#!/usr/bin/env python3
"""Detect new campaign sessions, store deltas, and validate Ellara Campaign State across ~/source/ellara and ~/source/dnd."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

IGNORED_HIDDEN_DIRS = {".git", ".obsidian", ".agents", ".github"}
PREEXISTING_DUPLICATE_PATHS = {Path("Session Notes/Session 3/Session 3.md")}


def run_git_info(repo_root: Path) -> dict:
    """Return lightweight git head and dirty state for a repository."""
    if not (repo_root / ".git").exists():
        return {"exists": repo_root.exists(), "git": False}

    def _run(args: list[str]) -> str:
        res = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout.strip() if res.returncode == 0 else ""

    head = _run(["rev-parse", "--short", "HEAD"])
    subject = _run(["log", "-1", "--format=%s"])
    dirty_lines = [line for line in _run(["status", "--porcelain"]).splitlines() if line]
    return {
        "exists": True,
        "git": True,
        "head": head,
        "last_commit_subject": subject,
        "dirty_count": len(dirty_lines),
    }


def _unquote_yaml(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_frontmatter(path: Path) -> dict[str, object] | None:
    """Parse lightweight YAML frontmatter from a markdown file without external deps."""
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    fm_match = re.match(r"^---\s*\n(.*?)\n---(?:\s*\n|$)", text, re.DOTALL)
    if not fm_match:
        return None

    data: dict[str, object] = {}
    current_list_key: str | None = None
    for raw_line in fm_match.group(1).splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        list_match = re.match(r"^\s+-\s+(.*)$", raw_line)
        if list_match and current_list_key is not None:
            existing = data.setdefault(current_list_key, [])
            if isinstance(existing, list):
                existing.append(_unquote_yaml(list_match.group(1)))
            continue
        kv_match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", raw_line)
        if not kv_match:
            return None
        key = kv_match.group(1)
        val_raw = kv_match.group(2).strip()
        if val_raw == "":
            data[key] = []
            current_list_key = key
        else:
            current_list_key = None
            if re.fullmatch(r"-?\d+", val_raw):
                data[key] = int(val_raw)
            else:
                data[key] = _unquote_yaml(val_raw)
    return data


def read_last_analyzed_session(state_file: Path) -> int | None:
    """Read `last_analyzed_session` from YAML frontmatter of Ellara Current State.md."""
    fm = parse_frontmatter(state_file)
    if not fm:
        return None
    val = fm.get("last_analyzed_session")
    if isinstance(val, int):
        return val
    if isinstance(val, str) and val.isdigit():
        return int(val)
    return None


def _extract_js_string(block: str, key: str) -> str | None:
    """Extract a single- or double-quoted JS string field value, handling escapes."""
    pattern = rf"\b{re.escape(key)}\s*:\s*(['\"])((?:\\.|(?!\1).)*)\1"
    match = re.search(pattern, block, re.DOTALL)
    if not match:
        return None
    quote = match.group(1)
    raw = match.group(2)
    return raw.replace(f"\\{quote}", quote).replace("\\\\", "\\").strip()


def scan_ellara_sessions(ellara_root: Path) -> dict:
    """Inventory polished notes, raw notes, and transcripts in ~/source/ellara."""
    notes_dir = ellara_root / "Session Notes"
    polished: dict[int, str] = {}
    raw: dict[int, str] = {}
    transcripts: dict[int, str] = {}

    if notes_dir.is_dir():
        for path in sorted(notes_dir.iterdir()):
            if not path.is_file():
                continue
            m_pol = re.fullmatch(r"Session (\d+)\.md", path.name)
            if m_pol:
                polished[int(m_pol.group(1))] = str(path.relative_to(ellara_root))
                continue
            m_raw = re.fullmatch(r"Raw Session (\d+)\.md", path.name)
            if m_raw:
                raw[int(m_raw.group(1))] = str(path.relative_to(ellara_root))

        transcript_dir = notes_dir / "Transcripts"
        if transcript_dir.is_dir():
            for path in sorted(transcript_dir.iterdir()):
                if not path.is_file():
                    continue
                m_tr = re.fullmatch(r"Transcript Session (\d+)\.txt", path.name)
                if m_tr:
                    transcripts[int(m_tr.group(1))] = str(path.relative_to(ellara_root))

    return {
        "notes_dir_exists": notes_dir.is_dir(),
        "polished": polished,
        "raw": raw,
        "transcripts": transcripts,
        "latest_polished": max(polished) if polished else None,
        "latest_raw": max(raw) if raw else None,
        "latest_transcript": max(transcripts) if transcripts else None,
    }


def _parse_sessions_js(sessions_js: Path) -> list[dict]:
    """Parse session metadata entries from dnd/src/store/sessions.js."""
    if not sessions_js.is_file():
        return []
    text = sessions_js.read_text(encoding="utf-8")
    id_matches = list(re.finditer(r"\bid\s*:\s*(['\"])session-(\d+)\1", text))
    entries: list[dict] = []
    for idx, match in enumerate(id_matches):
        start = match.start()
        end = id_matches[idx + 1].start() if idx + 1 < len(id_matches) else len(text)
        chunk = text[start:end]
        num = int(match.group(2))
        up_match = re.search(r"\bupcoming\s*:\s*(true|false)\b", chunk)
        copy_fields = [
            field
            for field in ("homeRecap", "nextSteps", "storyBeat")
            if re.search(rf"\b{field}\s*:", chunk)
        ]
        entries.append(
            {
                "session": num,
                "id": f"session-{num}",
                "title": _extract_js_string(chunk, "title") or f"Session {num}",
                "subtitle": _extract_js_string(chunk, "subtitle") or "",
                "location": _extract_js_string(chunk, "location") or "",
                "date": _extract_js_string(chunk, "date") or "",
                "upcoming": up_match.group(1) == "true" if up_match else False,
                "summaryFile": _extract_js_string(chunk, "summaryFile"),
                "description": _extract_js_string(chunk, "description") or "",
                "copy_fields": copy_fields,
            }
        )
    return entries


def scan_dnd_sessions(dnd_root: Path) -> dict:
    """Inventory session markdown files and sessions.js metadata in ~/source/dnd."""
    if not dnd_root.is_dir():
        return {"exists": False}

    sessions_dir = dnd_root / "src" / "assets" / "sessions"
    summary_files: dict[int, str] = {}
    if sessions_dir.is_dir():
        for path in sorted(sessions_dir.iterdir()):
            if not path.is_file():
                continue
            m = re.fullmatch(r"session-(\d+)\.md", path.name)
            if m:
                summary_files[int(m.group(1))] = str(path.relative_to(dnd_root))

    metadata = _parse_sessions_js(dnd_root / "src" / "store" / "sessions.js")
    completed_meta = [m for m in metadata if not m["upcoming"]]
    upcoming_meta = [m for m in metadata if m["upcoming"]]
    completed_nums = set(summary_files) | {m["session"] for m in completed_meta}

    return {
        "exists": True,
        "summary_files": summary_files,
        "metadata": metadata,
        "latest_completed": max(completed_nums) if completed_nums else None,
        "upcoming": upcoming_meta[0] if upcoming_meta else None,
    }


def find_dnd_store_changes(dnd_root: Path, since_session: int) -> dict:
    """Find store entities, session copy fields, and view stages updated after `since_session`."""
    if not dnd_root.is_dir():
        return {"stores": {}, "views": {}}

    store_dir = dnd_root / "src" / "store"
    store_deltas: dict[str, list[dict]] = {}
    if store_dir.is_dir():
        for path in sorted(store_dir.glob("*.js")):
            if path.name == "config.js":
                continue
            if path.name == "sessions.js":
                session_entries = _parse_sessions_js(path)
                session_copy_changes: list[dict] = []
                for item in session_entries:
                    if item["session"] > since_session and item.get("copy_fields"):
                        session_copy_changes.append(
                            {
                                "id": item["id"],
                                "sessions": [item["session"]],
                                "copy_fields": item["copy_fields"],
                            }
                        )
                if session_copy_changes:
                    store_deltas[str(path.relative_to(dnd_root))] = session_copy_changes
                continue
            text = path.read_text(encoding="utf-8")
            id_matches = list(re.finditer(r"\bid\s*:\s*(['\"])([^'\"]+)\1", text))
            changed_entities: list[dict] = []
            for idx, match in enumerate(id_matches):
                start = match.start()
                end = id_matches[idx + 1].start() if idx + 1 < len(id_matches) else len(text)
                chunk = text[start:end]
                nums = sorted(
                    {
                        int(s)
                        for s in re.findall(r"\bsession\s*:\s*(\d+)\b", chunk)
                        if int(s) > since_session
                    }
                )
                if nums:
                    changed_entities.append({"id": match.group(2), "sessions": nums})
            if changed_entities:
                store_deltas[str(path.relative_to(dnd_root))] = changed_entities

    view_deltas: dict[str, list[int]] = {}
    views_dir = dnd_root / "src" / "views"
    if views_dir.is_dir():
        for name in ("StorySoFarView.vue", "HomeView.vue"):
            vpath = views_dir / name
            if not vpath.is_file():
                continue
            vtext = vpath.read_text(encoding="utf-8")
            nums: set[int] = set()
            for pat in (r"\bminSession\s*:\s*(\d+)", r"^\s*(\d+)\s*:\s*(?:\[|['\"`])"):
                for found in re.findall(pat, vtext, re.MULTILINE):
                    if int(found) > since_session:
                        nums.add(int(found))
            if nums:
                view_deltas[str(vpath.relative_to(dnd_root))] = sorted(nums)

    return {"stores": store_deltas, "views": view_deltas}


def build_delta_report(ellara_root: Path, dnd_root: Path) -> dict:
    """Compare analyzed state against both sister repositories."""
    state_file = ellara_root / "Ellara" / "Campaign State" / "Ellara Current State.md"
    last_analyzed = read_last_analyzed_session(state_file)
    baseline = last_analyzed if last_analyzed is not None else 0

    ellara_scan = scan_ellara_sessions(ellara_root)
    dnd_scan = scan_dnd_sessions(dnd_root)
    dnd_changes = find_dnd_store_changes(dnd_root, baseline)

    dnd_completed: set[int] = set()
    if dnd_scan.get("exists"):
        dnd_completed = set(dnd_scan["summary_files"]) | {
            m["session"] for m in dnd_scan["metadata"] if not m["upcoming"]
        }

    candidate_nums = (
        dnd_completed
        | set(ellara_scan["polished"])
        | set(ellara_scan["raw"])
        | set(ellara_scan["transcripts"])
    )
    new_sessions = sorted(n for n in candidate_nums if n > baseline)

    new_session_details: list[dict] = []
    meta_by_num = (
        {m["session"]: m for m in dnd_scan.get("metadata", [])}
        if dnd_scan.get("exists")
        else {}
    )
    for num in new_sessions:
        sources: list[str] = []
        if dnd_scan.get("exists") and num in dnd_scan["summary_files"]:
            sources.append(f"dnd:{dnd_scan['summary_files'][num]}")
        if num in ellara_scan["polished"]:
            sources.append(f"ellara:{ellara_scan['polished'][num]}")
        if num in ellara_scan["raw"]:
            sources.append(f"ellara:{ellara_scan['raw'][num]}")
        if num in ellara_scan["transcripts"]:
            sources.append(f"ellara:{ellara_scan['transcripts'][num]}")
        only_raw_or_transcript = bool(sources) and all(
            ("Raw Session" in s or "Transcript Session" in s) for s in sources
        )
        meta = meta_by_num.get(num, {})
        new_session_details.append(
            {
                "session": num,
                "subtitle": meta.get("subtitle", ""),
                "sources": sources,
                "provisional_only": only_raw_or_transcript,
            }
        )

    warnings: list[str] = []
    latest_dnd = dnd_scan.get("latest_completed") if dnd_scan.get("exists") else None
    latest_ellara_pol = ellara_scan.get("latest_polished")
    if not dnd_scan.get("exists"):
        warnings.append(f"Sibling dnd repo not found at {dnd_root}")
    elif latest_dnd is not None and (
        latest_ellara_pol is None or latest_dnd > latest_ellara_pol
    ):
        warnings.append(
            f"Repo sync gap: dnd has completed sessions through {latest_dnd}, "
            f"while ellara/Session Notes stops at {latest_ellara_pol}."
        )
    elif latest_ellara_pol is not None and latest_dnd is not None and latest_ellara_pol > latest_dnd:
        warnings.append(
            f"Repo sync gap: ellara/Session Notes has Session {latest_ellara_pol}, "
            f"while dnd stops at {latest_dnd}."
        )

    all_raw_or_tr = set(ellara_scan["raw"]) | set(ellara_scan["transcripts"])
    unpolished = sorted(
        n for n in all_raw_or_tr if n not in ellara_scan["polished"] and n not in dnd_completed
    )
    if unpolished:
        warnings.append(
            "Unpolished session artifacts without polished summary in either repo: "
            + ", ".join(str(n) for n in unpolished)
        )

    files_to_read = [
        "ellara:Ellara/Campaign State/Ellara Current State.md",
        "ellara:Ellara/Campaign State/Ellara Threads and Callbacks.md",
        "ellara:Ellara/Campaign State/Knowledge Boundary and Dramatic Irony.md",
    ]
    for item in new_session_details:
        files_to_read.extend(item["sources"])
    for rel in dnd_changes["stores"]:
        files_to_read.append(f"dnd:{rel}")
    if dnd_scan.get("exists") and new_sessions:
        files_to_read.append("dnd:src/store/sessions.js")
    for rel in dnd_changes["views"]:
        files_to_read.append(f"dnd:{rel}")
    files_to_read = list(dict.fromkeys(files_to_read))

    return {
        "ellara_root": str(ellara_root),
        "dnd_root": str(dnd_root),
        "last_analyzed_session": last_analyzed,
        "ellara_latest_polished": latest_ellara_pol,
        "ellara_latest_raw": ellara_scan.get("latest_raw"),
        "ellara_latest_transcript": ellara_scan.get("latest_transcript"),
        "dnd_latest_completed": latest_dnd,
        "dnd_upcoming": dnd_scan.get("upcoming") if dnd_scan.get("exists") else None,
        "new_sessions": new_sessions,
        "new_session_details": new_session_details,
        "dnd_store_changes": dnd_changes["stores"],
        "dnd_view_changes": dnd_changes["views"],
        "repo_sync_warnings": warnings,
        "files_to_read": files_to_read,
        "git": {
            "ellara": run_git_info(ellara_root),
            "dnd": run_git_info(dnd_root),
        },
    }


def _iter_vault_markdown(ellara_root: Path) -> list[Path]:
    """Return all non-hidden vault markdown files sorted by relative path."""
    files: list[Path] = []
    for path in sorted(ellara_root.rglob("*.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(ellara_root)
        if any(part in IGNORED_HIDDEN_DIRS for part in rel.parts):
            continue
        files.append(path)
    return files


def validate_ellara_state(
    ellara_root: Path,
    dnd_root: Path,
    session: int | None = None,
    allow_provisional: bool = False,
) -> dict:
    """Validate Ellara Campaign State invariants for a target session."""
    report = build_delta_report(ellara_root, dnd_root)
    errors: list[str] = []
    warnings: list[str] = list(report.get("repo_sync_warnings", []))

    campaign_state_dir = ellara_root / "Ellara" / "Campaign State"
    state_file = campaign_state_dir / "Ellara Current State.md"
    state_fm = parse_frontmatter(state_file)

    target_session = session if session is not None else report.get("last_analyzed_session")
    if target_session is None:
        errors.append(
            f"Cannot determine target session: --session was not provided and `last_analyzed_session` is missing in {state_file}."
        )
        return {
            "ok": False,
            "session": None,
            "ellara_root": str(ellara_root),
            "dnd_root": str(dnd_root),
            "errors": errors,
            "warnings": warnings,
        }

    # 1. Living state files exist & Ellara Current State.md frontmatter checks
    for required_name in (
        "Ellara Current State.md",
        "Ellara Threads and Callbacks.md",
        "Knowledge Boundary and Dramatic Irony.md",
    ):
        req_path = campaign_state_dir / required_name
        if not req_path.is_file() or req_path.stat().st_size == 0:
            errors.append(f"Missing or empty living state file: {req_path}")

    if state_fm is None:
        errors.append(f"Missing or invalid YAML frontmatter in {state_file}")
    else:
        last_analyzed = state_fm.get("last_analyzed_session")
        if last_analyzed != target_session:
            errors.append(
                f"Ellara Current State.md frontmatter `last_analyzed_session` is {last_analyzed!r}, expected {target_session}."
            )
        next_session = state_fm.get("next_session")
        if next_session != target_session + 1:
            errors.append(
                f"Ellara Current State.md frontmatter `next_session` is {next_session!r}, expected {target_session + 1}."
            )
        next_title = str(state_fm.get("next_session_title", "") or "").strip()
        upcoming = report.get("dnd_upcoming")
        if (
            isinstance(upcoming, dict)
            and upcoming.get("session") == target_session + 1
            and upcoming.get("subtitle")
        ):
            expected_title = str(upcoming["subtitle"]).strip()
            if next_title != expected_title:
                errors.append(
                    f"Ellara Current State.md `next_session_title` ({next_title!r}) does not match "
                    f"dnd/src/store/sessions.js upcoming subtitle ({expected_title!r})."
                )

    if target_session in report.get("new_sessions", []):
        errors.append(
            f"Session {target_session} is still listed in unanalyzed `new_sessions`: {report['new_sessions']}."
        )

    # 2. Session Briefs/Session N Analysis.md check
    brief_path = campaign_state_dir / "Session Briefs" / f"Session {target_session} Analysis.md"
    if not brief_path.is_file() or brief_path.stat().st_size == 0:
        errors.append(f"Missing or empty session analysis brief: {brief_path}")
    else:
        brief_text = brief_path.read_text(encoding="utf-8")
        brief_fm = parse_frontmatter(brief_path)
        if brief_fm is None:
            errors.append(f"Missing or invalid YAML frontmatter in {brief_path}")
        else:
            if brief_fm.get("session") != target_session:
                errors.append(
                    f"{brief_path.name} frontmatter `session` is {brief_fm.get('session')!r}, expected {target_session}."
                )
            for key in ("title", "date_analyzed", "sources"):
                val = brief_fm.get(key)
                if not val:
                    errors.append(f"{brief_path.name} frontmatter missing non-empty `{key}`.")
        if not allow_provisional and re.search(r"\[PROVISIONAL\]", brief_text, re.IGNORECASE):
            errors.append(
                f"{brief_path.name} contains a [PROVISIONAL] marker (re-run with polished notes or pass --allow-provisional)."
            )

    # 3. Globally unique .md filename stems across ellara/ (ignoring Session Notes/Session 3/Session 3.md)
    vault_md_files = _iter_vault_markdown(ellara_root)
    stems_to_paths: dict[str, list[Path]] = {}
    all_valid_stems: set[str] = set()
    for md_path in vault_md_files:
        rel = md_path.relative_to(ellara_root)
        all_valid_stems.add(md_path.stem)
        if rel in PREEXISTING_DUPLICATE_PATHS:
            continue
        stems_to_paths.setdefault(md_path.stem, []).append(rel)

    for stem, paths in sorted(stems_to_paths.items()):
        if len(paths) > 1:
            rendered = ", ".join(str(p) for p in paths)
            errors.append(f"Duplicate vault markdown stem `{stem}` (breaks flattened GitHub Wiki links): {rendered}")

    # 4. Every [[WikiLink]] in Ellara/Campaign State/**/*.md resolves & none inside fenced code blocks
    fenced_re = re.compile(r"```.*?```", re.DOTALL)
    wikilink_re = re.compile(r"(?<!!)\[\[([^\[\]]+)\]\]")
    if campaign_state_dir.is_dir():
        for md_path in sorted(campaign_state_dir.rglob("*.md")):
            if not md_path.is_file():
                continue
            rel = md_path.relative_to(ellara_root)
            text = md_path.read_text(encoding="utf-8")

            for fenced in fenced_re.finditer(text):
                if wikilink_re.search(fenced.group(0)):
                    line = text.count("\n", 0, fenced.start()) + 1
                    errors.append(
                        f"{rel}:{line}: WikiLink found inside a fenced code block (breaks transform_wiki_syntax.py)."
                    )

            without_fences = fenced_re.sub(
                lambda m: "\n" * m.group(0).count("\n"),
                text,
            )
            for match in wikilink_re.finditer(without_fences):
                raw_inner = match.group(1).strip()
                target = raw_inner.split("|", 1)[0].strip()
                target = target.split("#", 1)[0].strip()
                if not target:
                    continue
                leaf = target.split("/")[-1].strip()
                if leaf.lower().endswith(".md"):
                    leaf = leaf[:-3]
                if leaf not in all_valid_stems:
                    line = without_fences.count("\n", 0, match.start()) + 1
                    errors.append(
                        f"{rel}:{line}: unresolved WikiLink `[[{raw_inner}]]` (no `{leaf}.md` in vault)."
                    )

    # 5. Zero __pycache__ directories or *.pyc/*.pyo files in ellara_root
    for path in sorted(ellara_root.rglob("*")):
        rel = path.relative_to(ellara_root)
        if ".git" in rel.parts:
            continue
        if path.is_dir() and path.name == "__pycache__":
            errors.append(f"Stray Python bytecode directory found in ellara: {rel}")
        elif path.is_file() and path.suffix in {".pyc", ".pyo"}:
            errors.append(f"Stray Python bytecode file found in ellara: {rel}")

    return {
        "ok": len(errors) == 0,
        "session": target_session,
        "ellara_root": str(ellara_root),
        "dnd_root": str(dnd_root),
        "errors": errors,
        "warnings": warnings,
    }


def render_validation_report(result: dict) -> str:
    """Format validation results for terminal output."""
    lines = [
        "Ellara Campaign State Validation",
        "================================",
        f"session     : {result['session']}",
        f"ellara root : {result['ellara_root']}",
        f"dnd root    : {result['dnd_root']}",
    ]
    if result["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for w in result["warnings"]:
            lines.append(f"  WARN: {w}")
    if result["errors"]:
        lines.append("")
        lines.append("Errors:")
        for err in result["errors"]:
            lines.append(f"  ERROR: {err}")
    lines.append("")
    status = "PASS" if result["ok"] else "FAIL"
    lines.append(
        f"Validation {status}: {len(result['errors'])} error(s), {len(result['warnings'])} warning(s)."
    )
    return "\n".join(lines)


def render_human_report(report: dict) -> str:
    """Format a concise terminal summary of the session delta."""
    lines = [
        "Ellara Campaign State Delta Check",
        "================================",
        f"ellara root           : {report['ellara_root']}",
        f"dnd root              : {report['dnd_root']}",
        f"last_analyzed_session : {report['last_analyzed_session']}",
        f"ellara polished notes : Session {report['ellara_latest_polished']}",
        f"ellara raw / tr       : Raw {report['ellara_latest_raw']} / Transcript {report['ellara_latest_transcript']}",
        f"dnd latest completed  : Session {report['dnd_latest_completed']}",
    ]
    upcoming = report.get("dnd_upcoming")
    if upcoming:
        lines.append(
            f"dnd upcoming          : Session {upcoming['session']} — {upcoming['subtitle']} ({upcoming['location']})"
        )

    if report["new_sessions"]:
        lines.append("")
        lines.append(f"New Unanalyzed Sessions ({len(report['new_sessions'])}): {report['new_sessions']}")
        for item in report["new_session_details"]:
            sub = f" — {item['subtitle']}" if item["subtitle"] else ""
            prov = " [PROVISIONAL: raw/transcript only]" if item["provisional_only"] else ""
            lines.append(f"  - Session {item['session']}{sub}{prov}")
            for src in item["sources"]:
                lines.append(f"      * {src}")
    else:
        lines.append("")
        lines.append("Status: Up to date — 0 unanalyzed sessions beyond last_analyzed_session.")

    if report["dnd_store_changes"]:
        lines.append("")
        lines.append("Updated dnd Stores Since Baseline:")
        for rel, ents in report["dnd_store_changes"].items():
            ent_parts = []
            for e in ents:
                extra = f" [{','.join(e['copy_fields'])}]" if e.get("copy_fields") else ""
                ent_parts.append(f"{e['id']} (S{','.join(map(str, e['sessions']))}){extra}")
            lines.append(f"  - {rel}: {', '.join(ent_parts)}")

    if report["repo_sync_warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for w in report["repo_sync_warnings"]:
            lines.append(f"  ! {w}")

    return "\n".join(lines)


def render_reanalysis_prompt(report: dict) -> str:
    """Generate a copy-pasteable prompt for running post-session analysis."""
    last_n = report["last_analyzed_session"]
    upcoming = report.get("dnd_upcoming")
    next_n = upcoming["session"] if upcoming else (last_n + 1 if last_n is not None else 1)
    next_sub = f" ({upcoming['subtitle']})" if upcoming and upcoming.get("subtitle") else ""

    if report["new_sessions"]:
        sess_list = ", ".join(str(n) for n in report["new_sessions"])
        files_block = "\n".join(f"- `{f}`" for f in report["files_to_read"])
        return (
            f"Run the `ellara-session-analysis` skill in `~/source/ellara` to analyze "
            f"Session(s) {sess_list} (baseline is currently Session {last_n}).\n\n"
            f"Start by running `python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py` "
            f"and reading:\n{files_block}\n\n"
            f"Verify exact quotes, check scopes, and strict IC vs. OOC boundaries against primary session text, "
            f"then update `Ellara/Campaign State/Ellara Current State.md`, "
            f"`Ellara/Campaign State/Ellara Threads and Callbacks.md`, "
            f"`Ellara/Campaign State/Knowledge Boundary and Dramatic Irony.md`, and write "
            f"`Ellara/Campaign State/Session Briefs/Session {report['new_sessions'][-1]} Analysis.md`. "
            f"Finish by running `python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py --validate --session {report['new_sessions'][-1]}` "
            f"and delivering a table-ready brief of Ellara's mindset, immediate actions, top next-session hooks, "
            f"useful RP callbacks, and OOC watchlist."
        )

    return (
        f"Already up to date through Session {last_n} (0 unanalyzed sessions on disk).\n\n"
        f"Option A — Once Session {next_n}{next_sub} notes/transcript land in `~/source/ellara` or `~/source/dnd`, paste:\n"
        f"---\n"
        f"Run the `ellara-session-analysis` skill for Session {next_n}{next_sub}. Check what changed via "
        f"`python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py`, read the new "
        f"session notes and any updated `../dnd/src/store/` entries, verify quotes and strict IC vs. OOC "
        f"boundaries, update the files in `Ellara/Campaign State/`, validate with `--validate --session {next_n}`, "
        f"and give me Ellara's updated headspace, immediate moves, next-session hooks, useful callbacks, and OOC watchlist.\n"
        f"---\n\n"
        f"Option B — Immediately after today's Session {next_n}{next_sub} (before notes are published), paste:\n"
        f"---\n"
        f"Run the `ellara-session-analysis` skill in provisional mode for Session {next_n}{next_sub} using "
        f"my rough post-session recap below. Compare against `Ellara/Campaign State/` (currently at Session {last_n}), "
        f"mark `Session {next_n} Analysis.md` as provisional until full notes land, update Ellara's living state, "
        f"hooks, callbacks, and IC/OOC boundaries, and tell me what Ellara is thinking/doing next:\n\n"
        f"[PASTE YOUR ROUGH SESSION RECAP / KEY ROLLS / QUOTES HERE]\n"
        f"---"
    )


def main() -> int:
    """CLI entrypoint."""
    default_ellara = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(
        description="Check session & store deltas or validate Ellara Campaign State across ~/source/ellara and ~/source/dnd."
    )
    parser.add_argument(
        "--ellara-root",
        type=Path,
        default=default_ellara,
        help="Path to the ellara vault repository (default: auto-detected repo root).",
    )
    parser.add_argument(
        "--dnd-root",
        type=Path,
        default=None,
        help="Path to the sibling dnd repository (default: <ellara-root>/../dnd).",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Print a copy-pasteable prompt for re-analyzing after the latest/next session.",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate Ellara Campaign State invariants for --session N (exits non-zero on failure).",
    )
    parser.add_argument(
        "--session",
        type=int,
        default=None,
        help="Target session number for --validate (defaults to last_analyzed_session).",
    )
    parser.add_argument(
        "--allow-provisional",
        action="store_true",
        help="With --validate, allow a [PROVISIONAL] marker in Session N Analysis.md.",
    )
    args = parser.parse_args()

    ellara_root = args.ellara_root.expanduser().resolve()
    dnd_root = (
        args.dnd_root.expanduser().resolve()
        if args.dnd_root
        else (ellara_root.parent / "dnd").resolve()
    )

    if args.validate:
        result = validate_ellara_state(
            ellara_root,
            dnd_root,
            session=args.session,
            allow_provisional=args.allow_provisional,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(render_validation_report(result))
        return 0 if result["ok"] else 1

    report = build_delta_report(ellara_root, dnd_root)
    if args.json:
        print(json.dumps(report, indent=2))
    elif args.prompt:
        print(render_reanalysis_prompt(report))
    else:
        print(render_human_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
