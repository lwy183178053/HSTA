"""Helpers for expanding experiment configurations without duplicating YAML."""

from __future__ import annotations

import copy
import re
from typing import Any


def expand_seeded_experiments(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return experiment entries with one concrete entry per requested seed.

    Configurations may declare ``seeds`` at the top level (or on an individual
    experiment).  Names containing ``{seed}`` are formatted; otherwise a
    ``_seed<N>`` suffix is added.  Legacy configurations without a seed list
    are returned unchanged.
    """

    top_level_seeds = config.get("seeds")
    base = config.get("base", {})
    if top_level_seeds is None:
        top_level_seeds = base.get("seeds")

    expanded: list[dict[str, Any]] = []
    for original in config.get("experiments", []):
        experiment = copy.deepcopy(original)
        seeds = experiment.pop("seeds", top_level_seeds)
        if seeds is None:
            expanded.append(experiment)
            continue
        for seed in seeds:
            entry = copy.deepcopy(experiment)
            seed_value = int(seed)
            entry["seed"] = seed_value
            raw_name = str(entry["exp_name"])
            if "{seed}" in raw_name:
                entry["exp_name"] = raw_name.format(seed=seed_value)
            elif re.search(r"_seed\d+$", raw_name):
                entry["exp_name"] = re.sub(r"_seed\d+$", f"_seed{seed_value}", raw_name)
            else:
                entry["exp_name"] = f"{raw_name}_seed{seed_value}"
            expanded.append(entry)
    return expanded
