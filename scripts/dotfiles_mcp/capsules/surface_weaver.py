"""Stack-agnostic surface selector inference, matching, and Lex Specialis scoring.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from dotfiles_mcp.capsules.capsule_engine import _slugify_codon
from dotfiles_mcp.core.constants import (
    CITATION_LIFECYCLE_QUADRANTS,
    CITATION_TELEMETRY_REL_PATH,
    EPISTEMIC_GRADE_RANK,
    HOT_CITATION_THRESHOLD,
    PLANE_PATH_RULES,
    SPECIFICITY_WEIGHT_GLOB,
    SPECIFICITY_WEIGHT_PLANE,
    SPECIFICITY_WEIGHT_SCOPE,
    SPECIFICITY_WEIGHT_TRAIT,
    STALE_POLICY_REVIEW_DAYS,
    STRUCTURAL_PATH_SEGMENTS,
)
from dotfiles_mcp.core.layer_topology_helpers import (
    _classify_inter_layer_relationship,
    _match_manifest_actor_role,
    _resolve_layer_entity_identity,
)
from dotfiles_mcp.core.manifest_helpers import _load_manifest_dict, _resolve_template_dir


def collect_layer_effective_bindings(
    layer_dir: Path, manifest: dict[str, Any]
) -> list[dict[str, Any]]:
    """Merge manifest surface_bindings with active template.json recommended_surface_bindings."""
    effective, seen_ids = [], set[str]()
    candidates = list(manifest.get("surface_bindings") or [])
    for tpl_name in manifest.get("default_stack_templates", []):
        tpl_dir = _resolve_template_dir(Path(layer_dir), str(tpl_name))
        meta_file = tpl_dir / "template.json" if tpl_dir is not None else None
        if meta_file is not None and meta_file.is_file():
            loaded = json.loads(meta_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                candidates.extend(loaded.get("recommended_surface_bindings", []))
    for raw_b in candidates:
        if isinstance(raw_b, dict):
            bid = str(raw_b.get("binding_id", ""))
            if not bid or bid not in seen_ids:
                if bid:
                    seen_ids.add(bid)
                effective.append(raw_b)
    return effective


def _infer_plane_from_path(rel_path: str) -> str:
    norm = rel_path.strip().replace("\\", "/").lstrip("/").lower()
    return next((p for p, toks in PLANE_PATH_RULES if any(t in norm for t in toks)), "")


def _infer_scope_from_path(rel_path: str) -> str:
    segs = rel_path.strip().replace("\\", "/").strip("/").split("/")
    parts = [p for p in segs if p and "." not in p and p.lower() not in STRUCTURAL_PATH_SEGMENTS]
    return parts[0].lower() if parts else ""


def _glob_matches(rel_path: str, pattern: str) -> bool:
    norm_path = rel_path.strip().replace("\\", "/").lstrip("/")
    norm_pat = pattern.strip().replace("\\", "/").lstrip("/")
    collapsed = norm_pat.replace("/**/", "/").removeprefix("**/")
    return bool(
        norm_pat == "**"
        or fnmatch.fnmatchcase(norm_path, norm_pat)
        or fnmatch.fnmatchcase(norm_path, collapsed)
        or (norm_pat.endswith("/**") and norm_path.startswith(norm_pat[:-2]))
    )


def _binding_matches_surface(
    binding: dict[str, Any], target_path: str, plane: str, scope: str, traits: set[str]
) -> bool:
    globs = [str(g) for g in binding.get("target_globs", ["**"])]
    planes = [str(p).lower() for p in binding.get("architectural_planes", ["*"])]
    scopes = [str(s).lower() for s in binding.get("scopes", ["*"])]
    req_traits = {str(t).lower() for t in binding.get("traits", [])}
    glob_ok = not target_path or any(_glob_matches(target_path, g) for g in globs)
    plane_ok = not plane or "*" in planes or plane in planes
    glob_seg_ok = bool(
        target_path
        and scope
        and any(
            _glob_matches(target_path, g) and scope in g.lower().replace("\\", "/").split("/")
            for g in globs
            if g not in ("*", "**")
        )
    )
    scope_ok = not scope or "*" in scopes or scope in scopes or glob_seg_ok
    traits_ok = not req_traits or "*" in req_traits or bool(req_traits & traits)
    return glob_ok and plane_ok and scope_ok and traits_ok


def _compute_binding_specificity(binding: dict[str, Any]) -> int:
    globs = [str(g).strip() for g in binding.get("target_globs", ["**"]) if str(g).strip()]
    raw_planes = binding.get("architectural_planes", ["*"])
    planes = [str(p).strip().lower() for p in raw_planes if str(p).strip()]
    scopes = [str(s).strip().lower() for s in binding.get("scopes", ["*"]) if str(s).strip()]
    traits = [str(t).strip().lower() for t in binding.get("traits", []) if str(t).strip(" *")]
    glob_pts = SPECIFICITY_WEIGHT_GLOB if (globs and "**" not in globs and "*" not in globs) else 0
    plane_pts = SPECIFICITY_WEIGHT_PLANE if (planes and "*" not in planes) else 0
    scope_pts = SPECIFICITY_WEIGHT_SCOPE if (scopes and "*" not in scopes) else 0
    return glob_pts + plane_pts + scope_pts + (SPECIFICITY_WEIGHT_TRAIT * len(traits))


def match_authoritative_surface_bindings(
    layer_nodes: list[tuple[str, Path, dict[str, Any]]], target_paths: list[str]
) -> list[dict[str, Any]]:
    """Resolve authoritative layer bindings governing each path in target_paths."""
    matches: list[dict[str, Any]] = []
    for raw_path in target_paths:
        norm_path = raw_path.strip().replace("\\", "/").lstrip("/")
        if not norm_path:
            continue
        plane, scope = _infer_plane_from_path(norm_path), _infer_scope_from_path(norm_path)
        path_hits: list[tuple[int, int, str, dict[str, Any]]] = []
        for lid, ldir, manifest in layer_nodes:
            prec = int(manifest.get("precedence", 50))
            for b in collect_layer_effective_bindings(ldir, manifest):
                mode = str(b.get("mode", "authoritative")).strip().lower()
                globs = [str(g).strip() for g in b.get("target_globs", []) if str(g).strip()]
                has_specific_glob = bool(globs and "**" not in globs and "*" not in globs)
                if (
                    mode == "authoritative"
                    and has_specific_glob
                    and _binding_matches_surface(b, norm_path, plane, scope, set())
                ):
                    spec, bid = (
                        _compute_binding_specificity(b),
                        str(b.get("binding_id", f"{lid}-binding")),
                    )
                    item = {
                        "target_path": norm_path,
                        "owning_layer_id": lid,
                        "owning_layer_dir": str(ldir),
                        "precedence": prec,
                        "binding_id": bid,
                        "specificity_score": spec,
                    }
                    path_hits.append((prec, -spec, lid, item))
        if path_hits:
            path_hits.sort(key=lambda x: (x[0], x[1], x[2]))
            co_owners = list(
                {lid_k: h_item for _, _, lid_k, h_item in reversed(path_hits)}.values()
            )
            co_owners.reverse()
            matches.append({**co_owners[0], "co_owning_layers": co_owners})
    return matches


def _collect_manifest_authority_emails(manifest: dict[str, Any]) -> set[str]:
    """Extract lowercased owner/maintainer/validator emails from a layer manifest."""
    raw_auth = manifest.get("layer_authority")
    auth = raw_auth if isinstance(raw_auth, dict) else {}
    raw_roster = auth.get("roster")
    roster = raw_roster if isinstance(raw_roster, dict) else {}
    top_keys = ("authorized_emails", "maintainer_emails", "validator_emails")
    top_ems = {str(e).strip().lower() for k in top_keys for e in auth.get(k, []) if str(e).strip()}
    ros_ems = {
        str(m.get("email", "")).strip().lower()
        for k in ("owners", "maintainers", "validators")
        for m in roster.get(k, [])
        if isinstance(m, dict) and str(m.get("email", "")).strip()
    }
    return top_ems | ros_ems


def _resolve_co_owner_ledger_decision(
    wt_txt: str,
    t_path: str,
    own_id: str,
    own_emails: set[str],
    gov_root_id: str | None,
    is_internal: bool,
    is_single_owner: bool,
) -> str:
    """Resolve the latest WORKTASK.md governance decision for a co-owning layer on t_path."""
    decision = "PENDING"
    for ln in wt_txt.splitlines():
        m = re.search(r"GOVERNANCE DECISION:\s*(APPROVED|REJECTED|DEFERRED|BLOCKED)", ln)
        if m is not None and ((t_path in ln) or (own_id in ln)):
            dec = m.group(1)
            if (
                (own_id in ln)
                or any(em in ln.lower() for em in own_emails)
                or (is_single_owner and t_path in ln)
                or (is_internal and dec == "APPROVED" and bool(gov_root_id and gov_root_id in ln))
            ):
                decision = dec
    return decision


def evaluate_multilayer_surface_consensus(
    ws: Path,
    surf_hits: list[dict[str, Any]],
    *,
    clean_env: str,
    eff_actor: str,
    role_prof: dict[str, Any],
    wt_txt: str,
    parent_dir: Path | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Evaluate N-layer surface co-ownership, mutual entity scope, and consensus state."""
    ws_entity = _resolve_layer_entity_identity(ws, parent_dir=parent_dir)
    req_roles = ("owner",) if clean_env == "pro" else ("owner", "maintainer", "validator")
    participating: list[str] = []
    approved: list[str] = []
    divergent: list[str] = []
    pending: list[str] = []
    blocked: list[str] = []
    has_external_block = False
    surface_gates: list[str] = []

    for hit in surf_hits:
        t_path = str(hit["target_path"])
        co_owners: list[dict[str, Any]] = list(hit.get("co_owning_layers") or [hit])
        is_single = len(co_owners) == 1
        for co in co_owners:
            own_id, own_dir = str(co["owning_layer_id"]), Path(str(co["owning_layer_dir"]))
            own_prec = int(co["precedence"])
            participating.append(own_id)
            own_m = _load_manifest_dict(own_dir)
            own_role, _ = _match_manifest_actor_role(own_m, eff_actor)
            own_emails = _collect_manifest_authority_emails(own_m)
            own_entity = _resolve_layer_entity_identity(own_dir, own_m)
            rel = _classify_inter_layer_relationship(ws_entity, own_entity)
            is_internal = bool(rel["relationship_scope"] == "internal")
            gov_root = ws_entity.get("governing_root_id")
            dec = _resolve_co_owner_ledger_decision(
                wt_txt, t_path, own_id, own_emails, gov_root, is_internal, is_single
            )
            no_neg_dec = dec not in ("REJECTED", "DEFERRED", "BLOCKED")
            root_overarching = (
                is_internal
                and str(role_prof["effective_role"]) == "owner"
                and int(role_prof["precedence"]) <= own_prec
                and no_neg_dec
            )
            actor_ok = (own_role in req_roles) and no_neg_dec
            auth_ok = dec == "APPROVED" or actor_ok or root_overarching
            co_status = (
                "simulated_in_dev_tst"
                if clean_env in ("dev", "tst")
                else (
                    "blocked_deadlock"
                    if dec == "BLOCKED"
                    else (
                        "divergent_iteration_required"
                        if dec in ("REJECTED", "DEFERRED")
                        else ("authorized" if auth_ok else "blocked_surface_authority")
                    )
                )
            )
            co["status"], co["ledger_decision"], co["relationship"] = co_status, dec, rel
            if co_status in ("simulated_in_dev_tst", "authorized"):
                approved.append(own_id)
            elif co_status == "divergent_iteration_required":
                divergent.append(own_id)
                surface_gates.append(
                    f"INTER_DEPT_ITERATION_REQUIRED: '{t_path}' has constructive divergence "
                    f"from '{own_id}' ({dec}); iterate on the same task branch in dev/tst and "
                    "re-validate in pre."
                )
            elif co_status == "blocked_deadlock":
                blocked.append(own_id)
                if is_internal:
                    surface_gates.append(
                        f"CROSS_DEPT_ESCALATION_TO_ROOT_REQUIRED: '{t_path}' is BLOCKED by "
                        f"internal layer '{own_id}'; escalate 1-hop upward to governing Root 0 "
                        f"('{gov_root or 'root'}') for cross-CO arbitration and upstream rule "
                        "codification."
                    )
                elif rel["external_category"] == "external:public-government":
                    has_external_block = True
                    ext_root = rel["target_governing_root_id"]
                    surface_gates.append(
                        f"PUBLIC_REGULATORY_COMPLIANCE_REQUIRED: '{t_path}' is BLOCKED by "
                        f"external public-government layer '{own_id}' (root '{ext_root}'); "
                        "local Root 0 cannot override statutory public regulation."
                    )
                else:
                    has_external_block = True
                    ext_cat, ext_root = rel["external_category"], rel["target_governing_root_id"]
                    surface_gates.append(
                        f"CROSS_ENTITY_ESCALATION_REQUIRED: '{t_path}' is BLOCKED by external "
                        f"layer '{own_id}' ({ext_cat}, root '{ext_root}'); requires inter-entity "
                        "Root 0 alignment."
                    )
            else:
                pending.append(own_id)
                surface_gates.append(
                    f"SURFACE_AUTHORITY_REQUIRED: '{t_path}' is governed authoritatively by "
                    f"'{own_id}' (precedence {own_prec}); requires '{own_id}' "
                    f"{', '.join(req_roles)} or approved governance decision before '{clean_env}'."
                )
        statuses = [str(c["status"]) for c in co_owners]
        div_req = "divergent_iteration_required"
        hit["status"] = (
            "simulated_in_dev_tst"
            if clean_env in ("dev", "tst")
            else (
                "authorized"
                if all(s == "authorized" for s in statuses)
                else (
                    "blocked_deadlock"
                    if "blocked_deadlock" in statuses
                    else (div_req if div_req in statuses else "blocked_surface_authority")
                )
            )
        )

    in_status = "ITERATION_REQUIRED" if (divergent or pending) else "RECONCILED_FLOW"
    c_status = (
        "ESCALATE_INTER_ENTITY_ROOTS"
        if has_external_block
        else ("ESCALATE_TO_ROOT" if blocked else in_status)
    )
    gov_root_id = ws_entity.get("governing_root_id")
    esc_root = (
        gov_root_id if c_status in ("ESCALATE_TO_ROOT", "ESCALATE_INTER_ENTITY_ROOTS") else None
    )
    hint = (
        f"./scripts/layer-config.sh promote-from-project {ws} "
        f"--to-layer {gov_root_id or 'root'} --create-pr"
        if c_status == "ESCALATE_TO_ROOT"
        else ""
    )
    consensus = {
        "consensus_status": c_status,
        "workspace_entity": ws_entity,
        "participating_layers": list(dict.fromkeys(participating)),
        "approved_layers": list(dict.fromkeys(approved)),
        "divergent_layers": list(dict.fromkeys(divergent)),
        "pending_layers": list(dict.fromkeys(pending)),
        "blocked_layers": list(dict.fromkeys(blocked)),
        "escalation_target_root": esc_root,
        "rule_learning_hint": hint,
    }
    return consensus, surface_gates


def build_citation_receipt(
    layer_id: str, rel_file: str, section_heading: str, digest_hex: str, epistemic_grade: str
) -> str:
    """Build a canonical citation receipt (<layer>::<file>#<slug>@<digest>:<grade>)."""
    clean_rel = rel_file.strip().lstrip("/")
    return (
        f"{layer_id}::{clean_rel}#{_slugify_codon(section_heading)}@{digest_hex}:{epistemic_grade}"
    )


def _verify_citation_receipt_claim(claim: dict[str, Any], claim_id: str) -> dict[str, str] | None:
    cited = str(claim.get("citation_receipt") or "").strip()
    official_dig = str(claim.get("official_digest") or "").strip()
    if cited and official_dig and "@" in cited:
        cited_dig = cited.rsplit("@", 1)[1].split(":", 1)[0].strip()
        if not official_dig.startswith(cited_dig) and not cited_dig.startswith(official_dig):
            msg = f"Cited receipt digest {cited_dig!r} drifted from official {official_dig!r}"
            return {"claim_id": claim_id, "code": "CITATION_DRIFT_DETECTED", "reason": msg}
    return None


def evaluate_citation_telemetry_lifecycle(sections: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify sections across the 4 Age x Empirical Usage quadrants while preserving E3..E0."""
    classified: list[dict[str, Any]] = []
    counts = {q: 0 for q in CITATION_LIFECYCLE_QUADRANTS}
    for item in sections:
        grade = str(item.get("epistemic_grade") or "E1").upper()
        hits, age = int(item.get("citation_count", 0)), int(item.get("age_days", 0))
        has_fric = (
            int(item.get("stale_citation_hits", 0)) > 0
            or int(item.get("proposal_friction_count", 0)) > 0
        )
        cold_q = (
            "Q4_NORMATIVE_OBSOLESCENCE" if age > STALE_POLICY_REVIEW_DAYS else "Q3_EMERGING_NICHE"
        )
        quadrant = (
            "Q2_HIGH_FRICTION"
            if has_fric
            else ("Q1_HOT_CORE" if hits >= HOT_CITATION_THRESHOLD else cold_q)
        )
        counts[quadrant] += 1
        act = CITATION_LIFECYCLE_QUADRANTS[quadrant]
        classified.append(
            {**item, "epistemic_grade": grade, "quadrant": quadrant, "recommended_action": act}
        )
    dynamic_index = sorted(
        classified,
        key=lambda s: (
            -EPISTEMIC_GRADE_RANK.get(str(s["epistemic_grade"]), 1),
            -int(s.get("citation_count", 0)),
            int(s.get("age_days", 0)),
        ),
    )
    obs = [s for s in classified if s["quadrant"] == "Q4_NORMATIVE_OBSOLESCENCE"]
    fric = [s for s in classified if s["quadrant"] == "Q2_HIGH_FRICTION"]
    return {
        "epistemic_override_allowed": False,
        "quadrant_counts": counts,
        "obsolescence_candidates": obs,
        "high_friction_targets": fric,
        "dynamic_hot_index": dynamic_index,
    }


def record_citation_telemetry_event(
    repo_dir: Path,
    citation_receipt: str,
    *,
    is_stale_hit: bool = False,
    is_proposal_friction: bool = False,
    age_days: int = 0,
    count_citation: bool = True,
) -> dict[str, Any]:
    """Persist a citation usage, drift, or friction event in citation_stats.json."""
    stats_path = Path(repo_dir) / CITATION_TELEMETRY_REL_PATH
    raw = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.is_file() else {}
    sec_map: dict[str, dict[str, Any]] = dict(raw.get("sections") or {})
    sec_key = citation_receipt.split("@", 1)[0].strip()
    grade = citation_receipt.rsplit(":", 1)[1].strip() if ":" in citation_receipt else "E1"
    cur = dict(sec_map.get(sec_key) or {})
    c_inc = 1 if (count_citation and not is_stale_hit) else 0
    entry = {
        "section_key": sec_key,
        "citation_receipt": citation_receipt,
        "epistemic_grade": grade.upper(),
        "citation_count": int(cur.get("citation_count", 0)) + c_inc,
        "stale_citation_hits": int(cur.get("stale_citation_hits", 0)) + (1 if is_stale_hit else 0),
        "proposal_friction_count": int(cur.get("proposal_friction_count", 0))
        + (1 if is_proposal_friction else 0),
        "age_days": max(int(cur.get("age_days", 0)), int(age_days)),
    }
    sec_map[sec_key] = entry
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps({"sections": sec_map}, indent=2) + "\n", encoding="utf-8")
    return entry


def load_citation_telemetry_radar(repo_dir: Path) -> dict[str, Any]:
    """Load persisted .agents/telemetry/citation_stats.json and evaluate the Q1..Q4 radar."""
    stats_path = Path(repo_dir) / CITATION_TELEMETRY_REL_PATH
    raw = json.loads(stats_path.read_text(encoding="utf-8")) if stats_path.is_file() else {}
    sec_map = raw.get("sections") if isinstance(raw, dict) else None
    sections = list(sec_map.values()) if isinstance(sec_map, dict) else []
    return {
        "telemetry_file": CITATION_TELEMETRY_REL_PATH,
        "tracked_sections_count": len(sections),
        **evaluate_citation_telemetry_lifecycle(sections),
    }
