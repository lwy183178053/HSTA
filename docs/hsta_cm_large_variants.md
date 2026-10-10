# HSTA-CM 大数据候选结构

这组实验只使用真正的大档 60 类数据：每个已知类别的训练、验证、测试上限为 `10000/2000/2000`，随机种子固定为 `599`。TLS 和 QUIC 各运行三种候选结构，共 6 个运行。结果写入 `results/hsta_cm_large_variants`，不使用 small 结果。

## 三个候选

### 双路多尺度卷积

保留 Mamba 时序分支和原始包卷积分支。卷积分支的三个残差块使用 `1/3/5` 卷积核，保持序列长度 30。两个分支都加入包位置编码和分支类型编码，不使用 DFT。

### 双路加 DFT

在 Mamba 和原始包卷积之外增加 DFT 频域卷积分支。对 `[30, 3]` 输入沿包序列做正交归一化 `rFFT`，得到 16 个复数频点，保留实部和虚部后形成 `[16, 6]`，再使用三个 `3/3/3` 残差卷积块。

三路 token 保留原始长度：Mamba 30 个、原始卷积 30 个、频域卷积 16 个，共 76 个 token。三路分别加入包位置编码或频率位置编码，并加入 Mamba、原始卷积、DFT 卷积三种分支类型编码。

### 完整三路多尺度模型

结构与上一组相同，但原始卷积和 DFT 卷积都使用 `1/3/5` 残差卷积块。该模型同时检验频域分支和渐进式多尺度卷积是否有叠加收益。

## 编码约定

- 包位置编码：可学习参数 `[1, 30, 256]`，供 Mamba 和原始卷积分支使用。
- 频率位置编码：可学习参数 `[1, 16, 256]`，只供 DFT 分支使用。
- 分支类型编码：可学习参数 `[3, 256]`，分别对应 `mamba`、`raw_conv`、`dft_conv`。
- 三路 token 拼接后送入 FlashAttention，使用 `branch_mean` 对三个分支等权池化，避免 30、30、16 的 token 数量造成频域分支权重偏低。

## 比较规则

三个候选使用相同的数据划分、unknown 训练协议、学习率、早停策略和随机种子。比较已知类别 Accuracy/Macro-F1、unknown Precision/Recall/F1、AUROC、AUPR、开放集 Macro-F1、参数量和推理时间。候选结构只有在与当前 HSTA-CM-open 的大数据结果比较后，才决定是否升级为论文主模型。

运行入口：

```powershell
wsl.exe -d Ubuntu-22.04 -- bash -lc "cd '/mnt/e/流量分析python项目/HSTA' && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/hsta_cm_large_variants.yaml --force --no-resume"
```

目前只完成代码和配置设计，未启动这 6 个训练任务。
