# 项目环境说明

开始处理本项目时先阅读本文件。代码整理和实验运行必须遵守下面的环境与目录约定。

## Windows Python

不要在 PowerShell 中直接使用 `python`。当前它可能指向 Microsoft Store 启动器：

```text
C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe
```

Windows 端统一使用项目 Anaconda 解释器：

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' <脚本或模块>
```

已知版本：Python 3.13.5。

## WSL 与 CUDA

训练和 Mamba/CUDA 实验使用 `Ubuntu-22.04`，Python 环境为：

```text
/opt/traffic-mamba-venv/bin/python
```

项目在 WSL 中的路径：

```text
/mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP
```

常用运行方式：

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/tls40_s.yaml --resume"
```

注意事项：

- `docker-desktop` 不是可用的项目运行环境。
- `traffic-ubuntu-22.04` 能看到项目目录，但没有 `/opt/traffic-mamba-venv`。
- 即使默认发行版已设置为 `Ubuntu-22.04`，脚本中仍应显式指定 `wsl -d Ubuntu-22.04`。

## 目录约定

`paper/` 是论文只读归档目录。整理代码时严禁删除、移动、重命名或修改其中任何文件。

实验结果目录：

- 主任务：`results/tls40_s`、`results/quic40_s`、`results/tls60_s`、`results/quic60_s`
- 适配方法：`results/sota_adapted`
- HSTA 消融：`results/hsta_no_attention`、`results/hsta_flash_ablation`
- 近期基线：`results/recent_journal_baselines`
- HSTA 主实验：`results/hsta_flash`
- 效率测试：`results/efficiency_benchmark`

## 常用入口

```bash
bash scripts/run_wsl_experiments.sh main_all
bash scripts/run_wsl_experiments.sh sota_all
bash scripts/run_wsl_experiments.sh recent_all
bash scripts/run_wsl_experiments.sh ablation_all
bash scripts/run_wsl_experiments.sh hsta_flash_all
bash scripts/run_wsl_experiments.sh efficiency
```

Windows 环境检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```
