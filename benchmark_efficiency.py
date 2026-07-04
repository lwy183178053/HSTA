from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import torch
import torch.nn as nn
import yaml

from models import build_model
from utils import count_parameters, deep_merge, ensure_dir, save_json, seed_everything


DEFAULT_CONFIGS = [
    "configs/tls40_s.yaml",
    "configs/quic40_s.yaml",
    "configs/tls60_s.yaml",
    "configs/quic60_s.yaml",
    "configs/sota_adapted.yaml",
]

# Standalone Mamba baseline is intentionally excluded; NetMamba-adapted covers
# the Mamba-only comparison in the final experiment set.
CORE_MODELS = {"transformer", "hybrid", "30pktTCNET-adapted", "NetMamba-adapted"}
TASK_NAMES = ("tls40_s", "quic40_s", "tls60_s", "quic60_s")

REPEATED_METRICS = [
    "latency_ms_mean",
    "latency_ms_median",
    "latency_ms_p95",
    "latency_ms_std",
    "throughput_samples_per_s",
    "per_sample_latency_ms",
    "gpu_memory_allocated_before_mb",
    "gpu_memory_reserved_before_mb",
    "gpu_memory_allocated_after_mb",
    "gpu_memory_reserved_after_mb",
    "gpu_memory_peak_allocated_mb",
    "gpu_memory_peak_reserved_mb",
    "gpu_memory_peak_delta_mb",
]


class FlopCounter:
    """Lightweight inference FLOPs estimator for this project's model zoo.

    Convention: one multiply-add is counted as 2 FLOPs. LayerNorm, GELU,
    dropout, scalar residual adds, and most indexing/reshape ops are ignored.
    Mamba selective scan is a rough analytical estimate because the official
    CUDA kernel is opaque to Python hooks.
    """

    def __init__(self, estimate_mamba_scan: bool = True):
        self.estimate_mamba_scan = estimate_mamba_scan
        self.handles = []
        self.breakdown = defaultdict(float)

    def _add(self, name: str, flops: float) -> None:
        self.breakdown[name] += float(flops)

    def _linear_hook(self, module: nn.Linear, inputs, output) -> None:
        out = output[0] if isinstance(output, tuple) else output
        flops = 2 * out.numel() * module.in_features
        if module.bias is not None:
            flops += out.numel()
        self._add("linear", flops)

    def _conv1d_hook(self, module: nn.Conv1d, inputs, output) -> None:
        out = output[0] if isinstance(output, tuple) else output
        kernel_ops = (module.in_channels // module.groups) * module.kernel_size[0]
        flops = 2 * out.numel() * kernel_ops
        if module.bias is not None:
            flops += out.numel()
        self._add("conv1d", flops)

    def _rnn_hook(self, module: nn.Module, inputs, output) -> None:
        x = inputs[0]
        if module.batch_first:
            batch, seq_len = int(x.shape[0]), int(x.shape[1])
        else:
            seq_len, batch = int(x.shape[0]), int(x.shape[1])
        hidden = int(module.hidden_size)
        directions = 2 if module.bidirectional else 1
        gates = 4 if isinstance(module, nn.LSTM) else 3
        macs = 0
        for layer_idx in range(int(module.num_layers)):
            layer_input = int(module.input_size) if layer_idx == 0 else hidden * directions
            macs += batch * seq_len * directions * gates * (layer_input * hidden + hidden * hidden)
        self._add(module.__class__.__name__.lower(), 2 * macs)

    def _attention_hook(self, module: nn.Module, inputs, output) -> None:
        x = inputs[0]
        batch, seq_len = int(x.shape[0]), int(x.shape[1])
        heads = int(getattr(module, "heads", 1))
        head_dim = int(getattr(module, "head_dim", x.shape[-1] // max(heads, 1)))
        # QK^T and attention-value matmuls; projections are counted by Linear hooks.
        matmul_flops = 4 * batch * heads * seq_len * seq_len * head_dim
        softmax_flops = 3 * batch * heads * seq_len * seq_len
        self._add("attention_matmul_softmax", matmul_flops + softmax_flops)

    def _mamba_block_hook(self, module: nn.Module, inputs, output) -> None:
        if not self.estimate_mamba_scan:
            return
        x = inputs[0]
        batch, seq_len, dim = int(x.shape[0]), int(x.shape[1]), int(x.shape[2])
        mixer = getattr(module, "mixer", None)
        d_state = int(getattr(mixer, "d_state", 16))
        d_inner = int(getattr(mixer, "d_inner", dim * int(getattr(mixer, "expand", 2))))
        # Rough state update + output projection work inside selective scan.
        self._add("mamba_selective_scan_estimate", 6 * batch * seq_len * d_inner * d_state)

    def register(self, model: nn.Module) -> None:
        for module in model.modules():
            if isinstance(module, nn.Linear):
                self.handles.append(module.register_forward_hook(self._linear_hook))
            elif isinstance(module, nn.Conv1d):
                self.handles.append(module.register_forward_hook(self._conv1d_hook))
            elif isinstance(module, (nn.LSTM, nn.GRU)):
                self.handles.append(module.register_forward_hook(self._rnn_hook))
            elif module.__class__.__name__ == "MultiHeadSelfAttention":
                self.handles.append(module.register_forward_hook(self._attention_hook))
            elif module.__class__.__name__ == "MambaBlock":
                self.handles.append(module.register_forward_hook(self._mamba_block_hook))

    def clear(self) -> None:
        self.breakdown.clear()

    def remove(self) -> None:
        for handle in self.handles:
            handle.remove()
        self.handles.clear()

    @property
    def total_flops(self) -> float:
        return float(sum(self.breakdown.values()))


def _read_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def discover_experiments(config_paths: list[str], only: set[str] | None, checkpoint_name: str) -> list[dict]:
    discovered = []
    for config_path in config_paths:
        cfg = _read_yaml(config_path)
        if "base" not in cfg:
            exp_cfg = dict(cfg)
            exp_name = exp_cfg.get("exp_name", Path(config_path).stem)
            if only and exp_name not in only:
                continue
            checkpoint = Path(exp_cfg.get("output_dir", "results")) / exp_name / checkpoint_name
            discovered.append({"config_path": config_path, "exp_name": exp_name, "cfg": exp_cfg, "checkpoint": checkpoint})
            continue

        base = cfg["base"]
        for exp in cfg.get("experiments", []):
            merged = deep_merge(base, exp)
            merged["model_cfg"] = deep_merge(base.get("model_cfg", {}), exp.get("model_cfg", {}))
            exp_name = merged["exp_name"]
            if only and exp_name not in only:
                continue
            checkpoint = Path(merged.get("output_dir", base.get("output_dir", "results"))) / exp_name / checkpoint_name
            discovered.append({"config_path": config_path, "exp_name": exp_name, "cfg": merged, "checkpoint": checkpoint})
    return discovered


def load_checkpoint(path: Path, device: str):
    try:
        return torch.load(path, map_location=device, weights_only=False)
    except TypeError:
        return torch.load(path, map_location=device)


def load_model_from_checkpoint(item: dict, device: str) -> tuple[nn.Module, dict]:
    checkpoint_path = Path(item["checkpoint"])
    checkpoint = load_checkpoint(checkpoint_path, device)
    checkpoint_cfg = checkpoint.get("config", item["cfg"]) if isinstance(checkpoint, dict) else item["cfg"]
    input_dim = int(checkpoint.get("input_dim", 3)) if isinstance(checkpoint, dict) else 3
    num_classes = int(checkpoint.get("num_classes", checkpoint_cfg.get("num_classes", 0))) if isinstance(checkpoint, dict) else 0
    if num_classes <= 0:
        classes = checkpoint.get("classes", []) if isinstance(checkpoint, dict) else []
        num_classes = len(classes)
    if num_classes <= 0:
        raise ValueError(f"Cannot infer num_classes from {checkpoint_path}")
    seq_len = int(checkpoint_cfg.get("seq_len", 30))
    model = build_model(
        checkpoint_cfg["model"],
        input_dim=input_dim,
        num_classes=num_classes,
        seq_len=seq_len,
        cfg=checkpoint_cfg.get("model_cfg", {}),
    ).to(device)
    state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    meta = {
        "model": checkpoint_cfg["model"],
        "input_dim": input_dim,
        "num_classes": num_classes,
        "seq_len": seq_len,
        "model_cfg": checkpoint_cfg.get("model_cfg", {}),
    }
    return model, meta


def estimate_flops(model: nn.Module, sample: torch.Tensor, estimate_mamba_scan: bool) -> tuple[float, dict[str, float]]:
    counter = FlopCounter(estimate_mamba_scan=estimate_mamba_scan)
    counter.register(model)
    counter.clear()
    with torch.inference_mode():
        _ = model(sample)
    total = counter.total_flops
    breakdown = {key: float(value) for key, value in sorted(counter.breakdown.items())}
    counter.remove()
    return total, breakdown


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return float(ordered[index])


def benchmark_latency(
    model: nn.Module,
    sample: torch.Tensor,
    device: str,
    warmup: int,
    iterations: int,
    amp: bool,
) -> dict[str, Any]:
    use_cuda = device.startswith("cuda")
    use_amp = bool(amp and use_cuda)
    autocast_device = "cuda" if use_cuda else "cpu"
    memory_stats: dict[str, float | None]
    if use_cuda:
        cuda_device = torch.device(device)
        torch.cuda.synchronize(cuda_device)
        torch.cuda.reset_peak_memory_stats(cuda_device)
        allocated_before = float(torch.cuda.memory_allocated(cuda_device))
        reserved_before = float(torch.cuda.memory_reserved(cuda_device))
        memory_stats = {
            "gpu_memory_allocated_before_mb": allocated_before / (1024**2),
            "gpu_memory_reserved_before_mb": reserved_before / (1024**2),
        }
    else:
        memory_stats = {
            "gpu_memory_allocated_before_mb": None,
            "gpu_memory_reserved_before_mb": None,
        }

    with torch.inference_mode():
        for _ in range(warmup):
            with torch.amp.autocast(device_type=autocast_device, enabled=use_amp):
                _ = model(sample)
        if use_cuda:
            torch.cuda.synchronize()

        times_ms = []
        if use_cuda:
            for _ in range(iterations):
                start = torch.cuda.Event(enable_timing=True)
                end = torch.cuda.Event(enable_timing=True)
                start.record()
                with torch.amp.autocast(device_type=autocast_device, enabled=use_amp):
                    _ = model(sample)
                end.record()
                torch.cuda.synchronize()
                times_ms.append(float(start.elapsed_time(end)))
        else:
            for _ in range(iterations):
                start = time.perf_counter()
                _ = model(sample)
                times_ms.append(float((time.perf_counter() - start) * 1000.0))

    if use_cuda:
        torch.cuda.synchronize(cuda_device)
        allocated_after = float(torch.cuda.memory_allocated(cuda_device))
        reserved_after = float(torch.cuda.memory_reserved(cuda_device))
        peak_allocated = float(torch.cuda.max_memory_allocated(cuda_device))
        peak_reserved = float(torch.cuda.max_memory_reserved(cuda_device))
        memory_stats.update(
            {
                "gpu_memory_allocated_after_mb": allocated_after / (1024**2),
                "gpu_memory_reserved_after_mb": reserved_after / (1024**2),
                "gpu_memory_peak_allocated_mb": peak_allocated / (1024**2),
                "gpu_memory_peak_reserved_mb": peak_reserved / (1024**2),
                "gpu_memory_peak_delta_mb": max(0.0, peak_allocated - allocated_before) / (1024**2),
            }
        )
    else:
        memory_stats.update(
            {
                "gpu_memory_allocated_after_mb": None,
                "gpu_memory_reserved_after_mb": None,
                "gpu_memory_peak_allocated_mb": None,
                "gpu_memory_peak_reserved_mb": None,
                "gpu_memory_peak_delta_mb": None,
            }
        )

    mean_ms = float(statistics.mean(times_ms))
    return {
        "latency_ms_mean": mean_ms,
        "latency_ms_median": float(statistics.median(times_ms)),
        "latency_ms_p95": _percentile(times_ms, 95),
        "latency_ms_std": float(statistics.pstdev(times_ms)) if len(times_ms) > 1 else 0.0,
        "throughput_samples_per_s": float(sample.shape[0] * 1000.0 / mean_ms) if mean_ms > 0 else float("nan"),
        "per_sample_latency_ms": float(mean_ms / sample.shape[0]),
        **memory_stats,
    }


def _format_breakdown(breakdown: dict[str, float]) -> str:
    total = sum(breakdown.values()) or 1.0
    parts = []
    for key, value in sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True):
        parts.append(f"{key}:{value / 1e6:.3f}MF/{value / total:.1%}")
    return "; ".join(parts)


def _task_from_config(config_path: str) -> str:
    return Path(config_path).stem


def _task_from_exp_name(exp_name: str) -> str | None:
    for task in TASK_NAMES:
        if task in exp_name:
            return task
    return None


def _dataset_from_task(task: str) -> str:
    task_lower = task.lower()
    if task_lower.startswith("tls"):
        return "TLS"
    if task_lower.startswith("quic"):
        return "QUIC"
    return task


def _seed_from_exp_name(exp_name: str) -> str:
    match = re.search(r"seed(\d+)", exp_name)
    return match.group(1) if match else ""


def _variant_from_exp_name(exp_name: str) -> str:
    if "2block" in exp_name:
        return "2block"
    if "4block" in exp_name:
        return "4block"
    if exp_name.startswith("ablation_no_attention"):
        return "ablation_no_attention"
    if exp_name.startswith("ablation_attention_middle"):
        return "ablation_attention_middle"
    if exp_name.startswith("ablation_attention_front"):
        return "ablation_attention_front"
    return "main"


def _is_core_main_row(row: dict[str, Any]) -> bool:
    exp_name = str(row.get("exp_name", ""))
    return (
        row.get("model") in CORE_MODELS
        and row.get("block_repeats") == 1
        and row.get("variant") == "main"
        and exp_name.endswith("_seed42")
    )


def _finite_values(rows: list[dict[str, Any]], key: str) -> list[float]:
    values = []
    for row in rows:
        value = row.get(key)
        if value is None or pd.isna(value):
            continue
        values.append(float(value))
    return values


def _aggregate_repeats(base_row: dict[str, Any], repeat_rows: list[dict[str, Any]]) -> dict[str, Any]:
    row = dict(base_row)
    row["repeats"] = len(repeat_rows)
    for metric in REPEATED_METRICS:
        values = _finite_values(repeat_rows, metric)
        if not values:
            row[metric] = None
            row[f"{metric}_std_across_repeats"] = None
            continue
        row[metric] = float(statistics.mean(values))
        row[f"{metric}_std_across_repeats"] = float(statistics.pstdev(values)) if len(values) > 1 else 0.0

    latency_values = _finite_values(repeat_rows, "latency_ms_mean")
    throughput_values = _finite_values(repeat_rows, "throughput_samples_per_s")
    memory_values = _finite_values(repeat_rows, "gpu_memory_peak_allocated_mb")
    if latency_values:
        row["latency_ms_mean_min_across_repeats"] = min(latency_values)
        row["latency_ms_mean_max_across_repeats"] = max(latency_values)
        row["latency_ms_mean_cv_percent"] = (
            100.0 * row["latency_ms_mean_std_across_repeats"] / row["latency_ms_mean"]
            if row["latency_ms_mean"]
            else 0.0
        )
    if throughput_values:
        row["throughput_samples_per_s_min_across_repeats"] = min(throughput_values)
        row["throughput_samples_per_s_max_across_repeats"] = max(throughput_values)
    if memory_values:
        row["gpu_memory_peak_allocated_mb_max_across_repeats"] = max(memory_values)
    return row


def _merge_existing_dataframe(path: Path, new_df: pd.DataFrame, replace_exp_names: set[str]) -> pd.DataFrame:
    if path.exists():
        old_df = pd.read_csv(path)
        if "exp_name" in old_df.columns:
            old_df = old_df[~old_df["exp_name"].isin(replace_exp_names)]
        return pd.concat([old_df, new_df], ignore_index=True, sort=False)
    return new_df


def _merge_existing_payload(output_dir: Path, payload: dict[str, Any], replace_exp_names: set[str]) -> dict[str, Any]:
    path = output_dir / "benchmark_results.json"
    if not path.exists():
        return payload
    with path.open("r", encoding="utf-8-sig") as handle:
        old_payload = json.load(handle)
    merged = dict(old_payload)
    merged["settings"] = payload["settings"]
    merged["resolved_device"] = payload["resolved_device"]
    for key in ("results", "repeat_results", "details", "skipped"):
        old_rows = old_payload.get(key, []) or []
        if key in {"results", "repeat_results", "details"}:
            old_rows = [
                row
                for row in old_rows
                if not (isinstance(row, dict) and row.get("exp_name") in replace_exp_names)
            ]
        merged[key] = old_rows + (payload.get(key, []) or [])
    return merged


def run(args) -> None:
    if args.warmup < 0:
        raise ValueError("--warmup must be >= 0")
    if args.iterations <= 0:
        raise ValueError("--iterations must be > 0")
    if args.repeats <= 0:
        raise ValueError("--repeats must be > 0")
    if any(batch_size <= 0 for batch_size in args.batch_sizes):
        raise ValueError("--batch-sizes must contain positive integers")

    seed_everything(args.seed)
    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() and not args.cpu else "cpu"
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available")

    only = set(args.only or []) or None
    items = discover_experiments(args.configs, only=only, checkpoint_name=args.checkpoint_name)
    rows: list[dict[str, Any]] = []
    repeat_rows: list[dict[str, Any]] = []
    details: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for item in items:
        checkpoint_path = Path(item["checkpoint"])
        if not checkpoint_path.exists():
            skipped.append({"exp_name": item["exp_name"], "reason": f"missing {args.checkpoint_name}"})
            continue
        try:
            model, meta = load_model_from_checkpoint(item, device)
        except Exception as exc:
            skipped.append({"exp_name": item["exp_name"], "reason": repr(exc)})
            continue

        total_params, trainable_params = count_parameters(model)
        sample_one = torch.randn(1, meta["seq_len"], meta["input_dim"], device=device)
        flops_per_sample, breakdown = estimate_flops(
            model,
            sample_one,
            estimate_mamba_scan=not args.no_mamba_scan_estimate,
        )
        macs_per_sample = flops_per_sample / 2.0
        model_cfg = meta.get("model_cfg", {}) or {}
        base_layout = model_cfg.get("layout", [])
        block_repeats = int(model_cfg.get("block_repeats", 1))
        hybrid_layers = len(base_layout) * block_repeats if base_layout else 0
        task = _task_from_exp_name(item["exp_name"]) or _task_from_config(item["config_path"])
        dataset = _dataset_from_task(task)
        seed = _seed_from_exp_name(item["exp_name"])
        variant = _variant_from_exp_name(item["exp_name"])

        for batch_size in args.batch_sizes:
            sample = torch.randn(batch_size, meta["seq_len"], meta["input_dim"], device=device)
            base_row = {
                "exp_name": item["exp_name"],
                "task": task,
                "dataset": dataset,
                "seed": seed,
                "variant": variant,
                "config_path": item["config_path"],
                "checkpoint": str(checkpoint_path),
                "model": meta["model"],
                "batch_size": int(batch_size),
                "device": device,
                "amp": bool(args.amp and device.startswith("cuda")),
                "seq_len": meta["seq_len"],
                "input_dim": meta["input_dim"],
                "num_classes": meta["num_classes"],
                "total_params": total_params,
                "parameters_m": total_params / 1e6,
                "trainable_params": trainable_params,
                "trainable_params_m": trainable_params / 1e6,
                "block_repeats": block_repeats,
                "hybrid_layers": hybrid_layers,
                "macs_per_sample": macs_per_sample,
                "gmacs_per_sample": macs_per_sample / 1e9,
                "macs_per_batch": macs_per_sample * batch_size,
                "flops_per_sample": flops_per_sample,
                "gflops_per_sample": flops_per_sample / 1e9,
                "flops_per_batch": flops_per_sample * batch_size,
                "gflops_per_batch": flops_per_sample * batch_size / 1e9,
                "flop_breakdown": _format_breakdown(breakdown),
            }
            current_repeat_rows = []
            for repeat_idx in range(args.repeats):
                latency = benchmark_latency(
                    model,
                    sample,
                    device=device,
                    warmup=args.warmup,
                    iterations=args.iterations,
                    amp=args.amp,
                )
                repeat_row = {
                    **base_row,
                    "repeat": repeat_idx + 1,
                    **latency,
                }
                repeat_rows.append(repeat_row)
                current_repeat_rows.append(repeat_row)
            rows.append(_aggregate_repeats(base_row, current_repeat_rows))

        details.append(
            {
                "exp_name": item["exp_name"],
                "checkpoint": str(checkpoint_path),
                "meta": meta,
                "params": {"total": total_params, "trainable": trainable_params},
                "flops_per_sample": flops_per_sample,
                "macs_per_sample": macs_per_sample,
                "flop_breakdown": breakdown,
            }
        )
        del model
        if device.startswith("cuda"):
            torch.cuda.empty_cache()

    df = pd.DataFrame(rows)
    repeat_df = pd.DataFrame(repeat_rows)
    replace_exp_names = set(df["exp_name"].astype(str)) if not df.empty and "exp_name" in df.columns else set()
    if not df.empty:
        if args.merge_existing:
            df = _merge_existing_dataframe(output_dir / "benchmark_results.csv", df, replace_exp_names)
            repeat_df = _merge_existing_dataframe(output_dir / "benchmark_repeats.csv", repeat_df, replace_exp_names)
        df.to_csv(output_dir / "benchmark_results.csv", index=False)
        repeat_df.to_csv(output_dir / "benchmark_repeats.csv", index=False)
        summary_cols = [
            "exp_name",
            "task",
            "dataset",
            "model",
            "variant",
            "seed",
            "block_repeats",
            "hybrid_layers",
            "batch_size",
            "repeats",
            "total_params",
            "parameters_m",
            "gmacs_per_sample",
            "gflops_per_sample",
            "latency_ms_mean",
            "latency_ms_mean_std_across_repeats",
            "latency_ms_mean_cv_percent",
            "latency_ms_p95",
            "per_sample_latency_ms",
            "throughput_samples_per_s",
            "throughput_samples_per_s_std_across_repeats",
            "gpu_memory_peak_allocated_mb",
            "gpu_memory_peak_allocated_mb_std_across_repeats",
            "gpu_memory_peak_allocated_mb_max_across_repeats",
            "gpu_memory_peak_reserved_mb",
            "gpu_memory_peak_delta_mb",
        ]
        summary = df[[col for col in summary_cols if col in df.columns]].sort_values(
            ["task", "batch_size", "model", "variant", "seed"]
        )
        summary.to_csv(output_dir / "summary.csv", index=False)
        core_summary = summary[
            summary.apply(lambda row: _is_core_main_row(row.to_dict()), axis=1)
        ].sort_values(["task", "batch_size", "model"])
        core_summary.to_csv(output_dir / "core_model_efficiency.csv", index=False)
    else:
        existing_csvs = [
            output_dir / "benchmark_results.csv",
            output_dir / "benchmark_repeats.csv",
            output_dir / "summary.csv",
            output_dir / "core_model_efficiency.csv",
        ]
        if args.merge_existing and any(path.exists() for path in existing_csvs):
            print("[merge-existing] no new benchmark rows; preserving existing CSV outputs.")
        else:
            df.to_csv(output_dir / "benchmark_results.csv", index=False)
            repeat_df.to_csv(output_dir / "benchmark_repeats.csv", index=False)
            pd.DataFrame().to_csv(output_dir / "summary.csv", index=False)
            pd.DataFrame().to_csv(output_dir / "core_model_efficiency.csv", index=False)

    payload = {
        "settings": vars(args),
        "resolved_device": device,
        "repeat_convention": "benchmark_results.csv reports means across repeated benchmark runs; benchmark_repeats.csv keeps each raw repeat.",
        "flops_convention": "1 multiply-add = 2 FLOPs; Mamba selective scan is estimated analytically.",
        "macs_convention": "MACs are reported as FLOPs / 2.",
        "gpu_memory_convention": "CUDA peak memory is reset immediately before the timed inference warmup loop for each model and batch size.",
        "ignored_ops": ["LayerNorm", "GELU", "Dropout", "residual adds", "reshape/indexing"],
        "results": rows,
        "repeat_results": repeat_rows,
        "details": details,
        "skipped": skipped,
    }
    if args.merge_existing and (replace_exp_names or (output_dir / "benchmark_results.json").exists()):
        payload = _merge_existing_payload(output_dir, payload, replace_exp_names)
    save_json(payload, output_dir / "benchmark_results.json")
    notes = [
        "# Efficiency Benchmark",
        "",
        "This directory is generated by `benchmark_efficiency.py`.",
        "",
        "Files:",
        "- `benchmark_results.csv`: per experiment and batch-size averaged latency/FLOPs rows.",
        "- `benchmark_repeats.csv`: raw rows from each repeated benchmark run.",
        "- `summary.csv`: compact sortable full-model table.",
        "- `core_model_efficiency.csv`: seed42 core/adapted model table across the four main tasks.",
        "- `benchmark_results.json`: full metadata and FLOPs breakdown.",
        "",
        "FLOPs convention: one multiply-add is counted as 2 FLOPs. MACs are reported as FLOPs / 2.",
        "Latency, throughput, and GPU memory in summary tables are averaged across repeated benchmark runs.",
        "GPU memory is measured with CUDA peak memory stats reset immediately before the timed inference warmup loop.",
        "Mamba selective scan is an analytical estimate.",
        "LayerNorm, GELU, dropout, residual additions, reshape/indexing, and dataloader/preprocessing time are not counted.",
        "",
        f"Device: `{device}`",
        f"Batch sizes: `{args.batch_sizes}`",
        f"Repeats/warmup/iterations: `{args.repeats}/{args.warmup}/{args.iterations}`",
    ]
    (output_dir / "README.md").write_text("\n".join(notes) + "\n", encoding="utf-8")

    print(f"Saved: {output_dir / 'benchmark_results.csv'}")
    print(f"Saved: {output_dir / 'summary.csv'}")
    if skipped:
        print(f"Skipped: {len(skipped)} checkpoints; see benchmark_results.json")


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark model FLOPs and inference latency.")
    parser.add_argument("--configs", nargs="*", default=DEFAULT_CONFIGS)
    parser.add_argument("--only", nargs="*", default=None, help="Benchmark only selected exp_name values.")
    parser.add_argument("--checkpoint-name", default="best.pt", choices=["best.pt", "latest.pt"])
    parser.add_argument("--output-dir", default="results/efficiency_benchmark")
    parser.add_argument("--device", default="auto", help="auto, cpu, cuda, cuda:0, ...")
    parser.add_argument("--cpu", action="store_true", help="Force CPU when --device auto is used.")
    parser.add_argument("--batch-sizes", nargs="*", type=int, default=[1, 32, 512])
    parser.add_argument("--repeats", type=int, default=5, help="Independent benchmark repeats averaged in result tables.")
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--amp", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-mamba-scan-estimate", action="store_true")
    parser.add_argument("--merge-existing", action="store_true", help="Replace matching exp_name rows while preserving other benchmark rows in the output directory.")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
