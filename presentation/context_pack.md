# PAINDICATOR — Complete Project Context Pack

> **Purpose of this file.** This is a single, self-contained, source-accurate dossier of the entire
> PAINDICATOR project. Paste it into ChatGPT (or any LLM) so it knows the project in full — enough to
> help write the **competition presentation** *and* the **final academic report**. Everything here was
> taken from the actual source code and project docs (not guessed). Accurate as of 2026-06-19.

---

## How to use this with ChatGPT (suggested opening prompt)

> "You are my expert assistant on a biomedical-engineering capstone project called **PAINDICATOR**.
> Below is the complete project context. Use ONLY this as ground truth about the system. Help me with
> (a) a 10-minute competition presentation and (b) a formal final report. When you state a technical
> fact, it must match this document. If something isn't covered here, say so instead of inventing it.
> Keep the medical framing honest: it is decision-support, **not** a diagnostic device."

Then paste everything below.

---

## 1. Identity, team & partners

- **Name / tagline:** PAINDICATOR — *"Map Your Pain."*
- **What it is:** A clinical decision-support system for **digital pain mapping** and **dermatome
  analysis**. A patient paints the location and intensity of pain on an interactive 3D human body
  model; the app converts that into quantitative, per-spinal-nerve-segment (dermatome) metrics and a
  rule-based pain-pattern report for a clinician.
- **Context:** Final project, **Biomedical Engineering, Tel Aviv University**.
- **Authors:** **Amit Bezalel** and **Shachar Guttman**.
- **Supervisor:** **Prof. Mickey Scheinowitz** (TAU).
- **Clinical partner:** **Loewenstein Rehabilitation Medical Center**, part of **Clalit Health
  Services** (a leading Israeli rehabilitation hospital).
- **Stated goal (from the in-app About text):** "streamline and improve the process of pain
  documentation in pain clinics, by replacing manual marking on paper with interactive, clear, and
  structured marking on a three-dimensional model."
- **Platform:** Windows tablet-first desktop app; ships as a standalone offline `.exe`. Bilingual
  **English / Hebrew** with full RTL support.

---

## 2. The problem it solves

Pain is among the most common clinical complaints but one of the worst-documented signals. Today it is
captured as **free text** or a **felt-tip drawing on a paper body chart**, which is:
- **subjective & unstructured** (no numbers can be computed from it),
- **not comparable over time** (you can't measure change between visits — the core of pain management),
- **anatomically imprecise** (a flat sketch doesn't point to a spinal nerve level).

The clinician's central task — **localizing pain to a spinal nerve root / level** — is done from memory
and a 2D picture. PAINDICATOR makes that localization **computable and trackable**.

---

## 3. Product overview & user flows

Two roles, two flows. Navigation is a `QStackedWidget` with fade transitions; screens are pre-built
and reused; handoff via `navigate_to("screen_name", **kwargs)`.

### Patient flow
`role_selection → patient_id → gender_selection → questionnaire → show_model (paint) → save`

1. **role_selection** — choose *Patient* or *Clinician*; a **Demo** mode skips patient-entry screens
   (useful for presentations/conferences).
2. **clinician_name** — enter the attending clinician's name.
3. **patient_id** — enter a unique patient identifier (creates or appends to a patient record).
4. **gender_selection** — *Male* / *Female*; selects which 3D model loads. For a returning patient the
   opposite gender is disabled (model/topology must stay consistent across sessions).
5. **questionnaire** — structured pain questionnaire (see §5). All fields optional.
6. **show_model** — the 3D painting screen (see §6). Paint, erase, undo, rotate/zoom/pan, notes, save.
7. **Save** — writes the session folder (see §10).

### Clinician flow
`role_selection → clinician_name → clinician_patients → clinician_session_selection → clinician_view_session`

1. **clinician_patients** — searchable list of patient IDs with session counts.
2. **clinician_session_selection** — sessions for a patient, newest first; each offers **View**
   (read-only analysis) or **Edit** (reopen in the paint screen to add/modify marks).
3. **clinician_view_session** — read-only painted model + **dermatome coverage panel** (HTML table) +
   toggle to the **dermatome-region view** + **click-to-identify** a dermatome by name +
   **multi-session comparison overlay** (cool-tone blue/violet) + full bilingual session summary.

### Registered screens (12)
`role_selection`, `clinician_name`, `clinician_patients`, `clinician_session_selection`,
`clinician_view_session`, `patient_id`, `patient_session_choice`, `session_selection`,
`gender_selection`, `questionnaire`, `show_model`, `view_session`.
(Class convention: `snake_case` filename → `SnakeCaseScreen` class.)

---

## 4. Feature list (what a user can actually do)

**Painting (per-vertex "Paint V2"):**
- Paint with **3 intensity levels**: `1` = mild (yellow), `2` = moderate (orange), `3` = severe (red);
  `0` = unpainted (gray).
- **Erase**, **Undo** (true per-stroke), **Clear all**, **Reset view**.
- Input by **stylus** (pressure), **finger**, or **mouse**.
- **Normal gating** — you cannot paint "through" the body onto the far side.

**Navigation / interaction:**
- Modes: **VIEW** (left-drag rotates), **MARK** (left paints / right rotates), **ERASE** (left erases
  / right rotates), **NONE** (camera only).
- Two-finger **pinch-zoom**, **pan**, **rotate**; on-screen **gesture guide** (the "?" overlay);
  zoom slider + rotation D-pad; **auto-rotate** demo spin.
- Clinician view locks rotation to the dominant axis (horizontal = azimuth, vertical = elevation) to
  prevent diagonal wobble.

**Session & review:**
- Add/edit/delete **notes (comments)**.
- **Save** session (JSON + bilingual TXT summary + front/back screenshots).
- Clinician: **dermatome toggle**, **click-to-identify**, **multi-session overlay**, **edit session**.

**Platform:**
- Bilingual **EN/HE** with live switching and RTL; tablet virtual-keyboard auto-popup; offline EXE.

---

## 5. The questionnaire (exact structure)

Stored as `session.data["questionnaire"]` — a flat dict of **save-keys → values**. Sections and keys
(from `session_manager._Q_SECTIONS`, which mirrors `questionnaire.py`):

| Section | Save-key | Type | Notes |
|---|---|---|---|
| Patient info | `age` | int | 0–120 |
| Pain intensity (VAS) | `pain anamnesis` | int 1–10 | pain during the exam/intake |
| | `pain average` | int 1–10 | average pain |
| | `pain peak` | int 1–10 | peak / acute pain |
| Frequency | `frequency` | list[str] | multi-select |
| | `frequency comment` | str | free text |
| Characteristics | `radiation` | str | radiation pattern |
| | `pain begin` | str | when it began |
| | `pain variation` | str | variation across the day |
| | `pain character` | list[str] | multi-select pain quality |
| | `pain character comment` | str | free text |
| Factors | `alleviating factors` | str | free text |
| | `aggravating factors` | str | free text |
| | `associated symptoms` | str | free text |
| Life impact | `life impact` | list[str] | multi-select |
| | `life comment` | str | free text |
| Exam date | `examination date` | str | dd/MM/yyyy |

**Multi-select option values** (the exact strings the analyzer keys off; labels come from the
translations table):
- `frequency`: *Related to a specific event, Sudden onset, Constant, Intermittent, Other.*
- `pain character`: *Pressing, Burning, Stabbing, Hot, Tingling, Sharp, Dull, Pulsating, Neuropathic,
  Shooting, Other.*
- `life impact`: *Sleep, Appetite, Rest, Physical activity, Walking, Educational/work, Mood,
  Concentration, Family relations, Social life.*

---

## 6. The 3D painting system (VTK)

- **Per-vertex, not per-cell.** The canonical paint state is `point_levels: List[int]` — one integer
  (0–3) per mesh vertex. This is what feeds the dermatome engine.
- **Brush:** radius-based via `vtkPointLocator.FindPointsWithinRadius()`, with **screen-space
  interpolation** between drag samples so fast strokes leave no gaps.
- **Normal gating:** a vertex is paintable only if `dot(vertex_normal, camera_direction)` exceeds a
  threshold (~0.05), so you can't paint the occluded back side.
- **Undo:** each stroke captures `{vertex_id: old_level}` pushed to an undo stack on mouse/touch up;
  long strokes are chunked for granular undo. (No redo — intentional.)
- **Ownership / architecture:**
  - `RendererScene` (`codes/renderer_scene.py`) owns **all** VTK objects (renderer, render window,
    interactor, actor, mapper, polydata) and exposes the toolbar-facing API.
  - `CustomInteractorStyle` (`codes/vtk_interactor_custom.py`) owns **all** paint/erase/camera
    interaction.
- **VTK lifecycle (fragile):** `RendererScene` is initialized lazily in `showEvent()` (VTK needs a
  visible widget); on `hideEvent()` the interactor is disabled and scene refs dropped. **Never call
  `TerminateApp()` or `Finalize()`** — only `interactor.Disable()`.
- **L/R orientation labels:** `vtkTextActor` badges reprojected before each render.

---

## 7. The dermatome system (concept + mapping)

**Dermatome (definition):** the area of skin whose sensation is carried by a single spinal nerve root.
~30 of them cover the body, labelled by spinal level. When a nerve root is irritated/compressed
(e.g. herniated disc), pain appears in *that* dermatome — so the *pattern* of pain points to the
*spinal level*. This is the clinical reasoning PAINDICATOR quantifies.

**How mapping works:** every vertex of the 3D model stores a **dermatome ID** in a compact binary
`.u8` file (one `uint8` per vertex). Because painting is per-vertex, `derm_map[vertex_id]` classifies
each painted point instantly. The painting mesh and the `.u8` map **must share vertex topology/order**.

**Dermatome ID table** (`DermatomeMapper._CANONICAL_NAME_TO_ID`):
- `0 = UNASSIGNED` (skipped in all analysis)
- `1 = C1` (unused), `2..8 = C2..C8`
- `9..20 = T1..T12`
- `21..25 = L1..L5`
- `26..30 = S1..S5`
- IDs are assigned in cranial→caudal order, so sorting ascending by ID = anatomical order.

**`DermatomeMapper`** (`codes/dermatome_mapper.py`) loads the `.u8` array + a meta JSON (supports three
meta formats: female `id_to_name`+`distribution_by_id`; male `distribution`-by-name; original
`derm_id_table`). Key methods: `get_dermatome_for_point()`, `get_dermatome_for_cell()` (majority vote,
ties → UNASSIGNED), `get_dermatome_order()`, `compute_metrics()` (legacy, see §9),
`total_vertices_per_dermatome` (used as denominators).

---

## 8. Coverage engine — EXACT metrics & logic (the core)

Module: `codes/dermatome_coverage.py` — **pure math, VTK-free, UI-free, fully testable.**
Entry: `compute_dermatome_coverage(point_levels, derm_map, total_vertices_per_dermatome, id_to_name, dermatome_order, options)`.

**Aggregation:** for every vertex with level `> 0` whose dermatome ≠ 0, accumulate per dermatome:
`painted_count` (number of painted vertices) and `level_sum` (sum of their 1–3 levels).
Global totals: `total_painted_vertices = Σ painted_count`, `total_painted_mass = Σ level_sum`.

**Per-dermatome metrics (exact formulas):**
| Metric | Formula | Meaning |
|---|---|---|
| `weighted_pain_burden` | `level_sum / total_painted_mass` | **Primary ranking.** Share of the body's total intensity-weighted pain in this dermatome. |
| `pain_area_share` | `painted_count / total_painted_vertices` | Share of painted *surface* (area, not weighted). |
| `local_involvement` | `painted_count / total_vertices_in_dermatome` | Fraction of this dermatome's own surface that is painted. |
| `mean_local_intensity` | `level_sum / painted_count` | Average level (1–3) where painted. |

**Ranking:** sort dermatomes by `(weighted_pain_burden, pain_area_share, local_involvement)` descending;
assign `rank = 1..n`.

**Segmental spread:** among "meaningful" dermatomes (`burden ≥ 0.05` OR `area_share ≥ 0.05`), if ≥2
exist, `segmental_spread = max(pos) − min(pos)` where `pos` = index in cranial-caudal `dermatome_order`.
A wider value implies a more diffuse, multi-level distribution.

**Overlap flag (radiculopathy-ambiguity heuristic):** walk meaningfully-painted dermatomes
(`burden ≥ 0.05`) in cranial-caudal order; for each pair that is **directly adjacent** (order-position
difference == 1), compute `rel_diff = |bA − bB| / max(bA, bB)`. If `rel_diff ≤ 0.30`, set
`overlap_flag = True` and mark both as overlap candidates. Clinically: two neighbouring levels carry
near-equal burden → the responsible root is ambiguous (e.g. L4 vs L5).

**Close competitors:** dermatomes just below the top-N whose burden is within `0.03` of the rank-N
burden (surfaced as "additional close dermatomes").

**Thresholds (`DermatomeOptions` defaults):** `top_n=5`, `close_competitor_threshold=0.03`,
`meaningful_burden_threshold=0.05`, `meaningful_area_share_threshold=0.05`,
`overlap_burden_threshold=0.05`, `overlap_relative_diff=0.30`.

**Result dict shape:**
```
{
  "analysis_type": "anatomical_mapping_only" | "unavailable",
  "overall": { total_painted_vertices, total_painted_mass, segmental_spread,
               top_n_displayed, overlap_flag, notes[] },
  "dermatomes": [ { id, name, rank, weighted_pain_burden, pain_area_share,
                    local_involvement, mean_local_intensity, painted_vertex_count,
                    total_vertices, is_close_competitor, is_overlap_candidate }, ... ]
}
```
**Notes** added automatically: an overlap note when flagged; "Wide segmental distribution detected
(N levels)" when `segmental_spread ≥ 5`.

**Companion functions:** `format_dermatome_coverage_for_display()` (plain text),
`format_dermatome_coverage_as_html()` (the clinician panel's HTML `<table>`),
`serialize_dermatome_coverage()` (rounds floats to 4 dp → stored in `model_data["dermatome_coverage"]`).

**Public API on `RendererScene`:** `compute_dermatome_coverage_result(session_manager=None)` loads the
mapper if needed and runs the engine; `_compute_dermatome_stats_for_save()` serializes for saving.

---

## 9. Legacy metric set (still in the mapper — know it exists)

`DermatomeMapper.compute_metrics(stats, totals)` is an **older, cell-based** metric set kept for
compatibility. Per dermatome: `coverage = painted/total`, `avg_pain = level_sum/painted`,
`pain_index = (avg_pain/3) * coverage`, `body_share = level_sum/total_painted_mass`, and a `severity`
label (`avg_pain ≥ 2.5` Severe, `≥ 1.5` Moderate, else Mild); sorted by `pain_index`. **The active
pipeline uses §8 (`dermatome_coverage.py`), not this.** Old saved sessions may carry a legacy
`dermatome_analysis` block; the summary renderer falls back to it.

---

## 10. Data & persistence

**Session folder:** `data/sessions/{subject_id}/session_{DD-MM-YYYY_HH-MM-SS}/` containing
`session.json`, `session_summary.txt`, `front.png`, `back.png`. Stored **locally** (privacy; not
committed to the repo). The folder is "sticky" within a session (re-saves overwrite the same folder).

**`session.json` schema** (single source of truth = `SessionManager.data`):
```
{
  "subject_info":  { "subject_id": str, "gender": "male"|"female"|null,
                     "clinician_name": str|null },
  "questionnaire": { ...save-keys from §5... },
  "model_data": {
     "mode": str,
     "camera": { ...camera state... },
     "marks": { cell_id: level },                 # legacy cell-based paint
     "paint_v2": { "point_level": [int…N],         # active per-vertex paint
                   "point_intensity": [float…N] },
     "comments": [str, …],
     "dermatome_coverage": { …serialized §8 result… },   # current key
     "dermatome_analysis": [ … ]                   # legacy key (older sessions only)
  },
  "screenshots": { "front": "front.png", "back": "back.png" },
  "timestamp": "<ISO-8601>"
}
```

**`session_summary.txt`** — bilingual, `[English]` then a `===` separator then `[עברית]`. Each side:
Patient ID / Gender / Clinician, the sectioned questionnaire, comments, painted-point count, and the
**Dermatome Coverage Analysis** (always rendered in English; reads `dermatome_coverage`, falls back to
legacy `dermatome_analysis`). An analysis report can be appended via `append_analysis_to_summary()`.

**Save entrypoint:** `RendererScene.save_full_session(session_manager)` captures screenshots, builds
`model_data`, then calls `session_manager.save_to_file()` + `save_to_human_readable_file()`.
(`save_session()` is legacy — use `save_full_session()`.)

---

## 11. Decision-support analyzer (rule-based, explainable)

Module: `codes/pain_analyzer.py` (~230 lines). `analyze_pain(patient_data)` returns a formatted text
report. It is **rule-based and explainable** (every line traces to a readable clinical rule) — framed
explicitly as **decision support, NOT a diagnosis**.

**Input (`patient_data`) keys it reads:** `dermatomes` (list of names), `severity_map`
(`{derm_name: "Mild/Moderate/Severe"}`), `pain peak`, `pain average`, `pain anamnesis`,
`pain character` (list), `aggravating factors`, `alleviating factors`, `associated symptoms`,
`frequency` (list), `radiation`, `life impact` (list). (An adapter combines the dermatome result +
questionnaire into this shape.)

**Output sections:** `Dermatomes affected`, `Primary zone`, `VAS line`, **Clinical findings**,
**Patterns to consider** (differentials), **Red flags**, **Recommended next steps**, plus a standing
"not a diagnosis" disclaimer header/footer.

**Representative encoded knowledge (not exhaustive):**
- *Cervical:* C5–C6 / C6–C7 / C7 / C8 radiculopathy; C8+T1 → thoracic outlet; ≥3 cervical →
  spondylosis; ≥4 → cervical myelopathy (red flag).
- *Thoracic:* single band → intercostal neuralgia; T10 → umbilical referral; severe single band
  (VAS≥7) → **herpes zoster pre-rash** (red flag); mid-thoracic severe → consider cardiac referral;
  ≥5 levels → thoracic myelopathy (red flag).
- *Lumbar/sacral:* L3–L4 / L4–L5 disc; L2–L3–L4 → femoral nerve; **L5–S1 → most common sciatica**;
  **S3–S4–S5 → possible cauda equina → urgent surgical referral** (red flag); ≥4 lumbar / ≥3 sacral →
  stenosis / cauda-equina rule-out.
- *Cross-region:* lumbar+sacral → sciatica; non-contiguous cervical+lumbar → central/multifocal (red
  flag); ≥7 dermatomes → central sensitization / fibromyalgia.
- *Character/VAS/frequency:* burning+tingling → neuropathic (suggest DN4); shooting/sharp → radicular;
  peak≥8 → acute compression; large peak−average gap → positional/episodic; sudden onset + high VAS →
  acute disc prolapse (red flag).
- *Aggravating/alleviating:* worse sitting → lumbar disc; worse standing/walking → neurogenic
  claudication/stenosis; **cough/sneeze/strain → Valsalva-positive → suggest MRI**; relief lying/rest
  → mechanical.
- *Associated symptoms:* **bladder/bowel/incontinence → urgent cauda-equina rule-out + emergency
  surgical consult**; weakness → motor exam; fever + spine pain → discitis/epidural abscess (red flag).
- *Life impact:* sleep+mood → pain-psychology referral; ≥5 domains → multidisciplinary management.

---

## 12. Architecture & code map

| Layer | File | Responsibility |
|---|---|---|
| Entry point | `codes/app.py` | `QApplication`, `SessionManager`, `MainWindow`, tablet keyboard filter |
| Navigation | `codes/ui_main.py` | `QStackedWidget` + fade transitions; screen registration |
| State (single source of truth) | `codes/session_manager.py` | all session data, save/load, summary |
| 3D pipeline | `codes/renderer_scene.py` | owns all VTK objects; toolbar API; coverage entrypoints |
| Interaction | `codes/vtk_interactor_custom.py` | per-vertex paint / erase / camera; modes; undo |
| Analysis (pure math) | `codes/dermatome_coverage.py` | coverage metrics, format & serialize |
| Mapping | `codes/dermatome_mapper.py` | loads `.u8` map; lookups; legacy metrics |
| Decision support | `codes/pain_analyzer.py` | rule-based pattern report |
| Paths | `codes/config.py` | EXE-safe path resolution (`sys._MEIPASS`) for `files/models/` |
| Screens | `codes/screens/` | one file per UI screen (12) |
| Widgets | `codes/widgets/` | toolbar, top bar, comment popup |
| i18n | `codes/translations.py` | EN/HE `STRINGS` table, `lang_manager` |

**Design rules (project guardrails):** SessionManager is the only state authority; RendererScene is the
only VTK owner; CustomInteractorStyle is the only interaction owner; screens hold UI/flow only, no
business logic; saved JSON must stay backward compatible; make minimal, local changes; never break VTK
interaction or the save pipeline.

---

## 13. Tech stack, run & build

- **Python 3.11** (Windows).
- **PyQt6 6.10.0** (UI, touch & stylus), **VTK 9.5.2** (3D), **NumPy 2.3.5** (`.u8` arrays),
  **Pillow 12.0.0** (images), **PyInstaller 6.17.0** (packaging).
- **Run (dev):** `venv311\Scripts\activate` → `python -m codes.app` (always from project root so
  `data/sessions/` and `files/models/` resolve).
- **Build EXE:** `pyinstaller --clean --noconfirm app.spec` → `dist/PAINDICATOR/PAINDICATOR.exe`
  (the whole `dist/PAINDICATOR/` folder is the distributable; the spec bundles VTK hidden imports +
  `codes/`, `files/`, `data/`).

---

## 14. Models & assets

- **Male model** (`files/models/male model/`): `male_derm_vertex_colors.ply` (painting + toggle actor),
  `male_derm_vertex_id.u8` (per-vertex dermatome IDs), `male_derm_meta.json` (ID table + counts).
- **Female model** (`files/models/female model/`): `female_derm_vertex_colors.ply` (painting),
  `female_derm_vertex_colors_fixed.ply` (toggle actor, **~212,196 faces — must use this; not the older
  ~106,098-face `filled.ply`**), `female_derm_vertex_id.u8`, `female_derm_meta.json`.
- ~200k vertices per model; **31 dermatome IDs (0–30)**. Path resolution via
  `config.get_male_model_info()` / `get_female_model_info()`.
- **Hard constraint:** the active painting mesh and the `.u8` map must share vertex topology, or IDs
  misalign. (Verifying female topology consistency is a flagged ongoing task.)
- **Presentation assets:** `docs/logo.png`, `docs/screenshots/{welcome, painting-front, painting-back,
  clinician-analysis}.png`; dermatome reference images in `files/pictures/`.

---

## 15. Status, known issues & roadmap

**Working:** full patient + clinician navigation; save/load; per-vertex paint, erase, per-stroke undo;
clinician session view; consistent front/back screenshots; full dermatome coverage pipeline (both
genders) → clinician HTML panel + JSON; dermatome toggle; click-to-identify; multi-session overlay;
rule-based analyzer; age field; L/R labels; touch pinch/pan/rotate; stylus paint; tablet keyboard;
auto-rotate.

**Fragile / partial:** female painting-vs-toggle topology consistency (verify); fixed-camera
screenshot consistency (partial); painting performance on older tablets; L/R label orientation depends
on model axis convention. *(Note: a known input quirk on some tablets — finger touch can arrive as a
mouse event rather than a `QTouchEvent`, which can make two-finger gestures behave like single-touch;
relevant if demoing on an unfamiliar tablet.)*

**Not yet implemented:** visual dermatome **heatmap**; quantitative **longitudinal** comparison
metrics; trained **ML** pattern recognition (the rule-based analyzer is the labeled foundation).

**Roadmap priorities:** (1) system stability; (2) verify female topology; (3) visual heatmap;
(4) screenshot consistency; (5) painting robustness/performance.

---

## 16. Honest limitations & disclaimer (use in the report)

- **Not a diagnostic device.** Output is a *descriptive summary of recorded data*; it does not
  constitute a diagnosis and does not replace clinical judgment, physical examination, imaging, or full
  medical evaluation. (In-app text and report footers state this explicitly.)
- **Decision rules are not clinically validated** — they encode textbook patterns for clinician
  *correlation*, not proof.
- **Dermatome boundaries are inherently approximate** (they vary between individuals and references) —
  which is precisely why the engine surfaces an **overlap flag** rather than asserting crisp borders.
- **Self-report bias** — painting reflects what the patient perceives/marks; coverage ≠ pathology.
- **No formal clinical study yet** — validation is the explicit next step; the architecture (pure
  testable math core + structured saved sessions) is built to support one.

---

## 17. Glossary (for non-specialist readers / judges)

- **Dermatome** — skin area served by one spinal nerve root (C1–S5).
- **Radiculopathy** — pain/dysfunction from a compressed/irritated nerve **root** (e.g. a disc pressing
  a root); pain follows the root's dermatome.
- **VAS** — Visual Analog Scale, a 0–10 self-reported pain intensity.
- **Cauda equina syndrome** — a surgical emergency from compression of the sacral nerve roots
  (saddle anesthesia, bladder/bowel dysfunction).
- **Valsalva sign** — pain worsened by coughing/straining; suggestive of disc herniation.
- **Neurogenic claudication** — leg pain on walking/standing, relieved by sitting; suggests spinal
  stenosis.
- **Vertex / mesh topology** — the 3D model is a mesh of points (vertices) and triangles (cells);
  "shared topology" means two files list the same vertices in the same order.

---

## 18. Quick-reference fact sheet

- ~5,600 lines of Python · 12 screens · 2 anatomical models · 31 dermatome IDs · bilingual EN/HE (RTL).
- Paint levels: 0 none / 1 mild (yellow) / 2 moderate (orange) / 3 severe (red).
- Six coverage metrics: weighted pain burden · pain area share · local involvement · mean local
  intensity · segmental spread · overlap flag.
- Per-session output: `session.json` + bilingual `session_summary.txt` + `front.png` + `back.png`
  (stored locally).
- Stack: Python 3.11 · PyQt6 6.10.0 · VTK 9.5.2 · NumPy 2.3.5 · Pillow 12.0.0 · PyInstaller 6.17.0.
- Team: Amit Bezalel & Shachar Guttman · Supervisor Prof. Mickey Scheinowitz · TAU BME ·
  partner Loewenstein Rehabilitation Medical Center (Clalit).
- Disclaimer (verbatim): *"PAINDICATOR is a research/decision-support tool. Its analysis is a
  descriptive summary of recorded data and is not a diagnosis or a substitute for clinical judgment,
  physical examination, or imaging."*

---

## 19. Suggested final-report skeleton (you can ask ChatGPT to expand each)

1. Abstract · 2. Introduction & clinical motivation · 3. Background (pain documentation, dermatomes,
prior art / EMR body charts) · 4. Requirements & design goals (with the clinical partner) ·
5. System architecture (layers, ownership, data flow) · 6. 3D interaction engine (per-vertex paint,
normal gating, undo) · 7. Dermatome mapping (`.u8`, topology) · 8. Coverage engine (the §8 metrics &
formulas) · 9. Decision-support analyzer (rule design, explainability) · 10. Data model & persistence ·
11. UX / tablet & bilingual design · 12. Implementation & packaging · 13. Results / example sessions ·
14. Limitations · 15. Future work (heatmap, longitudinal, ML, regulatory) · 16. Conclusion ·
17. References · Appendices (JSON schema, metric definitions, screen list).
