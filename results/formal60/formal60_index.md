# formal60 数据与结果索引

本索引是 `results/formal60` 的轻量入口，记录正式实验使用的数据来源、
开放集构造、时间切分、运行矩阵和结果文件。原始 H5、处理后 CSV、
checkpoint、日志和预测文件保留在本机原路径，不在此索引中复制或移动。

当前目录只保留 30 组五个基线模型结果。旧版 MVIF-Net 快照已移至外部
清理归档；当前 MVIF-Net 的 open/closed 结果位于
`results/mvif_net_masked_global_pooling`，并由活动配置统一管理。

## 数据来源

两套数据均由 CESNET DataZoo S 源数据按 flow 重建后导出：

| 数据集 | 原始入口 | 处理后入口 | 包记录 | 流数量 | 审计 |
|---|---|---|---:|---:|---|
| CESNET-TLS22-S | `data/raw/cesnet_tls22_datazoo/S/CESNET-TLS22-S.h5` | `data/processed/datazoo_tls60_s_protocol.csv` | 35,280,000 | 1,176,000 | passed |
| CESNET-QUIC22-S | `data/raw/cesnet_quic22_datazoo/S/CESNET-QUIC22-S.h5` | `data/processed/datazoo_quic60_s_protocol.csv` | 32,381,970 | 1,079,399 | passed |

审计快照分别为 `data/processed/datazoo_tls60_s_protocol.audit.json` 和
`data/processed/datazoo_quic60_s_protocol.audit.json`；manifest 和导出报告
使用同一数据集前缀。两套数据的模型输入均为每条流前 30 个数据包的
标准化三维特征 `[packet_size, direction, inter_packet_arrival]`，不足 30
个包时尾部补零，超过 30 个包时截断。日期、flow ID、原始应用身份、
来源组和噪声族只用于审计，不作为输入。

## 时间切分

| 数据集 | 训练 | 验证 | 测试 |
|---|---|---|---|
| CESNET-TLS22-S | 2021-10-04 至 2021-10-10 | 2021-10-11 | 2021-10-12 至 2021-10-17 |
| CESNET-QUIC22-S | 2022-10-31 至 2022-11-13 | 2022-11-14 至 2022-11-15 | 2022-11-16 至 2022-11-27 |

这是历史窗口训练、后续窗口测试的时间前向协议，用于检验未来流量上的
泛化和时间漂移风险。它不表示模型已经具备在线增量更新能力。

## 已知类别

两个数据集分别在训练窗口按应用流量频数选择 60 个 known 类，unknown
单独折叠为第 61 个输出类。

**CESNET-TLS22-S（60 类）**

`office-365`, `microsoft-update`, `seznam-media`, `appnexus`, `outlook`,
`microsoft-diagnostic`, `facebook-graph`, `google-ads`, `microsoft-settings`,
`tiktok`, `skype`, `microsoft-authentication`, `google-www`, `teams`,
`apple-itunes`, `instagram`, `rubiconproject`, `spotify`, `twitter`, `pubmatic`,
`mapscz`, `snapchat`, `seznam-authentication`, `facebook-media`,
`microsoft-defender`, `youtube`, `o2tv`, `dropbox`, `facebook-messenger`,
`google-play`, `autodesk`, `bing`, `microsoft-onedrive`, `seznam-ssp`, `avast`,
`seznam-email`, `microsoft-push`, `facebook-web`, `twitch`, `eset-edf`,
`apple-updates`, `apple-location`, `kaspersky`, `accuweather`, `grammarly`,
`bitdefender-gravityzone`, `google-safebrowsing`, `seznam-notifications`,
`google-connectivity`, `discord`, `google-fonts`, `amazon-advertising`,
`whatsapp`, `chmi`, `king-games`, `google-authentication`, `xbox-live`,
`adobe-ads`, `google-services`, `apple-weather`.

**CESNET-QUIC22-S（60 类）**

`google-www`, `google-ads`, `google-services`, `google-play`, `instagram`,
`google-gstatic`, `youtube`, `google-fonts`, `spotify`, `facebook-media`,
`snapchat`, `facebook-graph`, `google-safebrowsing`, `facebook-web`, `dns-doh`,
`google-usercontent`, `discord`, `google-authentication`, `microsoft-outlook`,
`google-autofill`, `facebook-connect`, `connectad`, `apple-privaterelay`,
`google-translate`, `openx`, `jsdelivr`, `cloudflare-cdnjs`, `google-calendar`,
`google-docs`, `facebook-messenger`, `google-imasdk`, `fontawesome`,
`google-drive`, `facebook-gamesgraph`, `microsoft-substrate`, `google-pay`,
`google-photos`, `joinhoney`, `sme-sk`, `tiktok`, `facebook-rupload`, `whatsapp`,
`playradio`, `garmin`, `onesignal`, `google-recaptcha`, `alza-www`, `usercentrics`,
`alza-webapi`, `firebase-crashlytics`, `chess-com`, `chrome-remotedesktop`,
`hubspot`, `csgo-market`, `xhamster`, `easybrain`, `unitygames`, `tawkto`,
`dm-de`, `google-colab`.

## Unknown 与噪声

真实 unknown 候选按应用身份分为不相交的 `unknown_support`、
`unknown_val_heldout` 和 `unknown_test_heldout`，再统一映射到 `unknown`。
TLS 的三组应用数量为 66/33/32，QUIC 为 21/10/11；测试真实 unknown
均按目标 36,000 条流导出。QUIC 训练和验证的可用 unknown 流量不足时
保留实际可用量，不重复采样。

合成噪声也按 split 隔离，三种噪声族为：

| Split | 噪声族 | 来源组 |
|---|---|---|
| train | `gaussian_iid_v1` | `noise_train` |
| val | `shuffle_spike_v2` | `noise_val` |
| test | `mixture_burst_v3` | `noise_test` |

审计确认两个数据集均含 `known`、真实 unknown 来源组和对应噪声来源组，
且 unknown 应用身份和噪声族没有跨 split 复用。

## 正式运行矩阵

活动配置 `configs/compact_s.yaml` 共展开 42 次运行，其中 MVIF-Net 的
open/closed 结果写入 `results/mvif_net_masked_global_pooling`。本目录只保留
五个基线模型的 30 次结果：

| 模型 | TLS seeds | QUIC seeds | 运行数 |
|---|---|---|---:|
| 30pktTCNET adapted | 599, 5009, 813 | 599, 5009, 813 | 6 |
| NetMamba adapted | 599, 5009, 813 | 599, 5009, 813 | 6 |
| SRViT adapted | 599, 5009, 813 | 599, 5009, 813 | 6 |
| TrafficAudio adapted | 599, 5009, 813 | 599, 5009, 813 | 6 |
| BPF-GNN adapted | 599, 5009, 813 | 599, 5009, 813 | 6 |
| **本目录合计** |  |  | **30** |

每个基线运行目录都应同时存在 `summary.csv` 和 `metrics.json`。MVIF-Net
运行快照位于独立的活动结果目录；各模型参数量和论文统计应从对应的
run-level `metrics.json` 与汇总文件计算。

## 结果入口

- `all_results.csv`: 30 条基线运行级正式结果。
- `formal60_summary.csv`: 按模型和数据集聚合的均值、样本标准差和 seed 数。
- `formal60_source_groups.csv`: 真实 unknown、合成噪声及其与 known 混合集的
  raw/threshold 来源分层指标。
- 每个 `*_seed*/summary.csv`: 单次运行的精简结果。
- 每个 `*_seed*/metrics.json`: 参数量、输入协议、阈值校准、训练状态和完整指标。

不把历史 MVIF-Net、branch-removal、time-CNN、residual-mode、
auxiliary-loss 或效率搜索结果混入 formal60 正式证据。
