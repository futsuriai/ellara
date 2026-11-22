# Dual-Repo Map & Post-Session Analysis Methodology

## 1. The Two Sister Repositories

### `~/source/ellara` — Private Character Vault & Obsidian Knowledge Base
Contains Ellara's private inner life, mechanical reflavoring, backstory, and living campaign state:
- `Ellara/Campaign State/` — Living analysis artifacts maintained by this skill:
  - `Ellara Current State.md` (`last_analyzed_session` frontmatter, headspace, relationships, active gear/level)
  - `Ellara Threads and Callbacks.md` (next-session hooks, medium/long arcs, verbatim quotes bank, resolved log)
  - `Knowledge Boundary and Dramatic Irony.md` (strict IC knowledge vs. OOC dramatic irony & canon disambiguation)
  - `Session Briefs/Session <N> Analysis.md` (immutable per-session delta snapshots)
- `Ellara/Ellara.md` & `Ellara/Background/` — Upbringing at the Priory of the Steadfast Light, personality, prejudices, transfer to Bastion City.
- `Ellara/Spirit/Spirit.md` — Mysterious Spirit tied to the Highland Standing Stones and Lyra's mother's death.
- `Ellara/D&D Flavor/Details.md` & `Mechanical Flavoring.md` — Human (mechanically Kalashtar reflavored as *The Divine Spark*), Circle of Stars Druid (reflavored as Clerical / Highland Light). *(Note: `Details.md` still shows Level 3; canon party level is 5 as of Session 19.)*
- `Ellara/Hometown (Arkos)/` & `Ellara/Hometown Connections/` — Arkos, Sunstone Quarry (643 AE Light Crystals + Standing Stones discovery), Highland Standing Stones (Grey Sisters, Ancestor's Perch), Brother Sorin, Abbot Aris, Lyra Meadowlight, `Keepsakes.md`, `Correspondence.md`.
- `Session Notes/` — Polished `Session <N>.md`, raw `Raw Session <N>.md`, and `Transcripts/Transcript Session <N>.txt`. *(May trail `../dnd` if the pipeline hasn't synced back yet.)*

### `../dnd` (`~/source/dnd`) — Campaign Wiki & World State
Contains the party-wide polished session records and structured world stores:
- `src/assets/sessions/session-<N>.md` — Authoritative polished session summaries (with line-level rolls, quotes, and split-party scenes).
- `src/store/sessions.js` — Completed sessions metadata (`highlights`, `description`, `location`, `date`) plus the next `upcoming: true` session teaser.
- `src/store/config.js` — Infers `currentSession` from the session before `upcoming: true`, and computes `isEntityNew(entity)` by checking `entity.history` entries for `session === currentSession`. *(Note: stores use `entity.history`, NOT `updatedInSessions`.)*
- `src/store/lore.js`, `locations.js`, `npcs.js` — World lore, places, NPCs, relationships, and session-stamped `history` arrays.
- `src/store/characters.js`, `correspondence.js`, `worldData.js`, `worldHistory.js` — PC stubs, early Arkos letters (`Ellara` <-> `Lyra`), and timeline (`651 AE`).
- `src/views/HomeView.vue` & `StorySoFarView.vue` — Campaign UI summaries and `HOME_NEXT_STEPS_BY_SESSION` teasers.

---

## 2. Incremental Analysis vs. Full Multi-Session Catch-Up

### Standard 1–2 Session Update (Fast Path)
1. Run `python3 -B .agents/skills/ellara-session-analysis/scripts/check_session_delta.py`.
2. Read the 3 living files in `Ellara/Campaign State/` (`Ellara Current State.md`, `Ellara Threads and Callbacks.md`, `Knowledge Boundary and Dramatic Irony.md`).
3. Read ONLY the newly detected session summary file(s) (`../dnd/src/assets/sessions/session-<N>.md` and/or `Session Notes/...`), `../dnd/src/store/sessions.js` top entries, and the specific `entity` blocks in `../dnd/src/store/{lore,locations,npcs}.js` flagged by the delta script.
4. Check any relevant `Ellara/` vault lore newly touched in the session (e.g., `Arkos`, `Spirit`, `Light Crystal`, `Correspondence`).
5. Run the Verification Checklist below, then update the 4 files.

### Multi-Session Catch-Up (3+ Sessions Behind) or `/swarm` Run
When catching up across several sessions or auditing the whole repo, split work into non-overlapping lanes:
- **Worker 1 (`session-delta`):** Reads all new `session-<N>.md` / `Session <N>.md` files for Ellara's actions, quotes, rolls, relationships, and split-party scenes.
- **Worker 2 (`world-delta`):** Diffs `../dnd/src/store/*.js` and `src/views/` without reading session prose, mapping changed entities and world pressures.
- **Worker 3 (`verifier`):** Mandatory final pass checking Workers 1 & 2 against primary session text for check scopes, quotes vs. prose, and strict IC vs. OOC boundaries.

---

## 3. Mandatory Verification Checklist (Run Before Writing Updates)

1. **Primary-Text Quote & Prose Check:** Verify every quote is verbatim from the session log; never put quotation marks around narrator paraphrase.
2. **Skill Check & Roll Scope:** Record *exactly* what a check covered (e.g., in Session 21, Ellara's `Insight 26` covered *only* Eduard's sincere concern when welcoming her on the Seminary grounds—NOT his later office denials or Pharus offer).
3. **Strict IC vs. OOC Separation:** For every dramatic reveal, ask: *Was Ellara physically in the room/scene? Did another PC explicitly tell her on-page?* If not, add it to `Knowledge Boundary and Dramatic Irony.md` Section 2, **never** her headspace.
4. **Preserve Intentional Ambiguity:** Do not collapse open mysteries into settled fact (e.g., whether Ellara's awake `Spirit` and her sleeping *"whispers of Eulogia"* / *"that voice"* are the same entity; whether the ~80 buried soldiers in Hýrda survived; what Eduard started writing in Session 21).
5. **Obsidian & GitHub Wiki Publishing Safety:**
   - Every `.md` file added to `Ellara/Campaign State/` must have a globally unique filename stem (because `.github/scripts/transform_wiki_syntax.py` flattens all WikiLinks to root filenames).
   - Never use `[[...]]` inside code blocks or around non-existent pages in `Ellara/Campaign State/*.md`; link with `[[Page Name]]` **only** to existing files in `~/source/ellara`.
   - Always run Python helper scripts with `python3 -B` (there is no `.gitignore` in `~/source/ellara`, so avoid generating `__pycache__`).
