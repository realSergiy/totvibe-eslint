(
    """VersionedCook for [pnpm] — global npm packages via `pnpm add -g`, installed versions read from """
    """`pnpm list -g` and resolved against the npm registry. Runs as the invoking user; depends on [url] """
    """(pnpm itself)."""
)

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, override

from loguru import logger
from pydantic import model_validator

from totchef import shell
from totchef.cook_base import PackageListCook, PackagesConfig, SyncOutcome
from totchef.harness import fetch_latest_concurrent, fetch_url, find_binary

if TYPE_CHECKING:
    from totchef.recipe_types import RecipeConfig

NPM_REGISTRY = "https://registry.npmjs.org/{name}"


def parse_npm_latest(payload: bytes) -> str | None:
    """Latest version from the npm registry's per-package document (the `dist-tags.latest` field)."""
    return json.loads(payload).get("dist-tags", {}).get("latest")


def fetch_npm_latest(name: str) -> str | None:
    return parse_npm_latest(fetch_url(NPM_REGISTRY.format(name=name)))


def package_name(spec: str) -> str:
    """The package identity from a bare name or versioned npm specifier such as `node@26`."""
    scope_end = spec.find("/") if spec.startswith("@") else 0
    version_at = spec.find("@", scope_end + 1)
    return spec[:version_at] if version_at >= 0 else spec


def pnpm_home() -> Path:
    (
        """pnpm's home — `$PNPM_HOME` when the user set one, else the `~/.local/share/pnpm` default of """
        """pnpm's standalone installer. Resolved at call time so it follows become_user's $HOME drop in a """
        """forked child."""
    )
    return Path(os.environ["PNPM_HOME"]) if os.environ.get("PNPM_HOME") else Path.home() / ".local/share/pnpm"


def global_bin_dir() -> Path:
    """Where `pnpm add -g` links a global's executables — the dir pnpm demands on PATH before installing one."""
    return pnpm_home() / "bin"


def ensure_pnpm_home_env() -> None:
    (
        """Pin `$PNPM_HOME` and put pnpm's global bin dir on PATH before any global command: pnpm refuses """
        """to read or install globals while that dir is off PATH, and totchef runs from a shell that may """
        """not have sourced the installer's profile snippet. Mutates this process's environment, which """
        """every child inherits."""
    )
    os.environ["PNPM_HOME"] = str(pnpm_home())
    bin_dir = str(global_bin_dir())
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    if bin_dir not in path_entries:
        os.environ["PATH"] = os.pathsep.join([bin_dir, *path_entries])


def parse_global_list(output: str) -> dict[str, str]:
    (
        """Map package name -> version from `pnpm list -g --depth 0 --json`: a list of global roots, each """
        """carrying a `dependencies` object keyed by package name. The on-disk layout underneath is a """
        """content-hashed directory, so pnpm itself is the only reliable reader."""
    )
    roots = json.loads(output)
    return {name: entry["version"] for root in roots for name, entry in root.get("dependencies", {}).items()}


def read_global_versions(pnpm: Path) -> dict[str, str]:
    completed = shell.run(str(pnpm), "list", "-g", "--depth", "0", "--json")
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        msg = f"`pnpm list -g` failed ({completed.returncode}): {detail}"
        raise RuntimeError(msg)
    return parse_global_list(completed.stdout)


class PnpmConfig(PackagesConfig):
    @model_validator(mode="after")
    def validate_unique_packages(self) -> PnpmConfig:
        specs: dict[str, str] = {}
        for spec in self.packages:
            name = package_name(spec)
            if previous := specs.get(name):
                msg = f"Multiple pnpm specs identify {name}: {previous}, {spec}"
                raise ValueError(msg)
            specs[name] = spec
        return self


class PnpmCook(PackageListCook):
    entry_model = PnpmConfig

    def __init__(self, section: RecipeConfig) -> None:
        super().__init__(section)
        config = PnpmConfig.model_validate(section)
        self.specs = {package_name(spec): spec for spec in config.packages}

    @override
    def list_requested(self) -> list[str]:
        return list(self.specs)

    @override
    def list_installed(self) -> dict[str, str]:
        pnpm = find_binary("pnpm")
        if not pnpm:
            return {}
        ensure_pnpm_home_env()
        return read_global_versions(pnpm)

    @override
    def find_latest(self, names: list[str]) -> dict[str, str | None]:
        unversioned = [name for name in names if self.specs[name] == name]
        latest = dict.fromkeys(names)
        latest.update(fetch_latest_concurrent(unversioned, fetch_npm_latest))
        return latest

    @override
    def sync(self, to_install: list[str], to_upgrade: list[str]) -> SyncOutcome:
        targets = [self.specs[name] for name in to_install + to_upgrade]
        pnpm = find_binary("pnpm")
        if not pnpm:
            if targets:
                return SyncOutcome(
                    "hard_fail",
                    "pnpm not found — the [url] section (pnpm) must run before [pnpm].",
                )
            return SyncOutcome("ok")

        ensure_pnpm_home_env()
        if not targets:
            return SyncOutcome("ok")

        logger.info(
            "Installing/upgrading {count} pnpm global(s): {names}", count=len(targets), names=", ".join(targets)
        )
        shell.stream([str(pnpm), "add", "-g", "--ignore-scripts", *targets])
        return SyncOutcome("ok")
