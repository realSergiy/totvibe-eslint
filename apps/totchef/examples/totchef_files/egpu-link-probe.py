#!/usr/bin/python3
"""Thunderbolt eGPU link-health sampler (egpu-link-telemetry.service): one key=value line per tick into
the journal. The hard freeze this watches for leaves no trace of its own
(docs/issues/egpu-freeze/investigation.md), so the run-up is the only thing observable while the machine
is still alive; NVIDIA's PCIe replay counters are the one link signal that survives this platform's
firmware withholding AER. STANDALONE: system python3 + stdlib only."""

import argparse
import subprocess
import sys
import time
from pathlib import Path

__version__ = "1.0.0"

NVIDIA_PCI_VENDOR_ID = "0x10de"
NVIDIA_DISPLAY_CLASS_PREFIXES = ("0x0300", "0x0302")
PCI_DEVICES_DIR = Path("/sys/bus/pci/devices")
THUNDERBOLT_DEVICES_DIR = Path("/sys/bus/thunderbolt/devices")
# A PCI address (0000:00:07.0) carries two colons; a parent that doesn't is above the bus hierarchy.
PCI_ADDRESS_COLON_COUNT = 2
DEFAULT_INTERVAL_SEC = 30.0
NVIDIA_SMI_TIMEOUT_SEC = 15
REPLAY_LABELS = {"Replays Since Reset": "replays", "Replay Number Rollovers": "replay_rollovers"}
AER_KINDS = ("correctable", "fatal", "nonfatal")


def read_attr(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def find_egpu_address() -> str | None:
    """The NVIDIA display device's PCI address, rediscovered each tick — an eGPU's address can move."""
    for device in sorted(PCI_DEVICES_DIR.iterdir()):
        pci_class = read_attr(device / "class")
        if read_attr(device / "vendor") != NVIDIA_PCI_VENDOR_ID or pci_class is None:
            continue
        if pci_class.startswith(NVIDIA_DISPLAY_CLASS_PREFIXES):
            return device.name
    return None


def list_uplink_addresses(address: str) -> list[str]:
    """The bridge chain from the GPU up to the host, root port last."""
    chain: list[str] = []
    node = (PCI_DEVICES_DIR / address).resolve().parent
    while node.name.count(":") == PCI_ADDRESS_COLON_COUNT:
        chain.append(node.name)
        node = node.parent
    return chain


def read_link_state(address: str) -> dict[str, str]:
    speed = read_attr(PCI_DEVICES_DIR / address / "current_link_speed") or "?"
    width = read_attr(PCI_DEVICES_DIR / address / "current_link_width") or "?"
    return {f"link[{address}]": f"{speed.split()[0]}GT/s,x{width}"}


def read_aer_totals(address: str) -> dict[str, str]:
    """AER totals stay zero while the platform withholds native AER — a nonzero value is the signal."""
    totals: dict[str, str] = {}
    for kind in AER_KINDS:
        content = read_attr(PCI_DEVICES_DIR / address / f"aer_dev_{kind}")
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
    except OSError, subprocess.SubprocessError:
        return {"replays": "unavailable"}
    counters: dict[str, str] = {}
    for line in report.splitlines():
        label, _, value = line.partition(":")
        if (key := REPLAY_LABELS.get(label.strip())) is not None:
            counters[key] = value.strip()
    return counters


def read_thunderbolt_links() -> dict[str, str]:
    if not THUNDERBOLT_DEVICES_DIR.is_dir():
        return {}
    links: dict[str, str] = {}
    for device in sorted(THUNDERBOLT_DEVICES_DIR.iterdir()):
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
    for target in (address, *list_uplink_addresses(address)):
        sample |= read_link_state(target)
        sample |= read_aer_totals(target)
    return sample | read_nvidia_replays() | read_thunderbolt_links()


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
        help=f"seconds between samples (default: {DEFAULT_INTERVAL_SEC:g})",
    )
    parser.add_argument("--once", action="store_true", help="emit a single sample and exit")
    return parser


def main() -> int:
    options = build_parser().parse_args()
    while True:
        sys.stdout.write(f"{format_sample(collect_sample())}\n")
        sys.stdout.flush()
        if options.once:
            return 0
        time.sleep(options.interval)


if __name__ == "__main__":
    sys.exit(main())
