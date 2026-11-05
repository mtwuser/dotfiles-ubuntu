"""Multi-resolution governance rule search and rcap1 capsule minting.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from dotfiles_mcp.capsules.capsule_engine import (
    _compute_digest16,
    _derive_chain_key,
    _extract_axiom_skeleton,
    _extract_codon_tags,
    _extract_l3_links,
    _iter_markdown_sections,
    _resolve_section_hierarchy,
    _seal_single_capsule,
    _slugify_codon,
)
from dotfiles_mcp.capsules.surface_weaver import (
    _verify_citation_receipt_claim,
    build_citation_receipt,
    load_citation_telemetry_radar,
    record_citation_telemetry_event,
)
from dotfiles_mcp.core.constants import (
    CAPSULE_ABSTRACTION_LAYERS,
    CAPSULE_DIGEST_HEX_LEN,
    CHARS_PER_TOKEN_ESTIMATE,
    CODON_STOPWORDS,
    EPISTEMIC_GRADE_LABELS,
    EPISTEMIC_GRADE_RANK,
    L1_FALLBACK_EST_TOKENS,
    L2_EXCERPT_MAX_CHARS,
    L2_SECTION_MAX_CHARS,
    LEVEL_MIN_TIER,
    MAX_QUERY_GOVERNANCE_MATCHES,
    NEXT_LEVEL_MAP,
    VALID_ENVIRONMENTS,
    VALID_EPISTEMIC_GRADES,
    VALID_RESOLUTIONS,
)
from dotfiles_mcp.core.manifest_helpers import (
    _iter_layer_template_dirs,
    _read_version,
    _resolve_effective_human_stack,
)
from dotfiles_mcp.mcp_node.node_base import MCPNodeBase


def infer_epistemic_grade(
    rel_file: str,
    section_title: str,
    section_body: str,
) -> tuple[str, str]:
    """Classify a rule or documentation section into universal epistemic grades E3..E0."""
    combined = f"{section_title}\n{section_body}"
    for explicit in VALID_EPISTEMIC_GRADES:
        if f"[{explicit}" in combined:
            return explicit, EPISTEMIC_GRADE_LABELS[explicit]
    rel_clean = rel_file.strip().lstrip("/")
    title_low = section_title.lower()
    if (
        rel_clean.startswith((".agents/proposals/", "roadmaps/"))
        or rel_clean in ("BACKLOG.md", "WORKROAD.md", "WORKTASK.md")
        or any(k in title_low for k in ("proposal", "hypothesis", "draft"))
    ):
        return "E0", EPISTEMIC_GRADE_LABELS["E0"]
    if (
        rel_clean.endswith(("AGENTS.md", "SECURITY.md", "human-base.md", "science-base.md"))
        or "**Mandate:**" in section_body
        or any(
            k in title_low for k in ("invariant", "mandate", "security", "axiom", "law", "statute")
        )
    ):
        return "E3", EPISTEMIC_GRADE_LABELS["E3"]
    if (
        rel_clean.startswith(("docs/architecture/", "docs/reference/", "corporate/", "surfaces/"))
        or "/rules/" in rel_clean
        or "Specification:" in section_body
        or any(
            k in title_low
            for k in ("contract", "specification", "schema", "1:1:1", "protocol", "standard")
        )
    ):
        return "E2", EPISTEMIC_GRADE_LABELS["E2"]
    return "E1", EPISTEMIC_GRADE_LABELS["E1"]


def verify_epistemic_context_claims(
    claims: list[dict[str, Any]],
    repo_dir: Path,
) -> dict[str, Any]:
    """Verify primary-source SHA-256 grounding, E3>E2>E1>E0 monotonicity, and cut-point bounds."""
    root_res = repo_dir.resolve()
    violations: list[dict[str, Any]] = []
    for idx, claim in enumerate(claims):
        c_id = str(claim.get("claim_id") or f"claim-{idx + 1}")
        grade = str(claim.get("epistemic_grade") or "E1").upper()
        over_grade = str(claim.get("overrides_grade") or "").upper()
        if over_grade in EPISTEMIC_GRADE_RANK and (
            EPISTEMIC_GRADE_RANK.get(grade, 1) < EPISTEMIC_GRADE_RANK[over_grade]
        ):
            violations.append({
                "claim_id": c_id, "code": "EPISTEMIC_PRECEDENCE_VIOLATION",
                "reason": f"Grade {grade} cannot override higher grade {over_grade}",
            })  # fmt: skip
        for tgt in claim.get("l3_targets") or []:
            rel_p = str(tgt.get("path") or "").strip().lstrip("/")
            exp_sha = str(tgt.get("sha256_prefix") or "").strip()
            cand = (root_res / rel_p).resolve() if rel_p else None
            live_sha = (
                hashlib.sha256(cand.read_bytes()).hexdigest()[:CAPSULE_DIGEST_HEX_LEN]
                if cand and cand.is_file() and cand.is_relative_to(root_res)
                else ""
            )
            if not live_sha or (exp_sha and not live_sha.startswith(exp_sha)):
                violations.append({
                    "claim_id": c_id, "code": "PRIMARY_SOURCE_HASH_MISMATCH",
                    "reason": f"L3 substrate {rel_p!r} missing or SHA-256 drifted",
                })  # fmt: skip
        if "cut_point" in claim and "observed_value" in claim:
            val, thr = float(claim["observed_value"]), float(claim["cut_point"])
            if val > thr:
                violations.append({
                    "claim_id": c_id, "code": "CUT_POINT_BOUNDARY_VIOLATION",
                    "reason": f"Observed {val} exceeds L3 cut-point threshold {thr}",
                })  # fmt: skip
        drift_v = _verify_citation_receipt_claim(claim, c_id)
        if drift_v:
            violations.append(drift_v)
        if cited := str(claim.get("citation_receipt") or "").strip():
            record_citation_telemetry_event(
                root_res,
                cited,
                is_stale_hit=bool(drift_v),
                is_proposal_friction=bool(claim.get("proposal_friction")),
                age_days=int(claim.get("age_days", 0)),
                count_citation=bool(claim.get("count_citation", True)),
            )
    return {
        "verified": not violations,
        "error_code": violations[0]["code"] if violations else None,
        "checked_claims_count": len(claims),
        "violations": violations,
        "abstraction_layers": dict(CAPSULE_ABSTRACTION_LAYERS),
        "citation_lifecycle_radar": load_citation_telemetry_radar(root_res),
    }


class CompactionToolsMixin(MCPNodeBase):
    """Implements capsule minting and query_governance_rules tool."""

    def _resolve_resonance_secret(self, explicit_key: str | None = None) -> bytes:
        raw_key = (
            (explicit_key or "").strip()
            or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip()
            or f"dotfiles-resonance-v1:{_read_version(self.repo_dir)}"
        )
        return raw_key.encode("utf-8")

    def _build_section_capsule(
        self,
        *,
        resolution: str,
        layer_name: str,
        rel_in_layer: str,
        heading: str,
        start_line: int,
        end_line: int,
        scope: str,
        l1_skeleton: str,
        l2_excerpt: str,
        l2_full: str,
        l3_links: list[dict[str, Any]],
        env_scope: str,
        secret: bytes,
        key_required: bool = False,
        heading_depth: int = 1,
        section_path: str = "",
    ) -> tuple[dict[str, Any], str]:
        l0_summary = f"[{layer_name}] {rel_in_layer} :: {heading}"
        l3_tokens = sum(int(item["estimated_tokens"]) for item in l3_links) + L1_FALLBACK_EST_TOKENS
        cost_map = {
            "L0": max(1, len(l0_summary) // CHARS_PER_TOKEN_ESTIMATE),
            "L1": max(1, len(l1_skeleton) // CHARS_PER_TOKEN_ESTIMATE),
            "L2": max(1, len(l2_excerpt) // CHARS_PER_TOKEN_ESTIMATE),
            "L3": l3_tokens,
        }
        tags = _extract_codon_tags(heading, l2_excerpt)
        ep_grade, ep_label = infer_epistemic_grade(rel_in_layer, heading, l2_excerpt)
        l3_targets = [
            {"path": str(item["path"]), "sha256_prefix": str(item["sha256"])} for item in l3_links
        ]
        promoter_codon = {
            "codon": f"AUG:{scope}:{_slugify_codon(heading)}:UAA", "layer": layer_name,
            "epistemic_grade": ep_grade, "epistemic_label": ep_label,
            "abstraction_layer": CAPSULE_ABSTRACTION_LAYERS[resolution],
            "heading_depth": heading_depth, "section_path": section_path or heading,
            "tags": tags, "has_l3_substrate": bool(l3_targets), "l3_links_count": len(l3_links),
            "l3_targets": l3_targets, "token_estimates": cost_map,
        }  # fmt: skip
        h0 = _compute_digest16(layer_name, rel_in_layer, heading)
        h1 = _compute_digest16(h0, l1_skeleton)
        h2 = _compute_digest16(h1, l2_full)
        h3 = _compute_digest16(h2, *(f"{item['path']}:{item['sha256']}" for item in l3_links))
        promoter_codon["citation_receipt"] = build_citation_receipt(
            layer_name, rel_in_layer, heading, h2, ep_grade
        )
        digest_by_level = {"L0": h0, "L1": h1, "L2": h2, "L3": h3}
        issuer_id = str(self._load_layer_manifest().get("layer_id", "root"))
        nxt, ph = NEXT_LEVEL_MAP[resolution], digest_by_level[resolution]
        min_tier = "pro" if (env_scope == "pro" and nxt == "L3") else LEVEL_MIN_TIER[nxt]
        hdr = {
            "lvl": resolution, "next": nxt, "iss": issuer_id, "lyr": layer_name,
            "sec": heading, "eg": ep_grade, "cap": min_tier,
            "env": env_scope, "kr": key_required, "ph": ph,
        }  # fmt: skip
        inner_lvl = {
            "ph": ph, "f": rel_in_layer, "s": start_line, "e": end_line,
            "h1": h1, "hd": digest_by_level,
        }  # fmt: skip
        ck = _derive_chain_key(secret, layer_name, resolution, ph, env_scope)
        return promoter_codon, _seal_single_capsule(hdr, inner_lvl, ck)

    def _tool_query_governance_rules(self, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", "")).strip()
        if not query:
            raise ValueError("'query' must be a non-empty string")
        scope = str(args.get("scope", "all"))
        resolution = str(args.get("resolution", "L2")).strip().upper() or "L2"
        if resolution not in VALID_RESOLUTIONS:
            raise ValueError(
                f"Invalid resolution {resolution!r}: must be one of {VALID_RESOLUTIONS}"
            )
        env_arg = str(args.get("environment", "")).strip().lower()
        if env_arg and env_arg not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment {env_arg!r}: must be one of {VALID_ENVIRONMENTS}"
            )
        min_ep_arg = str(args.get("min_epistemic_grade") or "E0").strip().upper()
        if min_ep_arg not in VALID_EPISTEMIC_GRADES:
            raise ValueError(
                f"Invalid min_epistemic_grade {min_ep_arg!r}: must be {VALID_EPISTEMIC_GRADES}"
            )
        min_ep_rank = EPISTEMIC_GRADE_RANK[min_ep_arg]
        env_scope = env_arg or "all"
        include_capsules = bool(args.get("include_capsules", True))
        explicit_key = (
            str(args["resonance_key"]).strip() if args.get("resonance_key") is not None else ""
        )
        key_required = bool(explicit_key or os.environ.get("DOTFILES_RESONANCE_KEY", "").strip())
        secret = self._resolve_resonance_secret(explicit_key or None)
        layer_arg = str(args.get("layer", "all")).strip() or "all"
        if layer_arg == "all":
            layer_dirs = [
                self.repo_dir,
                *(self.repo_dir / str(m["relative_path"]) for m in self._discover_mounted_layers()),
            ]
        else:
            layer_dirs = [self._resolve_layer_dir(layer_arg)]

        raw_tpath = str(args.get("target_path", "")).strip()
        branch_ref = str(args.get("branch_ref") or "").strip()
        dmcp_projection: dict[str, Any] | None = None
        source_items: list[tuple[str, Path, Path, str]] = []
        if branch_ref:
            branch_sha = ""
            for ldir in layer_dirs:
                lname = "root" if ldir == self.repo_dir else ldir.name
                b_sha, b_docs = self._list_git_branch_markdown_files(
                    branch_ref, scope=scope, target_path=raw_tpath, base_dir=ldir
                )
                branch_sha = branch_sha or b_sha
                for rel_p, doc_txt in b_docs:
                    source_items.append((lname, ldir, ldir / rel_p, doc_txt))
            dmcp_projection = {
                "branch_ref": branch_ref, "commit_sha": branch_sha, "zero_checkout": True,
            }  # fmt: skip
        else:
            candidate_files: list[tuple[str, Path, Path]] = []
            for ldir in layer_dirs:
                lname = "root" if ldir == self.repo_dir else ldir.name
                if raw_tpath:
                    candidate_files.append((lname, ldir, ldir / raw_tpath))
                if scope in ("all", "global"):
                    candidate_files.append(
                        (lname, ldir, ldir / "antigravity/.gemini/config/AGENTS.md")
                    )
                if scope in ("all", "templates"):
                    for _tname, tdir in _iter_layer_template_dirs(ldir):
                        for tf in sorted((tdir / "rules").glob("*.md")):
                            candidate_files.append((lname, ldir, tf))
                        for sf in sorted((tdir / "skills").rglob("*.md")) if scope == "all" else ():
                            candidate_files.append((lname, ldir, sf))
                if scope in ("all", "docs"):
                    if scope == "all":
                        candidate_files.append((lname, ldir, ldir / "README.md"))
                    doc_subs = ("docs", "corporate", "surfaces") if scope == "all" else ("docs",)
                    for sub in doc_subs:
                        for df in sorted((ldir / sub).rglob("*.md")):
                            candidate_files.append((lname, ldir, df))
            seen_files: set[tuple[str, Path]] = set()
            for lname, ldir, file_path in candidate_files:
                res_fp = file_path.resolve()
                if (
                    file_path.suffix == ".md"
                    and file_path.is_file()
                    and res_fp.is_relative_to(ldir.resolve())
                    and (lname, res_fp) not in seen_files
                ):
                    seen_files.add((lname, res_fp))
                    source_items.append(
                        (lname, ldir, file_path, file_path.read_text(encoding="utf-8"))
                    )

        matches: list[dict[str, Any]] = []
        excerpt_truncated = False
        q_lower = query.lower()
        q_tokens = [
            tok for tok in re.findall(r"[a-z0-9_-]{3,}", q_lower) if tok not in CODON_STOPWORDS
        ]
        t_set = {(ldir / raw_tpath).resolve() for ldir in layer_dirs} if raw_tpath else set()
        for lname, ldir, file_path, doc_text in source_items:
            res_fp = file_path.resolve()
            min_toks = 1 if (res_fp in t_set and len(q_tokens) >= 3) else 2
            lines = doc_text.splitlines()
            for heading, start_line, end_line, body in _iter_markdown_sections(
                lines, file_path.name
            ):
                h_depth, sec_path = _resolve_section_hierarchy(lines, start_line, heading)
                joined = "\n".join(body)
                haystack = f"{sec_path}\n{joined}".lower()
                if q_lower in haystack or (
                    len(q_tokens) >= 2 and sum(1 for t in q_tokens if t in haystack) >= min_toks
                ):
                    l2_excerpt, l2_full = (
                        joined[:L2_EXCERPT_MAX_CHARS],
                        joined[:L2_SECTION_MAX_CHARS],
                    )
                    l1_skeleton = _extract_axiom_skeleton(heading, body)
                    l3_links = _extract_l3_links(file_path, joined, ldir)
                    rel_in_layer = str(file_path.relative_to(ldir)).replace("\\", "/")
                    promoter_codon, capsule_token = self._build_section_capsule(
                        resolution=resolution, layer_name=lname, rel_in_layer=rel_in_layer,
                        heading=heading, start_line=start_line, end_line=end_line, scope=scope,
                        l1_skeleton=l1_skeleton, l2_excerpt=l2_excerpt, l2_full=l2_full,
                        l3_links=l3_links, env_scope=env_scope, secret=secret,
                        key_required=key_required, heading_depth=h_depth, section_path=sec_path,
                    )  # fmt: skip
                    ep_grade = str(promoter_codon["epistemic_grade"])
                    if EPISTEMIC_GRADE_RANK[ep_grade] < min_ep_rank:
                        continue
                    if resolution == "L2" and len(joined) > L2_EXCERPT_MAX_CHARS:
                        excerpt_truncated = True
                    compact_codon = {
                        "codon": promoter_codon["codon"], "tags": promoter_codon["tags"],
                        "has_l3_substrate": promoter_codon["has_l3_substrate"],
                        "l3_links_count": promoter_codon["l3_links_count"],
                        "token_estimates": promoter_codon["token_estimates"],
                    }  # fmt: skip
                    entry: dict[str, Any] = {
                        "file": str(file_path.relative_to(self.repo_dir)), "layer": lname,
                        "section": heading, "section_path": sec_path, "heading_depth": h_depth,
                        "epistemic_grade": ep_grade,
                        "epistemic_label": promoter_codon["epistemic_label"],
                        "abstraction_layer": promoter_codon["abstraction_layer"],
                        "citation_receipt": promoter_codon["citation_receipt"],
                        "l3_targets": promoter_codon["l3_targets"], "start_line": start_line,
                        "end_line": end_line, "promoter_codon": compact_codon,
                        "capsule_token": capsule_token if include_capsules else None,
                    }  # fmt: skip
                    if resolution == "L0":
                        entry["surface_preview"] = (
                            f"{promoter_codon['codon']} ({', '.join(promoter_codon['tags'])})"
                        )
                    elif resolution == "L1":
                        entry["axiom_skeleton"] = l1_skeleton
                        entry["excerpt"] = l1_skeleton
                    else:
                        entry["excerpt"] = l2_excerpt
                    matches.append(entry)

        hs_facets = _resolve_effective_human_stack(self.repo_dir)["facets"]
        is_acad = any(f.endswith((":M1", ":M2")) or f == "soft-socratic-coach" for f in hs_facets)
        consumer_viewpoint = "academic-tutor-m1-m2" if is_acad else "professional-scientific-m3-m4"
        matches.sort(
            key=lambda m: (
                0 if (is_acad and "docs/guides/" in str(m["file"])) else 1,
                -EPISTEMIC_GRADE_RANK[str(m["epistemic_grade"])],
                int(m["heading_depth"]) if resolution in ("L0", "L1") else 0,
                int(m["start_line"]),
            )
        )
        total_matches = len(matches)
        returned_matches = matches[:MAX_QUERY_GOVERNANCE_MATCHES]
        returned_tokens = sum(
            int(m["promoter_codon"]["token_estimates"][resolution]) for m in returned_matches
        )
        capsule_overhead_tokens = (
            sum(len(str(m["capsule_token"])) // CHARS_PER_TOKEN_ESTIMATE for m in returned_matches)
            if include_capsules
            else 0
        )
        baseline_l2_tokens = sum(
            int(m["promoter_codon"]["token_estimates"]["L2"]) for m in returned_matches
        )
        tokens_saved = max(0, baseline_l2_tokens - returned_tokens)
        savings_pct = (
            round((tokens_saved / baseline_l2_tokens) * 100, 1) if baseline_l2_tokens > 0 else 0.0
        )

        query_warnings: list[dict[str, Any]] = []
        if total_matches > MAX_QUERY_GOVERNANCE_MATCHES or excerpt_truncated:
            query_warnings.append(
                self._emit_warning(
                    "WARN",
                    "RESPONSE_TRUNCATED",
                    f"Query matched {total_matches} section(s) (returning top "
                    f"{min(total_matches, MAX_QUERY_GOVERNANCE_MATCHES)}). Narrow 'query', "
                    "'scope', or 'layer' to inspect full sections without truncation.",
                    {
                        "query": query,
                        "total_matches": total_matches,
                        "excerpt_truncated": excerpt_truncated,
                    },
                )
            )

        payload = {
            "query": query, "scope": scope, "layer": layer_arg, "resolution": resolution,
            "min_epistemic_grade": min_ep_arg, "consumer_viewpoint": consumer_viewpoint,
            "include_capsules": include_capsules,
            "dmcp_projection": dmcp_projection,
            "token_compaction_metrics": {
                "resolution": resolution, "returned_estimated_tokens": returned_tokens,
                "capsule_overhead_tokens": capsule_overhead_tokens,
                "full_l2_baseline_tokens": baseline_l2_tokens,
                "tokens_saved": tokens_saved, "savings_pct": savings_pct,
            },
            "total_matches_found": total_matches, "match_count": len(returned_matches),
            "truncated": bool(query_warnings), "warnings": query_warnings,
            "matches": returned_matches,
        }  # fmt: skip
        return {
            "content": [{"type": "text", "text": json.dumps(payload, indent=2)}],
            "isError": False,
        }
