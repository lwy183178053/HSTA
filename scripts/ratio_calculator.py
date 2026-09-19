#!/usr/bin/env python
"""Ratio / parameter-budget calculator -- NO GPU, NO training, runs in a second.

WHY THIS EXISTS
---------------
Designing the ratio study by trial and error on the GPU is wasteful: each run
costs 20-35 minutes. The parameter count of an HSTA layout is fully determined
by (dim, d_state, d_conv, expand, mlp_ratio, n_mamba, n_attention, n_mlp,
num_classes), so the design space can be enumerated analytically first and only
the genuinely informative arms ever get trained.

The model below mirrors models/hsta.py. It is CALIBRATED against the stored run
records, and the calibration error is printed, so you can see how much to trust
it instead of taking it on faith.

USAGE
    cd E:\\AllProject\\流量分析python项目\\HSTA
    & 'D:\\ProgramData\\anaconda3\\envs\\mybase\\python.exe' scripts\\ratio_calculator.py

    # smaller budget, e.g. if you want to keep runs fast
    ... scripts\\ratio_calculator.py --budget 450000
"""

from __future__ import annotations

import argparse
import math

# Reference HSTA configuration, identical to configs/hsta_flash.yaml.
REF_DIM = 128
REF_D_STATE = 16
REF_D_CONV = 4
REF_EXPAND = 2
REF_MLP_RATIO = 4

# Observed parameter counts from the stored run records (metrics.json).
OBSERVED = [
    ("mamba|mamba|mlp|attention|mlp", 2, 1, 2, 40, 602408),
    ("mamba|mamba|mlp|attention|mlp", 2, 1, 2, 60, 604988),
]


# ---------------------------------------------------------------------------
# Parameter model
# ---------------------------------------------------------------------------
def mamba_params(d: int, d_state: int = REF_D_STATE, d_conv: int = REF_D_CONV,
                 expand: int = REF_EXPAND) -> int:
    """Params of one MambaBlock, including its LayerNorm.

    Mirrors mamba_ssm.Mamba(d_model=d, d_state=N, d_conv=C, expand=E):
      in_proj   d -> 2E*d (no bias)
      conv1d    depthwise E*d -> E*d (kernel C, with bias)
      x_proj    E*d -> dt_rank + 2N     (no bias)
      dt_proj   dt_rank -> E*d
      A_log     E*d x N
      D         E*d
      out_proj  E*d -> d (no bias)
      norm      LayerNorm(d) -> 2d
    """
    ed = expand * d
    dt_rank = math.ceil(d / 16)
    p = d * (2 * ed)                                 # in_proj, bias=False
    p += ed * d_conv + ed                            # depthwise conv1d
    p += ed * (dt_rank + 2 * d_state)                # x_proj, bias=False
    p += dt_rank * ed + ed                           # dt_proj
    p += ed * d_state                                # A_log
    p += ed                                          # D
    p += ed * d                                      # out_proj, bias=False
    p += 2 * d                                       # external LayerNorm
    return p


def attention_params(d: int) -> int:
    """Params of one AttentionBlock (LayerNorm + 4 projections of d x d)."""
    return 2 * d + (4 * d * d + 4 * d)


def mlp_params(d: int, mlp_ratio: int = REF_MLP_RATIO) -> int:
    """Params of one FeedForwardBlock (LayerNorm + d->Rd + Rd->d)."""
    h = d * mlp_ratio
    return 2 * d + (d * h + h) + (h * d + d)


def total_params(n_mamba: int, n_attention: int, n_mlp: int, num_classes: int,
                 dim: int = REF_DIM) -> int:
    return (
        (3 * dim + dim)                              # embed: Linear(3,d) + bias
        + 256 * dim                                  # positional embedding (max_len=256)
        + n_mamba * mamba_params(dim)
        + n_attention * attention_params(dim)
        + n_mlp * mlp_params(dim)
        + 2 * dim                                    # terminal LayerNorm
        + dim * num_classes + num_classes            # classifier head
    )


def fmt(n: float) -> str:
    return f"{int(round(n)):,}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--budget", type=int, default=602408,
                        help="reference parameter budget (default: published HSTA, 40 classes)")
    parser.add_argument("--classes", type=int, default=40)
    parser.add_argument("--max-params", type=int, default=1000000,
                        help="flag arms above this size as too big to run")
    args = parser.parse_args()

    # ------------------------------------------------------------------
    print("=" * 94)
    print("STEP 1 -- CALIBRATION: does this parameter model match the real runs?")
    print("=" * 94)
    worst = 0.0
    for layout, m, a, mlp, cls, observed in OBSERVED:
        calc = total_params(m, a, mlp, cls)
        err = (calc - observed) / observed * 100.0
        worst = max(worst, abs(err))
        print(f"  {layout:<34} cls={cls:<3} calculated {fmt(calc):>10}  "
              f"observed {fmt(observed):>10}  error {err:+6.2f}%")
    print()
    print(f"  Worst calibration error: {worst:.2f}%")
    if worst < 3.0:
        print("  -> Model is accurate enough to design the study with. Proceed.")
    else:
        print("  -> WARNING: calibrate before trusting the numbers below.")
    print()

    # ------------------------------------------------------------------
    print("=" * 94)
    print("STEP 2 -- STRUCTURAL FACTS (no training needed)")
    print("=" * 94)
    mp = mamba_params(REF_DIM)
    ap = attention_params(REF_DIM)
    fp = mlp_params(REF_DIM)
    print(f"  At dim={REF_DIM}:")
    print(f"    one Mamba block      {fmt(mp):>10} params")
    print(f"    one attention block  {fmt(ap):>10} params   ({ap / mp:.2f}x a Mamba block)")
    print(f"    one FFN block        {fmt(fp):>10} params   ({fp / mp:.2f}x a Mamba block)")
    print()
    print("  Consequence for the design:")
    print("    At the reference width, an FFN is larger than a Mamba block, and a")
    print("    Mamba block is larger than an attention block. Therefore the fixed-width")
    print("    ratio sweep changes model size and cannot by itself prove a ratio effect.")
    print("    Use the parameter-matched study for any claim that is specific to the ratio.")
    print()

    # ------------------------------------------------------------------
    print("=" * 94)
    print(f"STEP 3 -- FIXED-WIDTH RATIO SWEEP  (dim={REF_DIM}, {args.classes} classes, "
          f"budget {fmt(args.budget)})")
    print("=" * 94)
    print("  Layout convention: one attention arm uses Mamba blocks, one transition FFN,")
    print("  attention, and one refinement FFN. The no-attention control uses one FFN;")
    print("  placement is identical across the one-attention arms, so only the ratio changes.")
    print()
    print(f"  {'ratio':<8}{'M':>3}{'A':>4}{'FFN':>5}{'blocks':>8}{'params':>12}"
          f"{'vs budget':>11}   note")
    print("  " + "-" * 90)

    # The explicit FFN count follows the actual layouts in the YAML studies.
    # In particular, the published 2:1 layout has two FFNs, not mamba_count + 1.
    arms = [(1, 1, 2), (2, 1, 2), (3, 1, 2), (4, 1, 2),
            (1, 2, 3), (2, 2, 3), (3, 2, 3), (5, 2, 3),
            (6, 2, 3), (1, 0, 1), (2, 0, 1), (4, 0, 1)]
    rows = []
    for m, a, n_mlp in arms:
        p = total_params(m, a, n_mlp, args.classes)
        ratio = f"{m}:{a}" if a else f"{m}:0"
        delta = (p - args.budget) / args.budget * 100.0
        if p > args.max_params:
            note = "TOO BIG - skip"
        elif abs(delta) <= 12:
            note = "size-matched to HSTA"
        elif delta < 0:
            note = f"{-delta:.0f}% smaller than HSTA"
        else:
            note = f"{delta:.0f}% larger than HSTA"
        rows.append((ratio, m, a, n_mlp, m + a + n_mlp, p, delta, note))
        print(f"  {ratio:<8}{m:>3}{a:>4}{n_mlp:>5}{m + a + n_mlp:>8}"
              f"{fmt(p):>12}{delta:>10.1f}%   {note}")
    print("  " + "-" * 90)
    print()

    # ------------------------------------------------------------------
    print("=" * 94)
    print("STEP 4 -- RECOMMENDED MINIMAL SET (train ONLY these)")
    print("=" * 94)
    recommended = [
        (1, 1, 2, "1:1", "low-attention bracket"),
        (2, 1, 2, "2:1", "THE PROPOSED RECIPE -- re-run so all arms share one protocol"),
        (3, 1, 2, "3:1", "state-space-heavy bracket"),
        (4, 1, 2, "4:1", "shows whether the peak is interior or keeps rising"),
        (1, 0, 1, "1:0", "no attention at all; deliberately the lightest arm"),
    ]
    print(f"  {'ratio':<7}{'layout':<36}{'params':>11}   why")
    print("  " + "-" * 90)
    total_all_tasks = 0
    for m, a, n_mlp, ratio, why in recommended:
        layout_parts = ["mamba"] * m
        layout_parts += ["mlp", "attention", "mlp"] if a else ["mlp"]
        layout = "|".join(layout_parts)
        p = total_params(m, a, n_mlp, args.classes)
        total_all_tasks += 3 * 4
        print(f"  {ratio:<7}{layout:<36}{fmt(p):>11}   {why}")
    print("  " + "-" * 90)
    print(f"  5 arms x 3 seeds x 4 tasks = {total_all_tasks} runs   (~10-17 h serial, ~4-6 h on 3 workers)")
    print(f"  5 arms x 3 seeds x 1 task  = {5 * 3} runs             (~1-1.5 h on 3 workers)")
    print()
    print("  ALREADY MEASURED -- do NOT re-run:")
    print("    Front / Middle attention placement: same 2:1 ratio, EQUAL parameters to HSTA,")
    print("      4 tasks x 3 seeds. This is the placement control and it is already done.")
    print("    7 baselines (GRU, Transformer, 30pktTCNET, NetMamba, SRViT, TrafficAudio, BPF-GNN).")
    print()
    print("  DELETE / DO NOT RUN:")
    print("    the legacy no-attention arm (mamba|mamba|mlp|mlp|mlp): it swaps attention for a")
    print("      3rd FFN, so it differs by an entire FFN as well as by attention. The 1:0 or")
    print("      2:0 arm above replaces it as a clean no-attention control.")
    print("    anything at 5:2 or above: already over budget and past the useful range.")
    print("    re-runs of baselines: reuse the stored records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
