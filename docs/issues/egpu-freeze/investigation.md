# eGPU Hard Freeze

> Note: keep this file minimalist and concise, less is more!
> Only record things we have zero doubt about to the "What We Know 100%

## Context

Kubuntu 26.04 on an MSI Summit B15 A11M (`MS-1552`, Tiger Lake-LP, BIOS `E1552IMS.321`), driving an NVIDIA RTX 4070 in a **Razer Core X Chroma over Thunderbolt 3**. Hybrid graphics: Intel Iris Xe (`00:02.0`) internal panel, eGPU (`04:00.0`) as seat-primary — see [laptop-rendering-sluggishness](../laptop-rendering-sluggishness/investigation.md).

The box has frozen hard for years. Frequency tracks the NVIDIA driver version unpredictably: months of quiet on one release, 2–3 hangs per day on the next, quiet again on the one after.

## The Problem

Total lockup. Num Lock unresponsive, only a hard reset recovers. The most recent occurrence ended boot `5008c9e8` (uptime 8d 8h) at **Sat 2026-08-08 20:00:49 AEST**, on kernel `7.0.0-28` with NVIDIA `580.173.02`.

## What We Know 100%

- **The freeze left no trace at all.** No oops, panic, or WARN; no `Xid` or `NVRM` error in *any* of the six retained boots; no MCE, EDAC, or thermal event; no vmcore in `/var/crash`; no pstore record. The journal simply stops mid-idle.
- **The machine was idle.** 99.84% idle, load 0.20, 37 GB free, no page scanning, no swap-in, no disk I/O. Last user-session activity 19:51:44, nine minutes before death.
- **Nothing was installed that day.** Kernel `7.0.0-29` landed Aug 6 via unattended-upgrades, two days clean.
- **AER is disabled by firmware.** `acpi PNP0A08:00: _OSC: platform does not support [AER]`, and AER is absent from `OS now controls [PCIeHotplug SHPCHotplug PME PCIeCapability LTR DPC]`. The Thunderbolt root port `00:07.0` has no `aer_dev_*` counters at all. PCIe errors on the tunnel have never been observable.
- **kdump was armed but could not fire.** `crashkernel` reserved (1 GB), `kexec_crash_loaded=1` — but `kernel.hardlockup_panic=0`, so the NMI detector (`NMI watchdog: Enabled` every boot) only printk()s. No panic, so neither kdump nor pstore ever ran.
- **Mains power to the laptop was clean.** 7,374 upower voltage samples, state `fully-charged` in every one, no `discharging` event ever recorded. 12.040–12.073 V across the hour before the freeze.
- **PowerDevil never talks to the monitors.** `EACCES` on every `/dev/i2c-*`; no `i2c` group exists. DDC/CI dimming is not a factor, and the dim/DPMS thresholds (15 min / 30 min from 19:51) both fall *after* 20:00:49 anyway.
- **`nvidia-smi` exposes PCIe replay counters** (`Replays Since Reset`, `Replay Number Rollovers`) — a direct Thunderbolt link-health signal that works despite AER being off.
- **`E1552IMS.321` is the latest BIOS.** MSI publishes only `.707`/`.321`/`.E03`, all 2022 or earlier, and LVFS has no update for the system firmware or either Core X Chroma controller.
- **netconsole is not viable here.** The only wired NIC (`enx98bb1e1f2012`, ax88179) sits at `0000:00:07.0/…/usb10` — downstream of the suspect tunnel — and `wlo1` is iwlwifi. Neither supports netpoll.

## What We Suspect

A PCIe link event on the Thunderbolt tunnel: MMIO reads to the GPU start returning all-ones, the NVIDIA driver spins holding locks, and the machine wedges with no oops path. This is inference by elimination — no direct evidence survived.

It reconciles the driver-version pattern. Split the problem into *rate of link disturbances* (hardware, roughly constant) and *probability the driver survives one* (varies wildly per release). The product is what we observe. A driver bug alone would not explain a freeze at 99.84% idle.

Untested corollary: a surprise eGPU unplug may reproduce the identical signature. If so, we have a reproducer. The Core X Chroma has its own PSU on its own mains cord, so an enclosure-side power blip would drop the tunnel with no trace on the laptop battery — consistent with everything above.

An Intel ME update exists (`ME15055_U`, 2026-04-29; installed `15.0.50.2633`). MSI describes it as a security patch only; relevance to this is speculative.

## Action Log

- **2026-08-09** — Instrumented via `recipe.toml`, since nothing currently captures this failure:
  - `[usr_local_sbin.egpu-link-probe]` + `[file.egpu-link-telemetry]` — sample replay counters, link speed/width along the whole bridge chain, AER totals, and Thunderbolt lane state into the journal every 30 s. No reboot needed.
  - `[file.grub_pcie_diagnostics]` — `pcie_ports=native` to claim AER/DPC over the firmware's refusal; `crash_kexec_post_notifiers=1` so pstore is written before kexec is attempted.
  - `[file.hardlockup_capture]` — `hardlockup_panic=1`, `hardlockup_all_cpu_backtrace=1`, `panic=20`. `softlockup_panic` deliberately left at 0.
  - `[bash.rsyslog_purge]` — rsyslog captured nothing (journald's downstream, unscheduled during a lockup) and had been dead since Aug 1, leaving `/var/log/{syslog,kern.log}` at 0 bytes.

## Next

1. Confirm the reproducer: with telemetry armed, deauthorize the tunnel (`echo 0 > /sys/bus/thunderbolt/devices/0-1/authorized`) before attempting a physical unplug. Expect to lose the session either way — the eGPU is seat-primary.
2. After the next freeze, read `/sys/fs/pstore` and `/var/crash`, and check whether replay counters or AER totals rose in the run-up.
3. If the tunnel is implicated, put the enclosure on a UPS — it isolates the enclosure-side power theory in one step.
