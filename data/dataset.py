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
CSV_CHUNKSIZE = 250_000


@dataclass
class SequenceData:
    X: np.ndarray
    y: np.ndarray
    splits: np.ndarray | None
    source_groups: np.ndarray | None
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
    # Processed S exports can contain tens of millions of packet rows. Read
    # only model columns and aggregate one chunk at a time to avoid materializing
    # the multi-gigabyte CSV in memory.
    header = pd.read_csv(csv_path, nrows=0)
    columns = set(header.columns)
    if label_col not in columns:
        raise ValueError(f"CSV must contain label column: {label_col}")
    if feature_cols is None:
        if all(col in columns for col in DEFAULT_TRAFFIC_FEATURES):
            feature_cols = DEFAULT_TRAFFIC_FEATURES.copy()
        else:
            sample = pd.read_csv(csv_path, nrows=1024, low_memory=False)
            feature_cols = _numeric_feature_cols(sample, label_col)
    if not feature_cols:
        raise ValueError("No numeric feature columns were found")
    for col in feature_cols:
        if col not in columns:
            raise ValueError(f"CSV is missing feature column: {col}")

    selected_columns = list(dict.fromkeys(
        [column for column in ("flow_id", label_col, split_col, "source_group") if column in columns]
        + list(feature_cols)
    ))

    flows, labels, splits, source_groups = [], [], [], []
    dropped = 0

    def append_group(group: pd.DataFrame) -> None:
        x = group[feature_cols].to_numpy(dtype="float32")[:seq_len]
        if len(x) < seq_len:
            x = np.pad(x, ((0, seq_len - len(x)), (0, 0)), mode="constant")
        flows.append(x)
        label = str(group[label_col].iloc[0])
        labels.append(unknown_label if label.strip().lower() in UNKNOWN_LABEL_ALIASES else label)
        if split_col in group.columns:
            splits.append(str(group[split_col].iloc[0]).lower())
        if "source_group" in group.columns:
            source_groups.append(str(group["source_group"].iloc[0] or ""))

    carry = None
    reader = pd.read_csv(
        csv_path,
        usecols=selected_columns,
        chunksize=CSV_CHUNKSIZE,
        low_memory=False,
    )
    for chunk in reader:
        for col in feature_cols:
            chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        valid_mask = chunk[feature_cols].notna().all(axis=1) & chunk[label_col].notna()
        dropped += int((~valid_mask).sum())
        chunk = chunk.loc[valid_mask].copy()
        if chunk.empty:
            continue

        if "flow_id" in chunk.columns:
            if carry is not None:
                chunk = pd.concat((carry, chunk), ignore_index=True)
                carry = None
            last_flow_id = chunk["flow_id"].iloc[-1]
            complete = chunk.loc[chunk["flow_id"] != last_flow_id]
            carry = chunk.loc[chunk["flow_id"] == last_flow_id].copy()
            for _, group in complete.groupby("flow_id", sort=False):
                append_group(group)
        else:
            values = chunk[feature_cols].to_numpy(dtype="float32")
            flows.extend(values[:, None, :])
            labels.extend(
                unknown_label if str(label).strip().lower() in UNKNOWN_LABEL_ALIASES else str(label)
                for label in chunk[label_col].tolist()
            )
            if split_col in chunk.columns:
                splits.extend(str(value).lower() for value in chunk[split_col].tolist())
            if "source_group" in chunk.columns:
                source_groups.extend(str(value or "") for value in chunk["source_group"].tolist())

    if carry is not None and not carry.empty:
        append_group(carry)
    if dropped:
        print(f"[data] dropped {dropped} malformed rows from {csv_path}")

    # Keep the reject class at the final output index.  This makes checkpoints
    # and reports stable when a new known application is inserted.
    unique_labels = sorted({str(label) for label in labels if str(label) != str(unknown_label)})
    if any(str(label) == str(unknown_label) for label in labels):
        unique_labels.append(str(unknown_label))
    label_encoder = StableLabelEncoder(unique_labels)
    y = label_encoder.transform(np.asarray(labels, dtype=str))
    split_arr = np.asarray(splits) if splits else None
    source_group_arr = np.asarray(source_groups, dtype=str) if source_groups else None
    return SequenceData(
        X=np.stack(flows).astype("float32"),
        y=y.astype("int64"),
        splits=split_arr,
        source_groups=source_group_arr,
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
        data.source_groups[masks["train"]] if data.source_groups is not None else None,
        data.X[masks["val"]],
        data.y[masks["val"]],
        data.source_groups[masks["val"]] if data.source_groups is not None else None,
        data.X[masks["test"]],
        data.y[masks["test"]],
        data.source_groups[masks["test"]] if data.source_groups is not None else None,
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
    train_unknown: bool = True,
):
    data = load_sequence_csv(csv_path, seq_len=seq_len, feature_cols=feature_cols, unknown_label=unknown_label)
    split = _split_by_column(data)
    if split is None:
        if not allow_random_split:
            raise ValueError("Processed CSV must contain non-empty train, val and test split columns")
        raise ValueError("Random splitting is intentionally disabled for the temporal benchmark")
    X_train, y_train, train_groups, X_val, y_val, val_groups, X_test, y_test, test_groups = split
    (X_train, X_val, X_test), scaler = _scale_from_train(X_train, X_val, X_test)

    # Closed-set baselines learn only the known application classes. Unknown
    # flows remain in validation/test so their rejection performance can be
    # measured, but they must not contribute to the training loss.
    unknown_index = next(
        (index for index, name in enumerate(data.label_encoder.classes_) if str(name) == str(unknown_label)),
        None,
    )
    output_classes = int(len(data.label_encoder.classes_))
    if not train_unknown and unknown_index is not None:
        known_mask = y_train != int(unknown_index)
        X_train = X_train[known_mask]
        y_train = y_train[known_mask]
        if train_groups is not None:
            train_groups = train_groups[known_mask]
        output_classes -= 1
        if not output_classes:
            raise ValueError("train_unknown=False requires at least one known class")

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
        "num_classes": output_classes,
        "classes": [str(c) for c in data.label_encoder.classes_],
        "unknown_label": str(unknown_label),
        "unknown_index": unknown_index,
        "train_unknown": bool(train_unknown),
        "feature_cols": data.feature_cols,
        "scaler": scaler,
        "train_source_groups": train_groups,
        "val_source_groups": val_groups,
        "test_source_groups": test_groups,
    }
    return loaders
