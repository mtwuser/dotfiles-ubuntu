"""Base MCP node state, manifest loader, path containment, and prompt templates.

Specification: docs/architecture/03_contextual_mcp_and_federation.md
"""

from __future__ import annotations

import contextlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotfiles_mcp.core.catalogs import MCP_PROMPTS_CATALOG
from dotfiles_mcp.core.constants import (
    AGENTS_MD_MAX_BYTES,
    AGENTS_MD_WARN_BYTES,
    ALLOWED_READ_PREFIXES,
    ALLOWED_ROOT_FILES,
    GIT_CMD_TIMEOUT_SECONDS,
    LAYER_MANIFEST_CONTRACT_REV,
    MAX_LOG_FILE_BYTES,
    REPO_DIR,
    ROLE_DEFAULT_PRECEDENCE,
    SAFE_GIT_REF_RE,
)
from dotfiles_mcp.core.manifest_helpers import (
    _read_version,
    _resolve_template_dir,
    discover_layer_template_names,
)


class MCPNodeBase:
    """Core layer state, path-containment guard, and prompt provider."""

    def __init__(
        self,
        repo_dir: Path = REPO_DIR,
        layer_id_override: str | None = None,
        layer_role_override: str | None = None,
        log_dir: Path | None = None,
    ) -> None:
        """Initialize the MCP node base with repository path, overrides, and ephemeral store."""
        self.repo_dir = repo_dir.resolve()
        self.layer_id_override = layer_id_override
        self.layer_role_override = layer_role_override
        self.log_dir = log_dir.resolve() if log_dir is not None else None
        self._ephemeral_memory_store: dict[str, dict[str, Any]] = {}

    def _reap_expired_memory_forks(self, now_epoch: float | None = None) -> list[str]:
        now = now_epoch if now_epoch is not None else datetime.now(UTC).timestamp()
        reaped: list[str] = []
        for fid in list(self._ephemeral_memory_store):
            if now >= float(self._ephemeral_memory_store[fid].get("expires_at_epoch", 0.0)):
                self._ephemeral_memory_store.pop(fid, None)
                reaped.append(fid)
        return reaped

    def _write_jsonl(self, filename: str, record: dict[str, Any]) -> None:
        if self.log_dir is None:
            return
        with contextlib.suppress(OSError):
            self.log_dir.mkdir(parents=True, exist_ok=True)
            target = self.log_dir / filename
            if target.is_file() and target.stat().st_size >= MAX_LOG_FILE_BYTES:
                target.replace(self.log_dir / f"{filename}.1")
            with target.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")

    def _emit_warning(
        self,
        severity: str,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        alert = {
            "ts": datetime.now(UTC).isoformat(),
            "severity": severity,
            "code": code,
            "message": message,
            "details": details or {},
        }
        self._write_jsonl("mcp_alerts.jsonl", alert)
        return alert

    def _evaluate_layer_warnings(
        self,
        target_dir: Path,
        agents_bytes: int,
    ) -> list[dict[str, Any]]:
        warnings: list[dict[str, Any]] = []
        if agents_bytes > AGENTS_MD_MAX_BYTES:
            warnings.append(
                self._emit_warning(
                    "CRITICAL",
                    "TOKEN_BUDGET_EXCEEDED",
                    f"AGENTS.md is {agents_bytes} bytes (exceeds {AGENTS_MD_MAX_BYTES}-byte cap; "
                    "context truncation risk).",
                    {"agents_md_bytes": agents_bytes, "cap_bytes": AGENTS_MD_MAX_BYTES},
                )
            )
        elif agents_bytes >= AGENTS_MD_WARN_BYTES:
            warnings.append(
                self._emit_warning(
                    "WARN",
                    "TOKEN_BUDGET_NEAR_LIMIT",
                    f"AGENTS.md is {agents_bytes} bytes (>= {AGENTS_MD_WARN_BYTES}-byte warning "
                    f"threshold; {AGENTS_MD_MAX_BYTES - agents_bytes} bytes remaining).",
                    {"agents_md_bytes": agents_bytes, "cap_bytes": AGENTS_MD_MAX_BYTES},
                )
            )
        manifest = self._load_layer_manifest(target_dir)
        for tpl_name in manifest.get("default_stack_templates", []):
            if _resolve_template_dir(target_dir, str(tpl_name)) is None:
                warnings.append(
                    self._emit_warning(
                        "WARN",
                        "TEMPLATE_PACK_MISSING",
                        f"Configured default_stack_templates entry {tpl_name!r} was not found "
                        f"under templates/{tpl_name}.",
                        {"template": str(tpl_name)},
                    )
                )
        if target_dir == self.repo_dir:
            for entry in self._discover_mounted_layers():
                if not entry["has_upstream"]:
                    warnings.append(
                        self._emit_warning(
                            "WARN",
                            "SUBTREE_LINEAGE_WARNING",
                            f"Mounted subtree {entry['relative_path']!r} is missing "
                            "upstream_layer.repository in system/mcp-layer.json.",
                            {"layer": entry["name"]},
                        )
                    )
        return warnings

    def _load_layer_manifest(self, target_dir: Path | None = None) -> dict[str, Any]:
        base_dir = (target_dir or self.repo_dir).resolve()
        manifest_path = base_dir / "system" / "mcp-layer.json"
        default_prec = (
            ROLE_DEFAULT_PRECEDENCE["workstation"]
            if base_dir == self.repo_dir
            else ROLE_DEFAULT_PRECEDENCE["service-node"]
        )
        data: dict[str, Any] = {
            "schema_version": LAYER_MANIFEST_CONTRACT_REV,
            "layer_id": base_dir.name if base_dir != self.repo_dir else "dotfiles-ubuntu-default",
            "layer_role": "workstation",
            "precedence": default_prec,
            "description": "Declarative Ubuntu 26.04 LTS & Google Antigravity 2.0 Layer",
            "upstream_layer": {
                "layer_id": "mtwuser/dotfiles-ubuntu",
                "repository": "https://github.com/mtwuser/dotfiles-ubuntu.git",
                "branch": "master",
            },
            "mounted_layers_dir": "layers",
            "mounted_layers": [],
            "default_stack_templates": discover_layer_template_names(base_dir),
            "baseline_guardrails": [],
            "surface_bindings": [],
            "environments": {},
            "federated_mcps": [],
        }
        if manifest_path.is_file():
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        if str(data.get("schema_version")) != LAYER_MANIFEST_CONTRACT_REV:
            raise ValueError(
                f"Unsupported mcp-layer.json schema_version {data.get('schema_version')!r}: "
                f"expected {LAYER_MANIFEST_CONTRACT_REV!r}"
            )
        if base_dir == self.repo_dir:
            if self.layer_id_override:
                data["layer_id"] = self.layer_id_override
            if self.layer_role_override:
                data["layer_role"] = self.layer_role_override
        return data

    def _discover_mounted_layers(self) -> list[dict[str, Any]]:
        layers_dir = self.repo_dir / "layers"
        discovered: list[dict[str, Any]] = []
        if not layers_dir.is_dir():
            return discovered
        for sub in sorted(layers_dir.iterdir()):
            if not sub.is_dir() or sub.name.startswith("."):
                continue
            raw_manifest_path = sub / "system" / "mcp-layer.json"
            has_upstream = True
            if raw_manifest_path.is_file():
                raw_data = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
                if isinstance(raw_data, dict) and "upstream_layer" in raw_data:
                    up = raw_data.get("upstream_layer")
                    has_upstream = bool(isinstance(up, dict) and up.get("repository"))
            sub_manifest = self._load_layer_manifest(sub)
            discovered.append(
                {
                    "name": sub.name,
                    "relative_path": f"layers/{sub.name}",
                    "layer_id": sub_manifest.get("layer_id", sub.name),
                    "layer_role": sub_manifest.get("layer_role", "service-node"),
                    "precedence": int(
                        sub_manifest.get("precedence", ROLE_DEFAULT_PRECEDENCE["service-node"])
                    ),
                    "surface_binding_count": len(sub_manifest.get("surface_bindings", [])),
                    "version": _read_version(sub),
                    "has_docs": (sub / "docs").is_dir(),
                    "has_rules": (sub / "antigravity/.gemini/config/AGENTS.md").is_file(),
                    "has_templates": (sub / "templates").is_dir(),
                    "has_upstream": has_upstream,
                    "federated_mcp_count": len(sub_manifest.get("federated_mcps", [])),
                }
            )
        discovered.sort(key=lambda item: (int(item["precedence"]), str(item["name"])))
        return discovered

    def _resolve_workspace_override(self, workspace_dir: object) -> Path:
        raw = str(workspace_dir or "").strip()
        if not raw:
            return self.repo_dir
        candidate = Path(raw).expanduser().resolve()
        has_marker = (
            (candidate / "system" / "mcp-layer.json").is_file()
            or (candidate / ".agents").is_dir()
            or (candidate / ".git").exists()
        )
        if not candidate.is_dir() or not has_marker:
            raise ValueError(
                f"Invalid workspace_dir {raw!r}: must be an existing layer or git/agent workspace."
            )
        return candidate

    def _resolve_layer_dir(self, layer: str | None = None) -> Path:
        clean = (layer or "").strip()
        root_id = str(self._load_layer_manifest().get("layer_id", ""))
        if not clean or clean in ("root", "self", root_id):
            return self.repo_dir
        for entry in self._discover_mounted_layers():
            if clean in (entry["name"], entry["layer_id"]):
                return (self.repo_dir / str(entry["relative_path"])).resolve()
        raise ValueError(f"Unknown or unmounted layer: {layer!r}")

    def _validate_safe_rel_path(
        self, relative_path: str, base_dir: Path | None = None
    ) -> tuple[Path, Path, str]:
        target_base = (base_dir or self.repo_dir).resolve()
        clean_rel = relative_path.strip().lstrip("/")
        if not clean_rel or ".." in Path(clean_rel).parts:
            raise ValueError(f"Invalid or forbidden relative path: {relative_path!r}")
        candidate = (target_base / clean_rel).resolve()
        if not candidate.is_relative_to(target_base):
            raise ValueError(f"Path escapes repository root: {relative_path!r}")
        rel_str = str(candidate.relative_to(target_base)).replace("\\", "/")
        allowed = rel_str in ALLOWED_ROOT_FILES or any(
            rel_str.startswith(prefix) for prefix in ALLOWED_READ_PREFIXES
        )
        if not allowed:
            raise ValueError(
                f"Access denied for {relative_path!r}: only docs/, templates/, "
                "antigravity/, system/, and root documentation files are readable."
            )
        return target_base, candidate, rel_str

    def _resolve_safe_path(self, relative_path: str, base_dir: Path | None = None) -> Path:
        _, candidate, rel_str = self._validate_safe_rel_path(relative_path, base_dir)
        if not candidate.is_file():
            raise FileNotFoundError(f"Document not found: {rel_str}")
        return candidate

    def _resolve_git_branch_commit_sha(
        self, branch_ref: str, target_base: Path
    ) -> tuple[str, str, str]:
        clean_ref = branch_ref.strip()
        if (
            not clean_ref
            or ".." in clean_ref
            or clean_ref.startswith("-")
            or not SAFE_GIT_REF_RE.match(clean_ref)
        ):
            raise ValueError(f"Invalid or unsafe branch_ref: {branch_ref!r}")
        git_bin = shutil.which("git") or "git"
        sha_proc = subprocess.run(  # noqa: S603
            [git_bin, "-C", str(target_base), "rev-parse", "--verify", f"{clean_ref}^{{commit}}"],
            capture_output=True,
            text=True,
            timeout=GIT_CMD_TIMEOUT_SECONDS,
            check=False,
        )
        if sha_proc.returncode != 0:
            raise ValueError(
                f"DMCP_BRANCH_REF_NOT_FOUND: Git ref {clean_ref!r} not found in {target_base.name}"
            )
        return git_bin, clean_ref, sha_proc.stdout.strip()

    def _read_git_branch_document(
        self, relative_path: str, branch_ref: str, base_dir: Path | None = None
    ) -> tuple[str, str]:
        target_base, _, rel_str = self._validate_safe_rel_path(relative_path, base_dir)
        git_bin, clean_ref, commit_sha = self._resolve_git_branch_commit_sha(
            branch_ref, target_base
        )
        blob_proc = subprocess.run(  # noqa: S603
            [git_bin, "-C", str(target_base), "show", f"{clean_ref}:{rel_str}"],
            capture_output=True,
            text=True,
            timeout=GIT_CMD_TIMEOUT_SECONDS,
            check=False,
        )
        if blob_proc.returncode != 0:
            raise FileNotFoundError(f"Document {rel_str!r} not found on branch_ref {clean_ref!r}")
        return blob_proc.stdout, commit_sha

    def _list_git_branch_markdown_files(
        self,
        branch_ref: str,
        *,
        scope: str = "all",
        target_path: str = "",
        base_dir: Path | None = None,
    ) -> tuple[str, list[tuple[str, str]]]:
        target_base = (base_dir or self.repo_dir).resolve()
        git_bin, clean_ref, commit_sha = self._resolve_git_branch_commit_sha(
            branch_ref, target_base
        )
        tree_proc = subprocess.run(  # noqa: S603
            [git_bin, "-C", str(target_base), "ls-tree", "-r", "--name-only", clean_ref],
            capture_output=True,
            text=True,
            timeout=GIT_CMD_TIMEOUT_SECONDS,
            check=False,
        )
        clean_tpath = target_path.strip().lstrip("/")
        docs_out: list[tuple[str, str]] = []
        for raw_line in tree_proc.stdout.splitlines():
            rel_p = raw_line.strip()
            if not rel_p.endswith(".md"):
                continue
            in_scope = (
                (rel_p == clean_tpath)
                or (scope in ("all", "global") and rel_p == "antigravity/.gemini/config/AGENTS.md")
                or (scope in ("all", "templates") and rel_p.startswith("templates/"))
                or (
                    scope in ("all", "docs")
                    and (
                        rel_p.startswith("docs/")
                        or (
                            scope == "all"
                            and (
                                rel_p == "README.md"
                                or rel_p.startswith(("corporate/", "surfaces/"))
                            )
                        )
                    )
                )
            )
            if in_scope:
                with contextlib.suppress(ValueError, FileNotFoundError):
                    txt, _ = self._read_git_branch_document(rel_p, clean_ref, target_base)
                    docs_out.append((rel_p, txt))
        return commit_sha, docs_out

    def list_prompts(self) -> list[dict[str, Any]]:
        """Return the catalog of MCP prompts exposed by this layer node."""
        return [dict(item) for item in MCP_PROMPTS_CATALOG]

    def get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render a structured MCP prompt message sequence for the requested prompt name."""
        args = arguments or {}
        if name == "orient-on-layer":
            task = args.get("task_description", "general architectural exploration")
            return {
                "description": f"Layer orientation for: {task}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Task context: {task}\n\n"
                                "1. Call the `get_layer_overview` tool to inspect this node's "
                                "4-Channel Executive Digest.\n"
                                "2. Read the `dotfiles://docs/index` resource to locate the "
                                "relevant normative specification before proposing changes."
                            ),
                        },
                    }
                ],
            }

        if name == "audit-container-or-node":
            service = args.get("target_service", "current node")
            return {
                "description": f"Environment & governance drift audit for {service}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Perform a read-only drift audit on `{service}`:\n"
                                "1. Call `audit_node_drift` with `mode='both'`.\n"
                                "2. Read `dotfiles://system/manifests` and `dotfiles://layer/identity`.\n"
                                "3. Summarize any symlink, package, or repository discrepancies."
                            ),
                        },
                    }
                ],
            }

        if name == "orchestrate-federated-mcps":
            goal = args.get("workflow_goal", "multi-service operation")
            env_scope = args.get("environment", "pre")
            layer_scope = args.get("layer", "all")
            return {
                "description": f"Guardrailed MCP orchestration for: {goal}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Workflow goal: {goal}\n\n"
                                "Before calling any downstream database, cloud, or service MCP:\n"
                                f"1. Call `discover_federated_mcps(layer={layer_scope!r}, "
                                f"environment={env_scope!r})` on this layer MCP.\n"
                                "2. Verify each target MCP's `activation_policy` "
                                "(`when_to_invoke` / `avoid_when`) and extract its merged "
                                "`effective_guardrails`.\n"
                                "3. Call `query_governance_rules` for any referenced rules and "
                                "enforce them strictly throughout execution."
                            ),
                        },
                    }
                ],
            }

        raise ValueError(f"Unknown prompt name: {name!r}")
