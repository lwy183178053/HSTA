"""Metrics for the open-world traffic classification protocol."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import f1_score, roc_auc_score


UNKNOWN_LABELS = {"unknown", "_unknown", "__unknown__"}


def unknown_class_index(classes: list[str] | tuple[str, ...] | None) -> int | None:
    """Return the explicit unknown class index, if the label map contains one."""
    if not classes:
        return None
    for index, name in enumerate(classes):
        if str(name).strip().lower() in UNKNOWN_LABELS:
            return int(index)
    return None


def open_set_metrics(
    y_true,
    y_pred,
    logits=None,
    classes: list[str] | tuple[str, ...] | None = None,
    unknown_index: int | None = None,
    reject_threshold: float | None = None,
) -> dict[str, float]:
    """Compute known/unknown recognition metrics.

    ``y_true`` contains the explicit unknown label for held-out applications
    and synthetic noise.  When ``reject_threshold`` is supplied, predictions
    are rejected using the unknown probability (or ``1-max(p_known)`` for a
    classifier without an unknown output).  Without it, the model's argmax is
    evaluated directly.  NaN is returned for AUROC when one side is absent.
    """
    y_true = np.asarray(y_true, dtype=np.int64).reshape(-1)
    y_pred = np.asarray(y_pred, dtype=np.int64).reshape(-1).copy()
    if y_true.shape != y_pred.shape:
        raise ValueError("y_true and y_pred must have the same number of samples")
    if unknown_index is None:
        unknown_index = unknown_class_index(classes)
    if unknown_index is None:
        return {
            "unknown_index": float("nan"),
            "known_count": float(y_true.size),
            "unknown_count": 0.0,
            "unknown_recall": float("nan"),
            "unknown_precision": float("nan"),
            "unknown_f1": float("nan"),
            "known_false_unknown_rate": float("nan"),
            "known_accuracy": float(f1_score(y_true, y_pred, average="micro", zero_division=0))
            if y_true.size
            else float("nan"),
            "open_set_accuracy": float("nan"),
            "unknown_auroc": float("nan"),
        }
    unknown_index = int(unknown_index)
    unknown_true = y_true == unknown_index

    unknown_scores = None
    if logits is not None:
        logits = np.asarray(logits, dtype=np.float64)
        if logits.ndim != 2 or logits.shape[0] != y_true.size:
            raise ValueError("logits must have shape [num_samples, num_classes]")
        logits = logits - np.max(logits, axis=1, keepdims=True)
        probs = np.exp(logits)
        probs /= np.maximum(np.sum(probs, axis=1, keepdims=True), 1e-12)
        if unknown_index < probs.shape[1]:
            unknown_scores = probs[:, unknown_index]
        else:
            unknown_scores = 1.0 - np.max(probs, axis=1)
        if reject_threshold is not None:
            y_pred = np.argmax(probs, axis=1).astype(np.int64)
            y_pred[unknown_scores >= float(reject_threshold)] = unknown_index

    known_true = ~unknown_true
    predicted_unknown = y_pred == unknown_index
    unknown_tp = int(np.sum(unknown_true & predicted_unknown))
    unknown_count = int(np.sum(unknown_true))
    known_count = int(np.sum(known_true))
    unknown_precision = unknown_tp / max(int(np.sum(predicted_unknown)), 1)
    unknown_recall = unknown_tp / max(unknown_count, 1)
    unknown_f1 = 2 * unknown_precision * unknown_recall / max(unknown_precision + unknown_recall, 1e-12)
    known_false_unknown_rate = float(np.sum(known_true & predicted_unknown) / max(known_count, 1))
    known_accuracy = float(np.mean(y_pred[known_true] == y_true[known_true])) if known_count else float("nan")
    open_set_accuracy = float(np.mean(y_pred == y_true)) if y_true.size else float("nan")

    if unknown_scores is not None and unknown_count and known_count:
        try:
            unknown_auroc = float(roc_auc_score(unknown_true.astype(np.int8), unknown_scores))
        except ValueError:
            unknown_auroc = float("nan")
    else:
        unknown_auroc = float("nan")
    return {
        "unknown_index": float(unknown_index),
        "known_count": float(known_count),
        "unknown_count": float(unknown_count),
        "unknown_recall": float(unknown_recall),
        "unknown_precision": float(unknown_precision),
        "unknown_f1": float(unknown_f1),
        "known_false_unknown_rate": known_false_unknown_rate,
        "known_accuracy": known_accuracy,
        "open_set_accuracy": open_set_accuracy,
        "unknown_auroc": unknown_auroc,
    }

