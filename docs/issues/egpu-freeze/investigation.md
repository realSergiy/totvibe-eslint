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
- **Software Thunderbolt deauthorization is unavailable.** `/sys/bus/thunderbolt/devices/domain0/deauthorization` reads `0`, so this platform cannot tear down the tunnel by writing `0` to the device's `authorized` attribute.
- **Abrupt Thunderbolt loss is sufficient to break NVIDIA cleanup.** Both enclosure power-off and powered-enclosure cable removal produced root-port `Link Down`, Xid 79 and 154, then the same warning in `nvidia_dev_put()`; temporary `panic_on_warn=1` converted the warning into a captured panic.
- **`E1552IMS.321` is the latest BIOS.** MSI publishes only `.707`/`.321`/`.E03`, all 2022 or earlier, and LVFS has no update for the system firmware or either Core X Chroma controller.
- **netconsole is not viable here.** The only wired NIC (`enx98bb1e1f2012`, ax88179) sits at `0000:00:07.0/…/usb10` — downstream of the suspect tunnel — and `wlo1` is iwlwifi. Neither supports netpoll.

## What We Suspect

Leading hypothesis: the Thunderbolt tunnel drops abruptly. Enclosure power loss is not required because removing only the cable reproduced the same NVIDIA failure path.

An NVIDIA driver failure while handling that event may turn it into a machine-wide wedge and would fit the driver-version sensitivity. Zero replay counters weaken progressive PCIe signal corruption but cannot exclude sudden power or link loss after the final 30-second sample.

The controlled failures do not prove that the natural freezes begin with the same event because those freezes left no fault record.

## Observation Log

- **2026-08-08 - boot `5008c9e8`.** While the machine was in active use, its journal stopped at 20:00:49 AEST on kernel `7.0.0-28` with NVIDIA `580.173.02`. Host metrics were 99.84% idle with no memory or disk pressure; laptop power was stable. No fault record, pstore record, or vmcore survived.
- **2026-08-12 - boot `07d7860a`.** While the machine was in active use, its journal stopped at 07:37:57 AEST on kernel `7.0.0-29` with NVIDIA `580.173.02`. All 1,270 telemetry samples had zero PCIe replays; the final sample showed normal full-width PCIe and 20 Gb/s x2 Thunderbolt links. No panic, pstore record, or vmcore survived despite the armed NMI watchdog and kdump. `pcie_ports=native` enabled AER/DPC on unrelated ports, but not anywhere in the eGPU bridge chain.
- **2026-08-12 - controlled enclosure power-off.** The root port reported `Link Down`, followed by NVIDIA Xid 79 and 154 and a warning in `nvidia_dev_put()`. Temporary `panic_on_warn=1` caused a panic and kdump; all preceding replay and AER counters were zero. The enclosure was powered on again about 10 seconds later, while the crash kernel was starting; it saved dmesg but stopped before writing a vmcore, consistent with reattachment disrupting recovery but not proving it.
- **2026-08-12 - controlled Thunderbolt cable removal.** With enclosure mains left on, the same `Link Down`, Xid 79 and 154, `nvidia_dev_put()` warning, panic, and kdump sequence occurred. The warning followed link loss by about 198 ms; preceding replay and AER counters were zero. The cable remained disconnected until the BIOS screen; the crash kernel completed a 471 MB vmcore.

## Action Log

- **2026-08-09** — Instrumented via `recipe.toml`, since nothing currently captures this failure:
  - `[usr_local_sbin.egpu-link-probe]` + `[file.egpu-link-telemetry]` — sample replay counters, link speed/width along the whole bridge chain, AER totals, and Thunderbolt lane state into the journal every 30 s. No reboot needed.
  - `[file.grub_pcie_diagnostics]` — `pcie_ports=native` to request AER/DPC; `crash_kexec_post_notifiers=1` gives panic notifiers a chance to write pstore before kexec is attempted.
  - `[file.hardlockup_capture]` — `hardlockup_panic=1`, `hardlockup_all_cpu_backtrace=1`, `panic=20`. `softlockup_panic` deliberately left at 0.
- **2026-08-12** - Added temporary `capture.py` and `collect-after-reboot.sh` beside this document for the controlled enclosure power-off test. They are not deployed by Totchef.
- **2026-08-12** - Replaced NVIDIA `580.173.02` with `595.84` open kernel modules. The first boot loaded `595.84` cleanly, with no NVIDIA Xid or warning.

## Next

1. Keep capture available for a natural freeze so its initiating event can be compared with the controlled `Link Down` signature.
2. Retest cable removal on NVIDIA `595.84`, first from an Intel-primary session and then, if it survives, from the representative NVIDIA-primary session.
