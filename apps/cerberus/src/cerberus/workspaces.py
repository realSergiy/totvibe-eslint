"""Workspace membership from the repo's own manifests — pnpm workspace globs
(pnpm-workspace.yaml `packages`) and uv `[tool.uv.workspace] members` in
pyproject.toml — for checks that scope an analysis to workspace-registered
code. Manifest decode errors propagate so each check can report them as its
own targeted finding.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from cerberus.context import Context
    from cerberus.model import Repo


def ts_member_globs(repo: Repo, ctx: Context) -> list[str]:
    manifest = ctx.file(repo, "pnpm-workspace.yaml")
    if manifest is None:
        return []
    data = yaml.safe_load(manifest)
    packages: list[Any] = data.get("packages", []) if isinstance(data, dict) else []
    return [glob for glob in packages if isinstance(glob, str)] if isinstance(packages, list) else []


def uv_member_globs(repo: Repo, ctx: Context) -> list[str]:
    pyproject = ctx.file(repo, "pyproject.toml")
    if pyproject is None:
        return []
    workspace = tomllib.loads(pyproject).get("tool", {}).get("uv", {}).get("workspace", {})
    return list(workspace.get("members", []))
