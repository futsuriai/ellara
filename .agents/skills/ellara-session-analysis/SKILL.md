---
name: ellara-session-analysis
description: >-
  Analyze new D&D campaign sessions across ~/source/ellara and ../dnd to keep
  Ellara's living state, next-session hooks, RP callbacks, and strict IC/OOC
  knowledge boundaries up to date. Use after any new session, when notes/stores
  update, or when preparing Ellara's thoughts, apologies, or hooks for play.
---

# Ellara Post-Session Analysis Skill

Iteratively updates Ellara's campaign state in `Ellara/Campaign State/` by reading only the delta since `last_analyzed_session`, cross-checking against primary session text and `../dnd` world stores, and preserving strict in-character vs. out-of-character separation.

## Workflow

1. **Detect Session & Store Deltas**
   Run the delta checker first (always pass `-B` so Python never creates `__pycache__`):
   ```bash
   python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py
   ```
   - Inspect `new_sessions`, `dnd_store_changes`, `dnd_upcoming`, and `repo_sync_warnings` (either repo may be ahead of the other).
   - If the user just finished playing a session and no summary/transcript is on disk yet (or only `Raw Session <N>.md` exists), proceed using the user's recap or raw notes and mark the session brief `[PROVISIONAL]` until polished notes land.
   - If generating a prompt for later reuse, run `check_session_delta.py --prompt`.

2. **Load Context Economically**
   Follow [the dual-repo map and methodology](./references/repo-map-and-methodology.md):
   - Always read the three living documents first:
     - `Ellara/Campaign State/Ellara Current State.md`
     - `Ellara/Campaign State/Ellara Threads and Callbacks.md`
     - `Ellara/Campaign State/Knowledge Boundary and Dramatic Irony.md`
   - Read ONLY the new session files listed by the delta script (`../dnd/src/assets/sessions/session-<N>.md`, `Session Notes/Session <N>.md`, or `Raw Session <N>.md`), the top entries of `../dnd/src/store/sessions.js`, and the changed entity blocks in `../dnd/src/store/{lore,locations,npcs}.js`.
   - Cross-reference relevant `Ellara/` vault backstory files (`Spirit.md`, `Mechanical Flavoring.md`, `Arkos/`, `Keepsakes.md`, `Correspondence.md`) when a new session touches those themes.
   - *(If catching up 3+ sessions at once, consider a parallel split with a dedicated primary-text verifier.)*

3. **Verify Canon & Knowledge Boundaries**
   Before writing updates, run the checklist in [the methodology guide](./references/repo-map-and-methodology.md#3-mandatory-verification-checklist-run-before-writing-updates):
   - Confirm exact wording of quotes vs. narrator paraphrase and exact scope of skill checks (especially `Insight` and `Perception`).
   - Check every scene for who was physically present: move revealed facts into Section 1 of `Knowledge Boundary and Dramatic Irony.md`, and quarantine offscreen/other-PC secrets in Section 2.
   - Keep ambiguous mysteries explicitly ambiguous unless resolved on-page.
   - Ensure any `[[WikiLinks]]` inside `Ellara/Campaign State/` point strictly to existing vault pages with unique filename stems.

4. **Update Living Documents & Archive Session Brief**
   - Create `Ellara/Campaign State/Session Briefs/Session <N> Analysis.md` using [the analysis template](./references/analysis-template.md).
   - Update `Ellara/Campaign State/Ellara Current State.md` (bump `last_analyzed_session`, `next_session`, `next_session_title`, `current_location`, headspace, relationships table, and gear/level changes).
   - Update `Ellara/Campaign State/Ellara Threads and Callbacks.md` (promote/retire hooks, add new verbatim quotes and spirit milestones, move completed items to Resolved).
   - Update `Ellara/Campaign State/Knowledge Boundary and Dramatic Irony.md` (move revealed items from Section 2 to Section 1; append new offscreen dramatic irony).

5. **Deliver the Prep Brief**
   Respond concisely with:
   - What Ellara is thinking right now (strictly IC)
   - Immediate next moves / conversations she would initiate
   - Prioritized next-session hooks (grounded in the upcoming session teaser if present)
   - Useful RP callbacks & exact lines to keep handy
   - A clearly separated **OOC Watchlist** so the player knows what Ellara still does not know

## Automated Pipeline Invocation

This skill is also invoked automatically as the `ellara-state` stage of the unified session pipeline in `../dnd`:

```bash
# As part of the full audio -> website -> ellara-state -> verify run
python3 -B ../dnd/scripts/transcription/run_session_auto.py --session <N> --audio-dir <audio_dir>

# Or standalone / catch-up for a single session
python3 -B ../dnd/scripts/transcription/run_ellara_analysis_agent.py --session <N> --ellara-root . --dnd-dir ../dnd
```

`run_ellara_analysis_agent.py` checks `Session <N>.md` <-> `session-<N>.md` parity, runs `check_session_delta.py --json`, skips idempotently if `last_analyzed_session >= N` (unless `--force`), invokes the agent scoped to `Ellara/Campaign State/`, runs a clean-context IC/OOC & quote audit pass, saves the table-ready Prep Brief, and enforces `check_session_delta.py --validate --session <N>`.

## Verification

After updating files, run the deterministic validator and check git status:
```bash
python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py --validate --session <N> && git status -s
```
This enforces:
- `last_analyzed_session == <N>` and `next_session == <N+1>` in `Ellara Current State.md`
- `next_session_title` parity with `../dnd/src/store/sessions.js` upcoming subtitle (when present)
- `Ellara/Campaign State/Session Briefs/Session <N> Analysis.md` exists with valid frontmatter and no `[PROVISIONAL]` marker (unless `--allow-provisional`)
- Globally unique `.md` filename stems across the vault and valid `[[WikiLinks]]` in `Ellara/Campaign State/`
- Zero `__pycache__/` directories or `*.pyc` files in `~/source/ellara` and no accidental edits in `../dnd`.
