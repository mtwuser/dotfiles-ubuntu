"""Agnostic Surface Governance Projection across 0..N mounted layers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotfiles_mcp.capsule_engine import (
    _extract_axiom_skeleton,
    _extract_l3_links,
    _iter_markdown_sections,
)
from dotfiles_mcp.constants import (
    VALID_ARCHITECTURAL_PLANES,
    VALID_BINDING_MODES,
    VALID_ENVIRONMENTS,
    VALID_RESOLUTIONS,
)
from dotfiles_mcp.manifest_helpers import _merge_unique_strings
from dotfiles_mcp.surface_weaver import (
    _binding_matches_surface,
    _compute_binding_specificity,
    _infer_plane_from_path,
    _infer_scope_from_path,
)
from dotfiles_mcp.tools_unfold import UnfoldToolsMixin


class SurfaceToolsMixin(UnfoldToolsMixin):
    """Implements resolve_surface_governance tool with Lex Superior & Lex Specialis weaving."""

    def _resolve_binding_asset(
        self,
        rel_path: str,
        layer_dir: Path,
        layer_name: str,
        binding_id: str,
        asset_type: str,
        warnings_out: list[dict[str, Any]],
    ) -> Path | None:
        try:
            return self._resolve_safe_path(rel_path, layer_dir)
        except FileNotFoundError:
            warnings_out.append(
                self._emit_warning(
                    "WARN",
                    "SURFACE_ASSET_MISSING",
                    f"Binding {binding_id!r} in layer {layer_name!r} references missing "
                    f"{asset_type} {rel_path!r}.",
                    {
                        "layer": layer_name,
                        "binding_id": binding_id,
                        "asset_type": asset_type,
                        "path": rel_path,
                    },
                )
            )
            return None

    def _tool_resolve_surface_governance(self, args: dict[str, Any]) -> dict[str, Any]:
        target_path = str(args.get("target_path", "")).strip()
        explicit_plane = str(args.get("architectural_plane", "")).strip().lower()
        if explicit_plane and explicit_plane not in VALID_ARCHITECTURAL_PLANES:
            raise ValueError(
                f"Invalid architectural_plane {explicit_plane!r}: "
                f"must be one of {VALID_ARCHITECTURAL_PLANES}"
            )
        explicit_scope = str(args.get("scope", "")).strip().lower()
        raw_traits = args.get("traits") or []
        traits_list = sorted({str(t).strip().lower() for t in raw_traits if str(t).strip()})
        traits_set = set(traits_list)
        if not (target_path or explicit_plane or explicit_scope or traits_set):
            raise ValueError(
                "At least one surface selector ('target_path', 'architectural_plane', "
                "'scope', or 'traits') must be provided"
            )
        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )
        res_override = str(args.get("resolution_override", "")).strip().upper()
        if res_override and res_override not in VALID_RESOLUTIONS:
            raise ValueError(
                f"Invalid resolution_override {res_override!r}: must be one of {VALID_RESOLUTIONS}"
            )
        include_capsules = bool(args.get("include_capsules", True))
        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        key_required = bool(explicit_key or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip())
        secret = self._resolve_resonance_secret(explicit_key or None)
        env_scope = env_arg or "all"
        effective_plane = explicit_plane or _infer_plane_from_path(target_path)
        effective_scope = explicit_scope or _infer_scope_from_path(target_path)

        layer_dirs = [
            self.repo_dir,
            *(self.repo_dir / str(m["relative_path"]) for m in self._discover_mounted_layers()),
        ]
        participating_layers: list[dict[str, Any]] = []
        pruned_layers: list[dict[str, Any]] = []
        matched_records: list[tuple[int, int, int, str, Path, str, str, dict[str, Any]]] = []
        layer_guardrails_in_order: list[tuple[int, list[str]]] = []
        surface_warnings: list[dict[str, Any]] = []

        for ldir in layer_dirs:
            lname = "root" if ldir == self.repo_dir else ldir.name
            manifest = self._load_layer_manifest(ldir)
            layer_id = str(manifest.get("layer_id", lname))
            layer_role = str(manifest.get("layer_role", "service-node"))
            default_prec = 10 if ldir == self.repo_dir else 50
            layer_prec = int(manifest.get("precedence", default_prec))
            if not (0 <= layer_prec <= 100):
                raise ValueError(
                    f"Invalid layer precedence {layer_prec} in {lname!r}: must be 0..100"
                )
            raw_bindings = manifest.get("surface_bindings") or [
                {
                    "binding_id": f"{lname}-default-baseline",
                    "target_globs": ["**"],
                    "architectural_planes": ["*"],
                    "scopes": ["*"],
                    "traits": [],
                    "mode": "transversal",
                    "rule_files": ["antigravity/.gemini/config/AGENTS.md"],
                    "canonical_templates": [],
                    "invariants": list(manifest.get("baseline_guardrails", [])),
                }
            ]
            matched_in_layer: list[dict[str, Any]] = []
            for b in raw_bindings:
                b_prec = int(b.get("precedence", layer_prec))
                b_mode = str(b.get("mode", "transversal")).strip().lower()
                if not (0 <= b_prec <= 100):
                    raise ValueError(
                        f"Invalid binding precedence {b_prec} in {lname!r}: must be 0..100"
                    )
                if b_mode not in VALID_BINDING_MODES:
                    raise ValueError(
                        f"Invalid surface_binding mode {b_mode!r}: "
                        f"must be one of {VALID_BINDING_MODES}"
                    )
                if _binding_matches_surface(
                    b, target_path, effective_plane, effective_scope, traits_set
                ):
                    matched_in_layer.append(b)
            if not matched_in_layer:
                pruned_layers.append(
                    {
                        "layer": lname,
                        "layer_id": layer_id,
                        "layer_role": layer_role,
                        "precedence": layer_prec,
                    }
                )
                continue

            participating_layers.append(
                {
                    "layer": lname,
                    "layer_id": layer_id,
                    "layer_role": layer_role,
                    "precedence": layer_prec,
                    "matched_bindings_count": len(matched_in_layer),
                }
            )
            env_g = (
                manifest.get("environments", {}).get(env_arg, {}).get("default_guardrails", [])
                if env_arg
                else []
            )
            layer_guardrails_in_order.append(
                (layer_prec, [*manifest.get("baseline_guardrails", []), *env_g])
            )
            for b in matched_in_layer:
                b_prec = int(b.get("precedence", layer_prec))
                m_rank = (
                    0 if str(b.get("mode", "transversal")).strip().lower() == "authoritative" else 1
                )
                spec_score = _compute_binding_specificity(b)
                matched_records.append(
                    (b_prec, m_rank, -spec_score, lname, ldir, layer_id, layer_role, b)
                )

        participating_layers.sort(key=lambda item: (int(item["precedence"]), str(item["layer_id"])))
        matched_records.sort(
            key=lambda rec: (rec[0], rec[1], rec[2], rec[5], str(rec[7].get("binding_id", "")))
        )
        layer_guardrails_in_order.sort(key=lambda item: item[0])

        collision_groups: dict[tuple[int, str], list[str]] = {}
        for b_prec, m_rank, _, lname, *_ in matched_records:
            c_key = (b_prec, "authoritative" if m_rank == 0 else "transversal")
            collision_groups[c_key] = _merge_unique_strings(
                collision_groups.get(c_key, []), [lname]
            )
        for (c_prec, c_mode), c_layers in sorted(collision_groups.items()):
            if len(c_layers) > 1:
                surface_warnings.append(
                    self._emit_warning(
                        "WARN",
                        "SURFACE_PRECEDENCE_COLLISION",
                        f"Multiple layers {c_layers} matched surface at identical "
                        f"precedence={c_prec} and mode={c_mode!r}; resolved via Lex Specialis "
                        "(specificity_score) then layer_id. Assign distinct precedence (0..100) "
                        "in system/mcp-layer.json to establish unambiguous hierarchy.",
                        {"precedence": c_prec, "mode": c_mode, "layers": c_layers},
                    )
                )

        resolved_bindings: list[dict[str, Any]] = []
        invariant_groups: list[list[str]] = [g for _, g in layer_guardrails_in_order]
        template_groups: list[list[str]] = []
        returned_tokens = 0
        capsule_overhead_tokens = 0
        baseline_l2_tokens = 0
        surface_truncated = False

        for b_prec, m_rank, neg_spec, lname, ldir, layer_id, layer_role, b in matched_records:
            mode = "authoritative" if m_rank == 0 else "transversal"
            res = res_override or ("L2" if mode == "authoritative" else "L1")
            binding_id = str(b.get("binding_id", f"{lname}-binding"))
            b_invariants = [str(inv) for inv in b.get("invariants", []) if str(inv).strip()]
            raw_templates = [
                str(tpl) for tpl in b.get("canonical_templates", []) if str(tpl).strip()
            ]
            verified_templates: list[str] = []
            for tpl_rel in raw_templates:
                if (
                    self._resolve_binding_asset(
                        tpl_rel, ldir, lname, binding_id, "canonical_template", surface_warnings
                    )
                    is not None
                ):
                    verified_templates.append(tpl_rel)
            invariant_groups.append(b_invariants)
            template_groups.append([f"{lname}:{tpl}" for tpl in verified_templates])

            sections_out: list[dict[str, Any]] = []
            for rf_rel in b.get("rule_files", []):
                rf_path = self._resolve_binding_asset(
                    str(rf_rel), ldir, lname, binding_id, "rule_file", surface_warnings
                )
                if rf_path is None:
                    continue
                lines = rf_path.read_text(encoding="utf-8").splitlines()
                rel_in_layer = str(rf_path.relative_to(ldir)).replace("\\", "/")
                all_sections = _iter_markdown_sections(lines, rf_path.name)
                if len(all_sections) > 3:
                    surface_truncated = True
                for heading, start_line, end_line, body in all_sections[:3]:
                    joined = "\n".join(body)
                    if res == "L2" and len(joined) > 1500:
                        surface_truncated = True
                    l2_excerpt = joined[:1500]
                    l2_full = joined[:8000]
                    l1_skeleton = _extract_axiom_skeleton(heading, body)
                    l3_links = _extract_l3_links(rf_path, joined, ldir)
                    promoter_codon, capsule_token = self._build_section_capsule(
                        resolution=res,
                        layer_name=lname,
                        rel_in_layer=rel_in_layer,
                        heading=heading,
                        start_line=start_line,
                        end_line=end_line,
                        scope=effective_scope or "all",
                        l1_skeleton=l1_skeleton,
                        l2_excerpt=l2_excerpt,
                        l2_full=l2_full,
                        l3_links=l3_links,
                        env_scope=env_scope,
                        secret=secret,
                        key_required=key_required,
                    )
                    sec_entry: dict[str, Any] = {
                        "file": str(rf_path.relative_to(self.repo_dir)),
                        "layer": lname,
                        "section": heading,
                        "start_line": start_line,
                        "end_line": end_line,
                        "resolution": res,
                        "promoter_codon": promoter_codon,
                        "capsule_token": capsule_token if include_capsules else None,
                    }
                    if res == "L0":
                        sec_entry["surface_preview"] = (
                            f"{promoter_codon['codon']} ({', '.join(promoter_codon['tags'])})"
                        )
                    elif res == "L1":
                        sec_entry["axiom_skeleton"] = l1_skeleton
                        sec_entry["excerpt"] = l1_skeleton
                    else:
                        sec_entry["excerpt"] = l2_excerpt
                    sections_out.append(sec_entry)
                    returned_tokens += int(promoter_codon["token_estimates"][res])
                    baseline_l2_tokens += int(promoter_codon["token_estimates"]["L2"])
                    if include_capsules:
                        capsule_overhead_tokens += len(capsule_token) // 4

            resolved_bindings.append(
                {
                    "binding_id": binding_id,
                    "layer": lname,
                    "layer_id": layer_id,
                    "layer_role": layer_role,
                    "precedence": b_prec,
                    "specificity_score": -neg_spec,
                    "mode": mode,
                    "resolution": res,
                    "invariants": b_invariants,
                    "canonical_templates": verified_templates,
                    "sections": sections_out,
                }
            )

        if surface_truncated:
            surface_warnings.append(
                self._emit_warning(
                    "WARN",
                    "RESPONSE_TRUNCATED",
                    "Surface governance rule sections exceeded per-file cap (top 3 sections "
                    "or 1,500-char L2 excerpt). Unfold rcap1 capsules or call "
                    "'read_layer_document' for complete files.",
                    {"target_path": target_path, "effective_plane": effective_plane or "all"},
                )
            )

        tokens_saved = max(0, baseline_l2_tokens - returned_tokens)
        savings_pct = (
            round((tokens_saved / baseline_l2_tokens) * 100, 1) if baseline_l2_tokens > 0 else 0.0
        )
        payload = {
            "surface_query": {
                "target_path": target_path,
                "effective_plane": effective_plane or "all",
                "effective_scope": effective_scope or "all",
                "traits": traits_list,
                "environment": env_scope,
                "resolution_mode": res_override or "adaptive",
            },
            "precedence_policy": (
                "Numeric precedence (0..100, lower value = higher authority / Lex Superior), "
                "mode ('authoritative' before 'transversal'), and selector specificity_score "
                "(higher = more specific / Lex Specialis); authoritative defaults to L2, "
                "transversal defaults to L1."
            ),
            "participating_layers_count": len(participating_layers),
            "participating_layers": participating_layers,
            "pruned_layers_count": len(pruned_layers),
            "pruned_layers": pruned_layers,
            "resolved_bindings_count": len(resolved_bindings),
            "resolved_bindings": resolved_bindings,
            "effective_invariants": _merge_unique_strings(*invariant_groups),
            "canonical_templates": _merge_unique_strings(*template_groups),
            "token_compaction_metrics": {
                "resolution": res_override or "adaptive",
                "returned_estimated_tokens": returned_tokens,
                "capsule_overhead_tokens": capsule_overhead_tokens,
                "full_l2_baseline_tokens": baseline_l2_tokens,
                "tokens_saved": tokens_saved,
                "savings_pct": savings_pct,
            },
            "truncated": surface_truncated,
            "warnings": surface_warnings,
        }
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "isError": False,
        }
