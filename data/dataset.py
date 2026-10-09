from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset


META_COLS = {"flow_id", "label", "split", "pkt_index"}
# Packet size, direction, and packet inter-arrival time features.
DEFAULT_TRAFFIC_FEATURES = ["size", "direction", "delta_time"]
UNKNOWN_LABEL_ALIASES = {"unknown", "_unknown", "__unknown__"}


@dataclass
class SequenceData:
    X: np.ndarray
    y: np.ndarray
    splits: np.ndarray | None
    feature_cols: list[str]
    label_encoder: "StableLabelEncoder"


class StableLabelEncoder:
    """Deterministic encoder with the reject class at the final index."""

    def __init__(self, classes: list[str]):
        self.classes_ = np.asarray(classes, dtype=str)
        self._index = {name: index for index, name in enumerate(self.classes_)}

    def transform(self, values):
        return np.asarray([self._index[str(value)] for value in values], dtype=np.int64)

    def inverse_transform(self, values):
        return self.classes_[np.asarray(values, dtype=np.int64)]


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
    unknown_label: str = "unknown",
) -> SequenceData:
    """Load packet rows into fixed-length flow tensors.

    By default the model input is [size, direction, delta_time]. Metadata such
    as pkt_index stays in the CSV for traceability but is not used as a feature.
    """

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
            label = str(group[label_col].iloc[0])
            labels.append(unknown_label if label.strip().lower() in UNKNOWN_LABEL_ALIASES else label)
            if split_col in group.columns:
                splits.append(str(group[split_col].iloc[0]).lower())
    else:
        flows = [row for row in df[feature_cols].to_numpy(dtype="float32")[:, None, :]]
        labels = [
            unknown_label if str(value).strip().lower() in UNKNOWN_LABEL_ALIASES else value
            for value in df[label_col].tolist()
        ]
        if split_col in df.columns:
            splits = [str(v).lower() for v in df[split_col].tolist()]

    # Keep the reject class at the final output index.  This makes checkpoints
    # and reports stable when a new known application is inserted.
    unique_labels = sorted({str(label) for label in labels if str(label) != str(unknown_label)})
    if any(str(label) == str(unknown_label) for label in labels):
        unique_labels.append(str(unknown_label))
    label_encoder = StableLabelEncoder(unique_labels)
    y = label_encoder.transform(np.asarray(labels, dtype=str))
    split_arr = np.asarray(splits) if splits else None
    return SequenceData(
        X=np.stack(flows).astype("float32"),
        y=y.astype("int64"),
        splits=split_arr,
        feature_cols=feature_cols,
        label_encoder=label_encoder,
    )


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
    feature_cols: list[str] | None = None,
    batch_size: int = 256,
    test_size: float = 0.2,
    val_size: float = 0.1,
    seed: int = 42,
    num_workers: int = 0,
    unknown_label: str = "unknown",
    allow_random_split: bool = False,
):
    data = load_sequence_csv(csv_path, seq_len=seq_len, feature_cols=feature_cols, unknown_label=unknown_label)
    split = _split_by_column(data)
    if split is None:
        if not allow_random_split:
            raise ValueError("Processed CSV must contain non-empty train, val and test split columns")
        raise ValueError("Random splitting is intentionally disabled for the temporal benchmark")
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
        "unknown_label": str(unknown_label),
        "unknown_index": next(
            (index for index, name in enumerate(data.label_encoder.classes_) if str(name) == str(unknown_label)),
            None,
        ),
        "feature_cols": data.feature_cols,
        "scaler": scaler,
    }
    return loaders
