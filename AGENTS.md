# Project Environment Notes

Use this file first when starting a new Codex session in this repository.

## Windows Python

Do not use bare `python` from PowerShell in this project. It currently resolves to:

```powershell
C:\Users\Administrator\AppData\Local\Microsoft\WindowsApps\python.exe
```

That is the Microsoft Store launcher stub and may fail silently.

Use the project Anaconda interpreter instead:

```powershell
& 'D:\ProgramData\anaconda3\envs\mybase\python.exe' <script-or-module>
```

Known version:

```text
Python 3.13.5
```

## WSL For Mamba/CUDA

Use `Ubuntu-22.04` for WSL training and Mamba/CUDA work.

Known good WSL Python:

```bash
/opt/traffic-mamba-venv/bin/python
```

Known good checks:

```text
torch 2.11.0+cu128
cuda True
mamba_ssm ok
```

Project path inside WSL:

```bash
/mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP
```

Recommended PowerShell pattern:

```powershell
wsl -d Ubuntu-22.04 -- bash -lc "cd /mnt/e/AllProject/流量分析python项目/MM-MLP-A-MLP && source /opt/traffic-mamba-venv/bin/activate && python run_experiments.py --config configs/tls40_s.yaml --resume"
```

Notes:

- `docker-desktop` is not a usable project shell.
- `traffic-ubuntu-22.04` can see the project path but does not have `/opt/traffic-mamba-venv`.
- The WSL default distro has been set to `Ubuntu-22.04`, but explicit `wsl -d Ubuntu-22.04 -- ...` is still preferred in scripts and one-off commands.

## Quick Check

Run this from PowerShell when unsure:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_environment.ps1
```
