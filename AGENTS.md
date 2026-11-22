# AGENTS.md — Ellara RP Vault & Post-Session Analysis Guide

## Repository Relationship
- **This repository (`~/source/ellara`)** is Ellara's private Obsidian RP vault: backstory (`Ellara/`), Spirit & D&D flavor (`Ellara/Spirit/`, `Ellara/D&D Flavor/`), Arkos lore (`Ellara/Hometown (Arkos)/`), session transcripts/notes (`Session Notes/`), and living campaign state (`Ellara/Campaign State/`).
- **Sister repository (`../dnd`, `~/source/dnd`)** is the campaign manager/wiki. It holds `src/assets/sessions/session-<N>.md`, world stores (`src/store/{lore,locations,npcs,sessions,correspondence,characters,worldHistory,config}.js`), and views. **`../dnd` is often ahead of `Session Notes/`** on polished summaries and world updates—always inspect both.

## Living State Entrypoints
Start every campaign prep, mid-session reminder, or post-session check in `Ellara/Campaign State/`:
- `Ellara/Campaign State/Ellara Current State.md` — Current snapshot, `last_analyzed_session`, headspace, relationships, active gear/level.
- `Ellara/Campaign State/Ellara Threads and Callbacks.md` — Next-session hooks, long-term arcs, verbatim RP quotes bank, Spirit milestones.
- `Ellara/Campaign State/Knowledge Boundary and Dramatic Irony.md` — Strict separation between what Ellara knows IC and what only other PCs/the DM/readers know.
- `Ellara/Campaign State/Session Briefs/` — Per-session delta analyses.

## Post-Session & Next-Session Workflow
Whenever asked to re-analyze after a session, refresh Ellara's thoughts/hooks/callbacks, or prep for the next session, load and follow the **`ellara-session-analysis`** skill (`.agents/skills/ellara-session-analysis/SKILL.md`), starting with:
```bash
python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py
```
If the user supplies a rough post-session recap before polished notes exist in either repo, run the same workflow in `[PROVISIONAL]` mode and re-run once polished notes/stores land.

## Non-Negotiable Rules
1. **Strict IC vs. OOC separation:** Never put items from Section 2 of `Knowledge Boundary and Dramatic Irony.md` into Ellara's in-character thoughts, motives, or plans.
2. **Primary-text discipline:** Verify verbatim quotes, narrator prose, and roll scopes (what a check actually applied to) against session files rather than guessing from memory.
3. **Wiki compatibility:** This vault publishes selected pages to a flattened GitHub Wiki via `.github/scripts/transform_wiki_syntax.py` and `generate_wiki_nav.py`. Keep every new `.md` filename stem globally unique across `Ellara/`, and only use double-bracket WikiLinks for real existing vault pages.
4. **No stray Python bytecode:** There is no `.gitignore` in this repo—always invoke Python with `python3 -B` and do not leave `__pycache__/` directories behind.
5. **Respect repo boundaries:** Read from `../dnd` as needed, but keep Ellara analysis artifacts in `~/source/ellara` unless explicitly asked otherwise.
