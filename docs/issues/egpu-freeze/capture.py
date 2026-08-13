#!/usr/bin/python3
"""Temporarily arm durable eGPU telemetry and aggressive kernel stall capture."""

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

__version__ = "1.0.0"

PCI_DEVICES = Path("/sys/bus/pci/devices")
PCI_SLOTS = Path("/sys/bus/pci/slots")
THUNDERBOLT_DEVICES = Path("/sys/bus/thunderbolt/devices")
USB_DEVICES = Path("/sys/bus/usb/devices")
DRM_DEVICES = Path("/sys/class/drm")
DYNAMIC_DEBUG = Path("/proc/dynamic_debug/control")
DEFAULT_OUTPUT = Path("/var/log/egpu-freeze")
NVIDIA_VENDOR = "0x10de"
NVIDIA_CLASSES = ("0x0300", "0x0302")
PCI_ADDRESS_COLONS = 2
CORE_USB_IDS = {"1532:0f1a": "chroma", "0b95:1790": "ethernet"}
SYSCTLS = {
    "kernel.hardlockup_panic": "1",
    "kernel.hardlockup_all_cpu_backtrace": "1",
    "kernel.softlockup_panic": "1",
    "kernel.softlockup_all_cpu_backtrace": "1",
    "kernel.hung_task_panic": "1",
    "kernel.hung_task_all_cpu_backtrace": "1",
    "kernel.hung_task_timeout_secs": "30",
    "kernel.panic_on_rcu_stall": "1",
    "kernel.panic_on_oops": "1",
    "kernel.panic_on_warn": "1",
    "kernel.panic": "20",
    "kernel.sysrq": "1",
}


class DurableLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o640)

    def close(self) -> None:
        os.close(self.fd)

    def write(self, text: str) -> None:
        line = f"time_ns={time.time_ns()} {text.rstrip()}\n"
        record = line.encode()
        while record:
            record = record[os.write(self.fd, record) :]
        os.fdatasync(self.fd)


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip().replace(" ", "_").replace("\n", "|")
    except OSError:
        return "unavailable"


def find_egpu() -> Path | None:
    for device in sorted(PCI_DEVICES.iterdir()):
        if read(device / "vendor") == NVIDIA_VENDOR and read(device / "class").startswith(NVIDIA_CLASSES):
            return device
    return None


def pci_chain(device: Path) -> list[Path]:
    chain = [device]
    parent = device.resolve().parent
    while parent.name.count(":") == PCI_ADDRESS_COLONS:
        chain.append(PCI_DEVICES / parent.name)
        parent = parent.parent
    return chain


def collect_pci(egpu: Path | None) -> list[str]:
    fields = [f"egpu={egpu.name if egpu else 'absent'}"]
    if egpu is None:
        return fields
    for device in pci_chain(egpu):
        fields.append(
            f"link[{device.name}]={read(device / 'current_link_speed')},x{read(device / 'current_link_width')}"
        )
        fields.extend(
            f"aer[{device.name}].{kind}={read(device / f'aer_dev_{kind}')}"
            for kind in ("correctable", "fatal", "nonfatal")
        )
    return fields


def collect_slots() -> list[str]:
    fields: list[str] = []
    for slot in sorted(PCI_SLOTS.glob("*")):
        address = read(slot / "address")
        if address in {"0000:02:00", "0000:05:00"}:
            fields.extend(
                f"slot[{slot.name}].{attr}={read(slot / attr)}" for attr in ("adapter", "power", "cur_bus_speed")
            )
    return fields


def collect_thunderbolt() -> list[str]:
    fields: list[str] = []
    for device in sorted(THUNDERBOLT_DEVICES.glob("*")):
        for attr in ("authorized", "rx_speed", "rx_lanes", "tx_speed", "tx_lanes"):
            value = read(device / attr)
            if value != "unavailable":
                fields.append(f"tb[{device.name}].{attr}={value}")
    return fields


def collect_usb() -> list[str]:
    usb_states = dict.fromkeys(CORE_USB_IDS.values(), "absent")
    for device in USB_DEVICES.glob("*"):
        usb_id = f"{read(device / 'idVendor')}:{read(device / 'idProduct')}"
        if usb_id in CORE_USB_IDS:
            usb_states[CORE_USB_IDS[usb_id]] = device.name
    return [f"usb[{name}]={state}" for name, state in usb_states.items()]


def collect_drm(egpu: Path | None) -> list[str]:
    if egpu is None:
        return []
    fields: list[str] = []
    for card in DRM_DEVICES.glob("card[0-9]*"):
        if "-" not in card.name and (card / "device").resolve().name == egpu.name:
            fields.extend(
                f"drm[{connector.name}]={read(connector / 'status')}"
                for connector in DRM_DEVICES.glob(f"{card.name}-*")
            )
    return fields


def collect_links() -> str:
    egpu = find_egpu()
    fields = collect_pci(egpu) + collect_slots() + collect_thunderbolt() + collect_usb() + collect_drm(egpu)
    return " ".join(fields)


def stream(command: list[str], log: DurableLog, stop: threading.Event) -> None:
    try:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
            if process.stdout is None:
                log.write("error=stdout-unavailable")
                return
            while not stop.is_set() and (line := process.stdout.readline()):
                log.write(line.replace("\n", "|"))
    except OSError as error:
        log.write(f"error={error}")


def query_nvidia() -> list[str]:
    report = subprocess.run(["nvidia-smi", "-q"], capture_output=True, text=True, timeout=15, check=True).stdout
    counters: list[str] = []
    for line in report.splitlines():
        label, _, value = line.partition(":")
        if label.strip() in {"Replays Since Reset", "Replay Number Rollovers"}:
            counters.append(f"{label.strip().lower().replace(' ', '_')}={value.strip()}")
    return counters


def sample_nvidia(log: DurableLog, stop: threading.Event) -> None:
    while not stop.is_set():
        log.write("phase=query-start")
        try:
            counters = query_nvidia()
        except (OSError, subprocess.SubprocessError) as error:
            log.write(f"phase=query-failed error={error}")
        else:
            log.write("phase=query-complete " + " ".join(counters))
        stop.wait(5)


def get_sysctl(name: str) -> str:
    return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, check=True).stdout.strip()


def set_sysctl(name: str, value: str) -> None:
    subprocess.run(["sysctl", "-q", "-w", f"{name}={value}"], check=True)


def set_dynamic_debug(*, enabled: bool) -> None:
    if not DYNAMIC_DEBUG.is_file():
        return
    operation = "+p" if enabled else "-p"
    DYNAMIC_DEBUG.write_text(f"module thunderbolt {operation}\nmodule pciehp {operation}\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture a controlled eGPU removal into durable logs.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    options = build_parser().parse_args()
    if os.geteuid() != 0:
        sys.stderr.write("Run this script as root.\n")
        return 1
    run_name = datetime.now(tz=UTC).strftime("run-%Y%m%dT%H%M%SZ")
    run_dir = options.output / run_name
    run_dir.mkdir(parents=True)
    logs = {name: DurableLog(run_dir / f"{name}.log") for name in ("link", "nvidia", "kernel", "udev")}
    stop = threading.Event()
    previous_sysctls = {name: get_sysctl(name) for name in SYSCTLS}
    for name, value in SYSCTLS.items():
        set_sysctl(name, value)
    set_dynamic_debug(enabled=True)
    (run_dir / "cmdline.txt").write_text(Path("/proc/cmdline").read_text(encoding="utf-8"), encoding="utf-8")
    threads = [
        threading.Thread(target=sample_nvidia, args=(logs["nvidia"], stop), daemon=True),
        threading.Thread(
            target=stream,
            args=(["journalctl", "-kf", "-o", "short-precise"], logs["kernel"], stop),
            daemon=True,
        ),
        threading.Thread(
            target=stream,
            args=(
                [
                    "udevadm",
                    "monitor",
                    "--kernel",
                    "--udev",
                    "--property",
                    "--subsystem-match=pci",
                    "--subsystem-match=thunderbolt",
                    "--subsystem-match=usb",
                    "--subsystem-match=drm",
                    "--subsystem-match=net",
                ],
                logs["udev"],
                stop,
            ),
            daemon=True,
        ),
    ]
    signal.signal(signal.SIGTERM, lambda *_args: stop.set())
    for thread in threads:
        thread.start()
    sys.stdout.write(f"Capture armed in {run_dir}\n")
    sys.stdout.flush()
    try:
        while not stop.is_set():
            started = time.monotonic()
            logs["link"].write(collect_links())
            stop.wait(max(0.0, 1 - (time.monotonic() - started)))
    except KeyboardInterrupt:
        stop.set()
    finally:
        set_dynamic_debug(enabled=False)
        for name, value in previous_sysctls.items():
            set_sysctl(name, value)
        for log in logs.values():
            log.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
