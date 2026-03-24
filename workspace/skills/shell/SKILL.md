---
name: shell
description: Execute shell commands, manage files, run scripts, and install packages on the MiniClaw VM
tools: [shell]
trigger: file, folder, directory, command, run, execute, install, create, delete, move, copy, service, process, script, package, apt, pip, npm, systemd, cron
---

# Shell Skill

## Capabilities
- Read and write files on the VM filesystem
- Run shell commands (bash)
- Install system packages via `apt install`
- Install Python packages via `/opt/miniclaw/venv/bin/pip install`
- Install Node packages via `npm install -g`
- Create and manage systemd services
- Run scripts in `/opt/miniclaw/scripts/`
- Manage cron jobs

## Safety Rules
- Always use the venv pip: `/opt/miniclaw/venv/bin/pip install` — never system-wide
- Never install PyTorch with CUDA — always use `--index-url https://download.pytorch.org/whl/cpu`
- Never install Ubuntu's `npm` package — Node 22 (nodesource) already includes it
- Dangerous operations (rm -rf, service restarts affecting production) require Esam's confirmation
- All commands are logged to the daily memory

## Procedures

### Install Python Package
```bash
/opt/miniclaw/venv/bin/pip install <package>
```

### Install System Package
```bash
sudo apt install -y <package>
```

### Create Systemd Service
1. Write unit file to `/opt/miniclaw/systemd/<name>.service`
2. Copy to `/etc/systemd/system/`
3. `systemctl daemon-reload && systemctl enable --now <name>`

### Read File
```bash
cat <path>
```

### Create/Edit File
Write the content, then use shell to verify.
