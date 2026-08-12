# eGPU Hard Freeze

> Note: keep this file minimalist and concise, less is more!
> Only record things we have zero doubt about in "What We Know 100%."

## Context

Kubuntu 26.04 on an MSI Summit B15 A11M (`MS-1552`, Tiger Lake-LP, BIOS `E1552IMS.321`), driving an NVIDIA RTX 4070 in a **Razer Core X Chroma over Thunderbolt 3**. Hybrid graphics: Intel Iris Xe (`00:02.0`) internal panel, eGPU (`04:00.0`) as seat-primary — see [laptop-rendering-sluggishness](../laptop-rendering-sluggishness/investigation.md).

The box has frozen hard for years. Frequency tracks the NVIDIA driver version unpredictably: months of quiet on one release, 2-3 hangs per day on the next, quiet again on the one after.

## The Problem

Recurring total-machine hard freeze while actively working. The two most recent recorded instances had the same symptom signature; only a hard reset recovered the machine.

## Symptoms

- The pointer stops moving and all input becomes unresponsive. Caps Lock, Num Lock, and attempted emergency keyboard shortcuts have no effect; only a hard reset recovers the machine.
- All three monitors retain the final frame without distortion or other visual artifacts.
- The laptop CPU fan ramps to high speed within 5-10 seconds and stays there until reset.
- The normally illuminated Razer Core X Chroma enclosure lights turn off immediately when the freeze occurs.

## What We Know 100%

- **Neither hard freeze produced a fault record.** No oops, panic, WARN, `Xid`, `NVRM`, MCE, EDAC, or thermal event; no vmcore or pstore record. Each journal stops abruptly.
- **AER remains unavailable on the eGPU path.** Firmware rejects AER control; `pcie_ports=native` enabled AER/DPC on unrelated ports, but the entire eGPU bridge chain still has no `aer_dev_*` counters.
- **The 12 August freeze did not reach the armed panic path.** The NMI watchdog, `hardlockup_panic=1`, pstore, and kdump were active, but produced neither a panic record nor a vmcore.
- **Laptop mains power was clean before the 8 August freeze.** 7,374 upower voltage samples were `fully-charged`, with no `discharging` event; voltage stayed at 12.040-12.073 V in the final hour. The enclosure's separate mains feed was not monitored.
- **Every recorded PCIe replay counter was zero on 12 August.** All 1,270 samples were zero; the final sample showed normal link widths and Thunderbolt lane state.
- **`E1552IMS.321` is the latest BIOS.** MSI publishes only `.707`/`.321`/`.E03`, all 2022 or earlier, and LVFS has no update for the system firmware or either Core X Chroma controller.
- **netconsole is not viable here.** The only wired NIC (`enx98bb1e1f2012`, ax88179) sits at `0000:00:07.0/…/usb10` — downstream of the suspect tunnel — and `wlo1` is iwlwifi. Neither supports netpoll.

## What We Suspect

Leading hypothesis: the enclosure abruptly loses power or Thunderbolt connectivity. Its lights turn off at the same moment as the freeze, but that does not distinguish enclosure power loss from loss of its USB/Thunderbolt path.

An NVIDIA driver failure while handling that event may turn it into a machine-wide wedge and would fit the driver-version sensitivity. Zero replay counters weaken progressive PCIe signal corruption but cannot exclude sudden power or link loss after the final 30-second sample.

No manual deauthorization or hard disconnect has been attempted, so this suspected trigger remains untested.

## Observation Log

- **2026-08-08 - boot `5008c9e8`.** While the machine was in active use, its journal stopped at 20:00:49 AEST on kernel `7.0.0-28` with NVIDIA `580.173.02`. Host metrics were 99.84% idle with no memory or disk pressure; laptop power was stable. No fault record, pstore record, or vmcore survived.
- **2026-08-12 - boot `07d7860a`.** While the machine was in active use, its journal stopped at 07:37:57 AEST on kernel `7.0.0-29` with NVIDIA `580.173.02`. All 1,270 telemetry samples had zero PCIe replays; the final sample showed normal full-width PCIe and 20 Gb/s x2 Thunderbolt links. No panic, pstore record, or vmcore survived despite the armed NMI watchdog and kdump. `pcie_ports=native` enabled AER/DPC on unrelated ports, but not anywhere in the eGPU bridge chain.

## Action Log

- **2026-08-09** — Instrumented via `recipe.toml`, since nothing currently captures this failure:
  - `[usr_local_sbin.egpu-link-probe]` + `[file.egpu-link-telemetry]` — sample replay counters, link speed/width along the whole bridge chain, AER totals, and Thunderbolt lane state into the journal every 30 s. No reboot needed.
  - `[file.grub_pcie_diagnostics]` — `pcie_ports=native` to request AER/DPC; `crash_kexec_post_notifiers=1` gives panic notifiers a chance to write pstore before kexec is attempted.
  - `[file.hardlockup_capture]` — `hardlockup_panic=1`, `hardlockup_all_cpu_backtrace=1`, `panic=20`. `softlockup_panic` deliberately left at 0.

## Next

1. Run the enclosure from a UPS with event logging, or monitor its mains feed for interruptions.
2. Attempt software deauthorization (`echo 0 > /sys/bus/thunderbolt/devices/0-1/authorized`) and a separate physical disconnect as controlled reproducer tests. Expect to lose the session because the eGPU is seat-primary.
3. After each freeze, read `/sys/fs/pstore` and `/var/crash`, and check the final replay and link samples.
