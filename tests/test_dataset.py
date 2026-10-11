"""正式 CSV 读取及 open/closed 标准化隔离。"""
import numpy as np
import pandas as pd
import data.dataset as dataset


def test_chunk_boundaries_and_shared_known_only_scaler(tmp_path, monkeypatch):
    rows = []
    for split in ("train", "val", "test"):
        for app, size in (("known", 10), ("unknown", 1000)):
            for pkt in range(30):
                rows.append(dict(flow_id=f"{split}-{app}", label=app, split=split,
                                 pkt_index=pkt, size=size + pkt, direction=1,
                                 delta_time=pkt / 10, source_group="known" if app == "known" else "unknown_support"))
    path = tmp_path / "data.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    monkeypatch.setattr(dataset, "CSV_CHUNKSIZE", 47)
    seq = dataset.load_sequence_csv(path)
    assert seq.X.shape == (6, 30, 3)
    opened = dataset.make_loaders(path, train_unknown=True)
    closed = dataset.make_loaders(path, train_unknown=False)
    assert opened["num_classes"] == 2 and closed["num_classes"] == 1
    np.testing.assert_array_equal(opened["scaler"].mean_, closed["scaler"].mean_)
    assert opened["scaler"].mean_[0] == 24.5
    np.testing.assert_array_equal(opened["test"].dataset.X, closed["test"].dataset.X)
