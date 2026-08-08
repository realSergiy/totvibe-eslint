#!/usr/bin/env python3

"""Sample Thunderbolt eGPU link health into the journal, one key=value line per tick.

The freeze this watches for leaves no trace of its own (docs/issues/egpu-freeze/investigation.md):
the run-up is the only thing observable while the machine is still alive. NVIDIA's PCIe replay
counters are the one link-health signal that survives this platform's firmware refusing AER.
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

__version__ = "1.0.0"

PCI_DEVICES = Path("/sys/bus/pci/devices")
THUNDERBOLT_DEVICES = Path("/sys/bus/thunderbolt/devices")
NVIDIA_VENDOR_ID = "0x10de"
VGA_CLASS_PREFIX = "0x0300"
DEFAULT_INTERVAL_SEC = 30
NVIDIA_SMI_TIMEOUT_SEC = 15
REPLAY_LABELS = {"Replays Since Reset": "replays", "Replay Number Rollovers": "replay_rollovers"}


def read_attr(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except OSError:
        return None


def find_egpu_address() -> str | None:
    """The PCI address of the NVIDIA display device, rediscovered each tick — eGPU addresses move."""
    for device in sorted(PCI_DEVICES.iterdir()):
        vendor = read_attr(device / "vendor")
        pci_class = read_attr(device / "class")
        if vendor == NVIDIA_VENDOR_ID and pci_class is not None and pci_class.startswith(VGA_CLASS_PREFIX):
            return device.name
    return None


def list_uplink_addresses(address: str) -> list[str]:
    """The bridge chain from the GPU up to the host, root port last."""
    chain: list[str] = []
    node = (PCI_DEVICES / address).resolve().parent
    while node.name.count(":") == 2:
        chain.append(node.name)
        node = node.parent
    return chain


def read_link_state(address: str) -> dict[str, str]:
    speed = read_attr(PCI_DEVICES / address / "current_link_speed") or "?"
    width = read_attr(PCI_DEVICES / address / "current_link_width") or "?"
    return {f"link[{address}]": f"{speed.split()[0]}GT/s,x{width}"}


def read_aer_totals(address: str) -> dict[str, str]:
    """AER totals stay zero while the platform withholds native AER — a nonzero value is the signal."""
    totals: dict[str, str] = {}
    for kind in ("correctable", "fatal", "nonfatal"):
        content = read_attr(PCI_DEVICES / address / f"aer_dev_{kind}")
        if content is None:
            continue
        for line in content.splitlines():
            label, _, count = line.partition(" ")
            if label.startswith("TOTAL_ERR") and count.strip() != "0":
                totals[f"aer[{address}].{kind}"] = count.strip()
    return totals


def read_nvidia_replays() -> dict[str, str]:
    try:
        report = subprocess.run(
            ["nvidia-smi", "-q"],
            capture_output=True,
            text=True,
            timeout=NVIDIA_SMI_TIMEOUT_SEC,
            check=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {"replays": "unavailable"}
    counters: dict[str, str] = {}
    for line in report.splitlines():
        label, _, value = line.partition(":")
        if (key := REPLAY_LABELS.get(label.strip())) is not None:
            counters[key] = value.strip()
    return counters


def read_thunderbolt_links() -> dict[str, str]:
    if not THUNDERBOLT_DEVICES.is_dir():
        return {}
    links: dict[str, str] = {}
    for device in sorted(THUNDERBOLT_DEVICES.iterdir()):
        rx_speed = read_attr(device / "rx_speed")
        rx_lanes = read_attr(device / "rx_lanes")
        if rx_speed is None or rx_lanes is None:
            continue
        links[f"tb[{device.name}]"] = f"{rx_speed.split()[0]}Gb/s,x{rx_lanes}"
    return links


def collect_sample() -> dict[str, str]:
    address = find_egpu_address()
    if address is None:
        return {"egpu": "absent"} | read_thunderbolt_links()
    sample = {"egpu": address}
    sample |= read_link_state(address)
    sample |= read_aer_totals(address)
    for uplink in list_uplink_addresses(address):
        sample |= read_link_state(uplink)
        sample |= read_aer_totals(uplink)
    sample |= read_nvidia_replays()
    return sample | read_thunderbolt_links()


def format_sample(sample: dict[str, str]) -> str:
    return " ".join(f"{key}={value}" for key, value in sample.items())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="egpu-link-probe",
        description="Sample Thunderbolt eGPU PCIe link health into the journal.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SEC,
        metavar="SEC",
        help=f"seconds between samples (default: {DEFAULT_INTERVAL_SEC})",
    )
    parser.add_argument("--once", action="store_true", help="emit a single sample and exit")
    return parser


def main() -> int:
    options = build_parser().parse_args()
    while True:
        print(format_sample(collect_sample()), flush=True)
        if options.once:
            return 0
        time.sleep(options.interval)


if __name__ == "__main__":
    sys.exit(main())
