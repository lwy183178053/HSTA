from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import DataLoader, Dataset


META_COLS = {"flow_id", "label", "split", "pkt_index"}
DEFAULT_TRAFFIC_FEATURES = ["size", "direction", "delta_time"]


@dataclass
class SequenceData:
    X: np.ndarray
    y: np.ndarray
    splits: np.ndarray | None
    feature_cols: list[str]
    label_encoder: LabelEncoder


class TrafficSeqDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.long)

    def __len__(self) -> int:
        return int(self.y.shape[0])

    def __getitem__(self, index: int):
        return self.X[index], self.y[index]


def _numeric_feature_cols(df: pd.DataFrame, label_col: str) -> list[str]:
    if all(col in df.columns for col in DEFAULT_TRAFFIC_FEATURES):
        return DEFAULT_TRAFFIC_FEATURES.copy()
    excluded = set(META_COLS) | {label_col}
    return [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(df[c])]


def load_sequence_csv(
    csv_path: str | Path,
    seq_len: int = 30,
    feature_cols: list[str] | None = None,
    label_col: str = "label",
    split_col: str = "split",
) -> SequenceData:
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    if label_col not in df.columns:
        raise ValueError(f"CSV must contain label column: {label_col}")
    if feature_cols is None:
        feature_cols = _numeric_feature_cols(df, label_col)
    if not feature_cols:
        raise ValueError("No numeric feature columns were found")
    for col in feature_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    valid_mask = df[feature_cols].notna().all(axis=1) & df[label_col].notna()
    dropped = int((~valid_mask).sum())
    if dropped:
        print(f"[data] dropped {dropped} malformed rows from {csv_path}")
        df = df.loc[valid_mask].copy()

    flows, labels, splits = [], [], []
    if "flow_id" in df.columns:
        for _, group in df.groupby("flow_id", sort=False):
            x = group[feature_cols].to_numpy(dtype="float32")[:seq_len]
            if len(x) < seq_len:
                x = np.pad(x, ((0, seq_len - len(x)), (0, 0)), mode="constant")
            flows.append(x)
            labels.append(group[label_col].iloc[0])
            if split_col in group.columns:
                splits.append(str(group[split_col].iloc[0]).lower())
    else:
        flows = [row for row in df[feature_cols].to_numpy(dtype="float32")[:, None, :]]
        labels = df[label_col].tolist()
        if split_col in df.columns:
            splits = [str(v).lower() for v in df[split_col].tolist()]

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(np.asarray(labels))
    split_arr = np.asarray(splits) if splits else None
    return SequenceData(
        X=np.stack(flows).astype("float32"),
        y=y.astype("int64"),
        splits=split_arr,
        feature_cols=feature_cols,
        label_encoder=label_encoder,
    )


def _stratified_split(X: np.ndarray, y: np.ndarray, test_size: float, val_size: float, seed: int):
    X_train, X_tmp, y_train, y_tmp = train_test_split(
        X,
        y,
        test_size=test_size + val_size,
        stratify=y,
        random_state=seed,
    )
    rel_test = test_size / (test_size + val_size)
    X_val, X_test, y_val, y_test = train_test_split(
        X_tmp,
        y_tmp,
        test_size=rel_test,
        stratify=y_tmp,
        random_state=seed,
    )
    return X_train, y_train, X_val, y_val, X_test, y_test


def _split_by_column(data: SequenceData):
    split = data.splits
    if split is None:
        return None
    masks = {name: split == name for name in ("train", "val", "test")}
    if not all(mask.any() for mask in masks.values()):
        return None
    return (
        data.X[masks["train"]],
        data.y[masks["train"]],
        data.X[masks["val"]],
        data.y[masks["val"]],
        data.X[masks["test"]],
        data.y[masks["test"]],
    )


def _scale_from_train(X_train: np.ndarray, *others: np.ndarray):
    scaler = StandardScaler()
    n_train, seq_len, dim = X_train.shape
    X_train_scaled = scaler.fit_transform(X_train.reshape(-1, dim)).astype("float32").reshape(n_train, seq_len, dim)
    scaled = [X_train_scaled]
    for X in others:
        n = X.shape[0]
        scaled.append(scaler.transform(X.reshape(-1, dim)).astype("float32").reshape(n, seq_len, dim))
    return scaled, scaler


def make_loaders(
    csv_path: str | Path,
    seq_len: int = 30,
    batch_size: int = 256,
    test_size: float = 0.2,
    val_size: float = 0.1,
    seed: int = 42,
    num_workers: int = 0,
):
    data = load_sequence_csv(csv_path, seq_len=seq_len)
    split = _split_by_column(data)
    if split is None:
        split = _stratified_split(data.X, data.y, test_size=test_size, val_size=val_size, seed=seed)
    X_train, y_train, X_val, y_val, X_test, y_test = split
    (X_train, X_val, X_test), scaler = _scale_from_train(X_train, X_val, X_test)

    pin_memory = torch.cuda.is_available()
    loaders = {
        "train": DataLoader(
            TrafficSeqDataset(X_train, y_train),
            batch_size=batch_size,
            shuffle=True,
            num_workers=num_workers,
            pin_memory=pin_memory,
        ),
        "val": DataLoader(
            TrafficSeqDataset(X_val, y_val),
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=pin_memory,
        ),
        "test": DataLoader(
            TrafficSeqDataset(X_test, y_test),
            batch_size=batch_size,
            shuffle=False,
            num_workers=num_workers,
            pin_memory=pin_memory,
        ),
        "input_dim": int(data.X.shape[-1]),
        "seq_len": int(data.X.shape[1]),
        "num_classes": int(len(data.label_encoder.classes_)),
        "classes": [str(c) for c in data.label_encoder.classes_],
        "feature_cols": data.feature_cols,
        "scaler": scaler,
    }
    return loaders
