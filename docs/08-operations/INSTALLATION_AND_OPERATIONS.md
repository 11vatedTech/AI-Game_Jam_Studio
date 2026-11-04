# Installation and Operational Practices

## Principles

Install applications and adapters in clearly documented locations. Preserve clean upgrades and uninstalls. Avoid global environment contamination. Do not run as administrator unless an operation genuinely requires it.

## Operational checks

- Process exists and is healthy.
- Endpoint is reachable only on intended interface/port.
- Application version matches adapter support matrix.
- Required plugins are loaded and report expected versions.
- No unresolved startup/import/runtime errors.
- Disk, RAM and VRAM capacity available.
- Queue and child process state reconciled.
- Logs and diagnostics path exists and is writable.

## Local endpoint policy

ComfyUI, model servers and editor bridges should bind to loopback by default. Record endpoint/port per instance and discover it from configuration/process metadata rather than hardcoding assumptions. Any non-loopback exposure requires authenticated transport, firewall policy, threat review and approval.

## Recovery and support

Provide start/stop/restart, health, diagnostics, clean-up, backup, rollback and version pinning operations. Restart only studio-managed services, not arbitrary user processes. If an app becomes unresponsive, preserve logs and unsaved-project warnings; ask before terminating when user data may be lost.
