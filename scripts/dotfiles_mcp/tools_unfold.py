"""Progressive rcap1 context capsule decryption and decompression (L0->L1->L2->L3).

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import zlib
from typing import Any

from dotfiles_mcp.capsule_engine import (
    CapsuleError,
    _compute_digest16,
    _derive_chain_key,
    _extract_axiom_skeleton,
    _extract_l3_links,
    _iter_markdown_sections,
    _parse_capsule_envelope,
    _xor_keystream,
)
from dotfiles_mcp.constants import (
    AGENT_TIER_RANK,
    LEVEL_INDEX,
    LEVEL_MIN_TIER,
    NEXT_LEVEL_MAP,
    VALID_AGENT_TIERS,
    VALID_CAPSULE_LEVELS,
    VALID_ENVIRONMENTS,
)
from dotfiles_mcp.manifest_helpers import _merge_unique_strings
from dotfiles_mcp.tools_compaction import CompactionToolsMixin


class UnfoldToolsMixin(CompactionToolsMixin):
    """Implements unfold_context_capsule tool with capability and hash-chain verification."""

    def _tool_unfold_context_capsule(self, args: dict[str, Any]) -> dict[str, Any]:
        raw_token = str(args.get("capsule_token", "")).strip()
        try:
            header, signing_prefix, cipher_bytes, sig_hex = _parse_capsule_envelope(raw_token)
        except ValueError as exc:
            self._emit_warning(
                "WARN",
                "CAPSULE_CHAIN_BROKEN",
                str(exc),
                {"capsule_prefix": raw_token[:32]},
            )
            raise CapsuleError(
                f"{exc} [Recovery: Re-run query_governance_rules to obtain a fresh capsule.]"
            ) from exc

        cur_lvl = str(header["lvl"])
        default_next = str(header.get("next", NEXT_LEVEL_MAP[cur_lvl]))
        target_level = str(args.get("target_level") or default_next).strip().upper()
        if target_level not in VALID_CAPSULE_LEVELS:
            raise ValueError(
                f"Invalid target_level {target_level!r}: must be one of {VALID_CAPSULE_LEVELS}"
            )

        agent_tier = str(args.get("agent_tier", "inherit")).strip().lower() or "inherit"
        if agent_tier not in VALID_AGENT_TIERS:
            raise ValueError(
                f"Invalid agent_tier {agent_tier!r}: must be one of {VALID_AGENT_TIERS}"
            )

        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )

        expected_issuer = str(self._load_layer_manifest().get("layer_id", "root"))
        cap_issuer = str(header.get("iss") or expected_issuer)
        if cap_issuer != expected_issuer:
            msg = (
                f"Cross-node capsule mismatch: capsule was issued by MCP node {cap_issuer!r}, "
                f"but this MCP server is {expected_issuer!r}. "
                "[Recovery: Invoke unfold_context_capsule on the issuing MCP server node.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "issuer_node_mismatch", "capsule_issuer": cap_issuer},
            )
            raise CapsuleError(msg)

        cap_env = str(header.get("env", "all"))
        if cap_env != "all" and env_arg != cap_env:
            msg = (
                f"Capsule is bound to environment {cap_env!r}; "
                f"cannot unfold with environment={env_arg or 'unspecified'!r}. "
                f"[Recovery: Pass environment={cap_env!r}.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "environment_mismatch", "capsule_env": cap_env},
            )
            raise CapsuleError(msg)

        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        env_key = os.environ.get("DOTFILES_RESONANCE_KEY", "").strip()
        if header.get("kr") is True and not (explicit_key or env_key):
            msg = (
                "Capsule requires an explicit resonance_key (header.kr=true), "
                "but none was provided via arguments or DOTFILES_RESONANCE_KEY. "
                "[Recovery: Provide resonance_key or re-query without key gating.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "missing_resonance_key", "level": cur_lvl},
            )
            raise CapsuleError(msg)

        secret = self._resolve_resonance_secret(explicit_key or None)
        hdr_layer = str(header.get("lyr", "root"))
        step_key = _derive_chain_key(secret, hdr_layer, cur_lvl, str(header.get("ph", "")), cap_env)
        expected_sig = hmac.new(
            step_key, signing_prefix.encode("ascii"), hashlib.sha256
        ).hexdigest()[:24]
        if not hmac.compare_digest(sig_hex, expected_sig):
            msg = (
                "Capsule resonance signature verification failed "
                "(invalid resonance_key or tampered capsule). "
                "[Recovery: Verify resonance_key or re-run query_governance_rules.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_RESONANCE_DENIED",
                msg,
                {"reason": "hmac_mismatch", "level": cur_lvl},
            )
            raise CapsuleError(msg)

        if target_level == "L0":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "unfolded_level": "L0",
                                "unfold_chain": [],
                                "decrypted_hops": 0,
                                "chain_verified": True,
                                "truncated": False,
                                "warnings": [],
                                "promoter_header": header,
                                "next_capsule_token": raw_token,
                            },
                            indent=2,
                        ),
                    }
                ],
                "isError": False,
            }

        if LEVEL_INDEX[target_level] <= LEVEL_INDEX[cur_lvl]:
            raise ValueError(
                f"target_level {target_level!r} must be deeper than capsule level {cur_lvl!r} "
                "(or 'L0' for promoter inspection)"
            )

        required_tier = (
            "pro" if (cap_env == "pro" and target_level == "L3") else LEVEL_MIN_TIER[target_level]
        )
        if AGENT_TIER_RANK[agent_tier] < AGENT_TIER_RANK[required_tier]:
            msg = (
                f"Agent tier {agent_tier!r} is insufficient to unfold {target_level!r} "
                f"(requires {required_tier!r} per AGENTS.md §13 Model Delegation Discipline). "
                f"[Recovery: Request target_level='L1' or delegate to a {required_tier!r} agent.]"
            )
            self._emit_warning(
                "WARN",
                "CAPSULE_CAPABILITY_INSUFFICIENT",
                msg,
                {"agent_tier": agent_tier, "target_level": target_level},
            )
            raise CapsuleError(msg)

        step_lvl = cur_lvl
        step_header = header
        step_cipher = cipher_bytes
        unfold_chain: list[str] = []
        inner: dict[str, Any] = {}
        digest_map: dict[str, str] = {}
        layer_name = hdr_layer
        layer_dir = self._resolve_layer_dir(layer_name)
        rel_file = ""
        target_file = self.repo_dir
        start_line = 1
        end_line = 1
        heading = str(header.get("sec", ""))
        joined_section = ""
        l1_skeleton = ""
        l3_links: list[dict[str, Any]] = []
        line_drift_relocated = False

        while step_lvl != target_level:
            nxt = NEXT_LEVEL_MAP[step_lvl]
            try:
                decrypted_bytes = _xor_keystream(step_cipher, step_key)
                inner = json.loads(zlib.decompress(decrypted_bytes).decode("utf-8"))
            except Exception as exc:
                msg = (
                    f"Failed to decompress chained capsule interior at {step_lvl}->{nxt}: {exc} "
                    "[Recovery: Re-run query_governance_rules to mint a fresh capsule.]"
                )
                self._emit_warning("WARN", "CAPSULE_CHAIN_BROKEN", msg, {"level": step_lvl})
                raise CapsuleError(msg) from exc

            if not isinstance(inner, dict) or inner.get("ph") != step_header.get("ph"):
                msg = (
                    f"Capsule parent hash mismatch inside decrypted payload at {step_lvl}->{nxt} "
                    "[Recovery: Re-run query_governance_rules to mint a fresh capsule.]"
                )
                self._emit_warning("WARN", "CAPSULE_CHAIN_BROKEN", msg, {"level": step_lvl})
                raise CapsuleError(msg)

            if not digest_map:
                rel_file = str(inner.get("f", ""))
                target_file = self._resolve_safe_path(rel_file, layer_dir)
                all_lines = target_file.read_text(encoding="utf-8").splitlines()
                start_line = max(1, int(inner.get("s", 1)))
                end_line = min(len(all_lines), int(inner.get("e", len(all_lines))))
                section_lines = all_lines[start_line - 1 : end_line]
                l1_skeleton = _extract_axiom_skeleton(heading, section_lines)
                live_h0 = _compute_digest16(layer_name, rel_file, heading)
                live_h1 = _compute_digest16(live_h0, l1_skeleton)
                if live_h1 != inner.get("h1"):
                    _, start_line, end_line, section_lines = next(
                        (
                            sec
                            for sec in _iter_markdown_sections(all_lines, target_file.name)
                            if sec[0] == heading
                        ),
                        (heading, start_line, end_line, section_lines),
                    )
                    l1_skeleton = _extract_axiom_skeleton(heading, section_lines)
                    live_h1 = _compute_digest16(live_h0, l1_skeleton)
                    line_drift_relocated = live_h1 == inner.get("h1")
                joined_section = "\n".join(section_lines)
                l3_links = _extract_l3_links(target_file, joined_section, layer_dir)
                live_h2 = _compute_digest16(live_h1, joined_section[:8000])
                live_h3 = _compute_digest16(
                    live_h2,
                    *(f"{item['path']}:{item['sha256']}" for item in l3_links),
                )
                digest_map = {"L0": live_h0, "L1": live_h1, "L2": live_h2, "L3": live_h3}

            if inner.get("h_cur") != digest_map[step_lvl] or inner.get("h_next") != digest_map[nxt]:
                msg = (
                    f"Capsule chain digest mismatch at {step_lvl}->{nxt}: "
                    "underlying section drifted or payload tampered. "
                    "[Recovery: Re-run query_governance_rules(resolution='L2') for fresh content.]"
                )
                self._emit_warning(
                    "WARN",
                    "CAPSULE_CHAIN_BROKEN",
                    msg,
                    {"file": rel_file, "hop": f"{step_lvl}->{nxt}"},
                )
                raise CapsuleError(msg)

            unfold_chain.append(f"{step_lvl}->{nxt}")
            step_lvl = nxt
            if step_lvl != target_level:
                step_header, _, step_cipher, _ = _parse_capsule_envelope(str(inner["next_cap"]))
                step_key = _derive_chain_key(
                    secret, layer_name, step_lvl, digest_map[step_lvl], cap_env
                )

        next_capsule_token = str(inner["next_cap"]) if "next_cap" in inner else None
        l3_paths = [str(item["path"]) for item in l3_links]
        unfold_truncated = (target_level in ("L2", "L3") and len(joined_section) > 8000) or (
            target_level == "L3"
            and (len(l3_paths) > 5 or any(int(item["bytes"]) > 4000 for item in l3_links[:5]))
        )
        unfold_warnings: list[dict[str, Any]] = []
        if unfold_truncated:
            unfold_warnings.append(
                self._emit_warning(
                    "WARN",
                    "RESPONSE_TRUNCATED",
                    f"Unfolded {target_level} context for section {heading!r} exceeded inline "
                    "excerpt bounds (8,000-char section or 5x4,000-char L3 link cap). "
                    "Use 'read_layer_document' to inspect complete files.",
                    {
                        "file": str(target_file.relative_to(self.repo_dir)),
                        "target_level": target_level,
                        "section_chars": len(joined_section),
                        "l3_links_count": len(l3_paths),
                    },
                )
            )

        if target_level == "L1":
            unfolded_body: dict[str, Any] = {
                "file": str(target_file.relative_to(self.repo_dir)),
                "layer": layer_name,
                "section": heading,
                "start_line": start_line,
                "end_line": end_line,
                "axiom_skeleton": l1_skeleton,
                "l3_links_count": len(l3_links),
            }
        elif target_level == "L2":
            unfolded_body = {
                "file": str(target_file.relative_to(self.repo_dir)),
                "layer": layer_name,
                "section": heading,
                "start_line": start_line,
                "end_line": end_line,
                "full_section": joined_section[:8000],
                "l3_links": l3_links,
            }
        else:
            linked_docs: list[dict[str, Any]] = []
            for l3_path in l3_paths[:5]:
                l3_file = self._resolve_safe_path(l3_path, layer_dir)
                l3_text = l3_file.read_text(encoding="utf-8")
                linked_docs.append(
                    {
                        "path": str(l3_file.relative_to(self.repo_dir)),
                        "line_count": len(l3_text.splitlines()),
                        "excerpt": l3_text[:4000],
                    }
                )
            root_manifest = self._load_layer_manifest()
            layer_manifest = self._load_layer_manifest(layer_dir)
            effective_env = env_arg or (cap_env if cap_env != "all" else "")
            root_env_g = (
                root_manifest.get("environments", {})
                .get(effective_env, {})
                .get("default_guardrails", [])
                if effective_env
                else []
            )
            layer_env_g = (
                layer_manifest.get("environments", {})
                .get(effective_env, {})
                .get("default_guardrails", [])
                if effective_env
                else []
            )
            unfolded_body = {
                "file": str(target_file.relative_to(self.repo_dir)),
                "layer": layer_name,
                "section": heading,
                "full_section": joined_section[:8000],
                "linked_l3_documents": linked_docs,
                "effective_guardrails": _merge_unique_strings(
                    root_manifest.get("baseline_guardrails", []),
                    layer_manifest.get("baseline_guardrails", []),
                    root_env_g,
                    layer_env_g,
                ),
                "federated_mcps": layer_manifest.get("federated_mcps", []),
            }

        payload = {
            "unfolded_level": target_level,
            "unfold_chain": unfold_chain,
            "decrypted_hops": len(unfold_chain),
            "chain_verified": True,
            "line_drift_relocated": line_drift_relocated,
            "agent_tier": agent_tier,
            "environment": cap_env,
            "parent_digest": header.get("ph"),
            "level_digest": digest_map[target_level],
            "truncated": bool(unfold_warnings),
            "warnings": unfold_warnings,
            "promoter_header": header,
            "content": unfolded_body,
            "next_capsule_token": next_capsule_token,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "isError": False,
        }
