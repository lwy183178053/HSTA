from data.sampler import (
    TEMPORAL_DATE_SPLITS,
    limit_real_unknown_ratio,
    select_available_top_apps,
)
import csv


def test_quic_windows_are_14_2_12_days():
    assert tuple(map(len, (TEMPORAL_DATE_SPLITS["quic"][x] for x in ("train", "val", "test")))) == (14, 2, 12)


def test_top_apps_are_restricted_to_available_classes_but_keep_heldout_apps():
    counts = {"known-a": 100, "known-b": 80, "heldout-only": 0, "not-in-s": 1000}
    available = {"known-a", "known-b", "heldout-only", "default-background"}

    known, unknown = select_available_top_apps(counts, available, topk=2)

    assert known == ["known-a", "known-b"]
    assert unknown == ["heldout-only"]


def test_unknown_budget_is_actual_and_keeps_whole_flows(tmp_path):
    path = tmp_path / "tls60.csv"
    fields = ["flow_id", "label", "pkt_index", "split", "original_app", "source_group",
              "size", "direction", "delta_time", "noise_family", "capture_date", "source_flow_id"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for split in ("train", "val", "test"):
            for i in range(10):
                for pkt in range(30):
                    writer.writerow(dict(flow_id=f"known-{split}-{i}", label="known", pkt_index=pkt,
                                         split=split, original_app="known", source_group="known",
                                         size=1, direction=1, delta_time=1, noise_family="",
                                         capture_date="20211004", source_flow_id=f"src-known-{split}-{i}"))
            for app in ("u1", "u2", "u3"):
                for i in range(4):
                    for pkt in range(30):
                        writer.writerow(dict(flow_id=f"{app}-{split}-{i}", label="unknown", pkt_index=pkt,
                                             split=split, original_app=app, source_group="unknown_support",
                                             size=1, direction=1, delta_time=1, noise_family="",
                                             capture_date="20211004", source_flow_id=f"src-{app}-{split}-{i}"))
    result = limit_real_unknown_ratio(path, ratio=.30, seed=599)
    assert result["requested_by_split"] == {"train": 3, "val": 3, "test": 3}
    assert result["actual_by_split"] == result["requested_by_split"]
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for flow in {r["flow_id"] for r in rows}:
        assert sum(r["flow_id"] == flow for r in rows) == 30
