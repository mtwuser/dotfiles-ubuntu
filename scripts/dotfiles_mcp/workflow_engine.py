"""Task-branch workflow onboarding and section-level upstream template reconciliation.

Specification: docs/architecture/04_compaction_surface_and_promotion_engines.md
"""

import json
import re
from pathlib import Path
from typing import Any

VALID_TASK_TRACKERS: tuple[str, ...] = (
    "WORKTASK.md",
    "BACKLOG.md",
    "WORKROAD.md",
    "ROADMAP.md",
)
_TASK_LINE_RE = re.compile(r"^(\s*-\s*\[)([ /xX])(\]\s+)(.+)$")
_ACTIVE_TASK_SECTION_RE = re.compile(r"\n*## Active Task\n[\s\S]*$", re.MULTILINE)


def _derive_branch_slug(task_text: str) -> str:
    """Derive a clean kebab-case branch slug from a markdown task description."""
    plain = re.sub(r"[*_`~]", "", task_text)
    plain = re.sub(r"Delegated from\s+[a-z0-9-]+\s*\([^)]*\)", "", plain, flags=re.IGNORECASE)
    tokens = [tok for tok in re.split(r"[^a-z0-9]+", plain.lower()) if tok]
    slug = "-".join(tokens[:7])[:48].strip("-")
    return slug or "work-item"


def start_task_workflow(
    workspace_dir: Path,
    *,
    task_query: str,
    tracker: str = "WORKTASK.md",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Claim a task in <tracker>, mark it [/], update SESSION.md, and return branch metadata."""
    clean_q = task_query.strip()
    if not clean_q:
        raise ValueError("task_query must be a non-empty string")
    if tracker not in VALID_TASK_TRACKERS:
        raise ValueError(f"Invalid tracker {tracker!r}: must be one of {VALID_TASK_TRACKERS}")

    ws = workspace_dir.resolve()
    trk_file = ws / tracker
    if not trk_file.is_file():
        raise ValueError(f"Tracker file not found: {trk_file}")

    m_path = ws / "system" / "mcp-layer.json"
    m_data = json.loads(m_path.read_text(encoding="utf-8")) if m_path.is_file() else {}
    manifest = m_data if isinstance(m_data, dict) else {}
    layer_id = str(manifest.get("layer_id", ws.name))
    layer_role = str(manifest.get("layer_role", "project"))

    lines = trk_file.read_text(encoding="utf-8").splitlines()
    match_idx: int | None = None
    matched_body = ""
    for idx, line in enumerate(lines):
        m = _TASK_LINE_RE.match(line)
        if m and clean_q.lower() in line.lower():
            match_idx = idx
            matched_body = m.group(4).strip()
            lines[idx] = f"{m.group(1)}/{m.group(3)}{matched_body}"
            break

    if match_idx is None:
        raise ValueError(f"No task matching {clean_q!r} found in {tracker}")

    subtasks: list[str] = []
    for sub_line in lines[match_idx + 1 :]:
        if sub_line.startswith(("  ", "\t")) and sub_line.strip():
            subtasks.append(sub_line.strip())
        elif sub_line.strip():
            break

    slug = _derive_branch_slug(matched_body)
    branch_name = f"task/{slug}"
    git_cmd = f"git checkout -b {branch_name}"
    session_rel = ".agents/SESSION.md"
    session_file = ws / session_rel

    if not dry_run:
        trk_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        session_file.parent.mkdir(parents=True, exist_ok=True)
        existing_session = (
            session_file.read_text(encoding="utf-8")
            if session_file.is_file()
            else "# Session State Log\n\n## Session Log\n\n- Initialized.\n"
        )
        cleaned_session = _ACTIVE_TASK_SECTION_RE.sub("", existing_session).rstrip()
        active_block = (
            f"\n\n## Active Task\n"
            f"- **Tracker**: `{tracker}`\n"
            f"- **Branch**: `{branch_name}`\n"
            f"- **Task**: {matched_body}\n"
        )
        session_file.write_text(cleaned_session + active_block, encoding="utf-8")

    return {
        "workspace_dir": str(ws),
        "layer_id": layer_id,
        "layer_role": layer_role,
        "tracker": tracker,
        "task_query": clean_q,
        "matched_task": matched_body,
        "task_status": "in_progress",
        "subtasks": subtasks,
        "branch_name": branch_name,
        "git_branch_command": git_cmd,
        "session_file": session_rel,
        "dry_run": dry_run,
    }
