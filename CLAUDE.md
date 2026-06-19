# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Activate the virtual environment first
venv311\Scripts\activate

# Run from the project root (PAINDICATOR/)
python -m codes.app
```

The entry point is `codes/app.py`. Always run from the project root so relative paths (`data/sessions/`, `files/models/`) resolve correctly.

## Building the EXE (PyInstaller)

```bash
venv311\Scripts\activate
pyinstaller app.spec
# Output: dist/app/
```

The spec file handles VTK hidden imports and bundles `codes/`, `files/`, and `data/` directories.

---

## Architecture Overview

### Layer Structure

```
codes/app.py                    ← entry point; creates QApplication, SessionManager, MainWindow
codes/ui_main.py                ← MainWindow with QStackedWidget + FaderWidget fade transitions
codes/session_manager.py        ← single source of truth for all session data
codes/renderer_scene.py         ← VTK pipeline owner; toolbar-facing public API
codes/vtk_interactor_custom.py  ← CustomInteractorStyle; all paint/erase/camera interaction
codes/dermatome_coverage.py     ← pure computation engine for dermatome coverage (VTK-free, no UI)
codes/dermatome_mapper.py       ← loads .u8 map; provides DermatomeMapper used by RendererScene
codes/config.py                 ← EXE-safe path resolution for files/models/
codes/screens/                  ← 12 registered screens (dynamically loaded by name)
codes/widgets/                  ← toolbar, topbar, comment popup
```

### Screen Registration

`MainWindow._register_screens()` dynamically imports screens by filename. The class name convention is `snake_case_name` → `SnakeCaseNameScreen`. Screens are pre-instantiated at startup and reused; navigation is via `main_window.navigate_to("screen_name", **kwargs)`.

Active screens: `role_selection`, `clinician_name`, `clinician_patients`, `clinician_session_selection`, `clinician_view_session`, `patient_id`, `patient_session_choice`, `session_selection`, `gender_selection`, `questionnaire`, `show_model`, `view_session`.

### Data Flow

1. `SessionManager` holds all session state in `self.data` (subject_info, questionnaire, model_data, screenshots).
2. Each screen receives `session_manager` at construction and reads/writes through it.
3. `RendererScene.save_full_session(session_manager)` is the single save entrypoint — it captures screenshots, builds `model_data`, calls `session_manager.save_to_file()` and `save_to_human_readable_file()`.
4. Session folders: `data/sessions/{patient_id}/session_{DD-MM-YYYY_HH-MM-SS}/` containing `session.json`, `session_summary.txt`, `front.png`, `back.png`.

### VTK Pipeline (Critical — Fragile)

`RendererScene` owns all VTK objects: `renderer`, `render_window`, `interactor`, `actor`, `mapper`, `polydata`. It passes them into `CustomInteractorStyle` at construction.

**CustomInteractorStyle (Paint V2):**
- Painting is **per vertex** (not per cell). `point_levels: List[int]` is the canonical paint state.
- Paint colors: `0`=gray (no pain), `1`=yellow, `2`=orange, `3`=red (defined in `COLORS` dict).
- Brush: radius-based using `vtkPointLocator.FindPointsWithinRadius()` + interpolation between drag samples.
- Normal gating: skips vertices whose normal dot camera-direction < `_normal_gate_threshold` (prevents painting through the body).
- Undo: per-stroke dict `{pid: old_level}` pushed to `undo_stack` on `LeftButtonUp`.
- Modes: `NONE`, `VIEW`, `MARK`, `ERASE`. Left-click paints in MARK/ERASE; right-click rotates in MARK/ERASE.

**VTK lifecycle in ShowModelScreen:**
- `RendererScene` is initialized lazily in `showEvent()` (VTK requires a visible widget).
- On `hideEvent()`, the interactor is disabled and all scene references are dropped to prevent native crashes. `_scene_initialized = False` so it reinitializes on next show.
- **Never call `TerminateApp()` or `Finalize()` on the interactor.** Use `interactor.Disable()` only.

### Dermatome System

**Files (male model — `files/models/male model/`):**
- `male_derm_vertex_colors.ply` — painting model + dermatome toggle actor (baked vertex colors)
- `male_derm_vertex_id.u8` — binary file: one uint8 per vertex = dermatome ID (0–30)
- `male_derm_meta.json` — dermatome ID table (C1–C8, T1–T12, L1–L5, S1–S5), vertex counts per dermatome

**Files (female model — `files/models/female model/`):**
- `female_derm_vertex_colors.ply` — painting model
- `female_derm_vertex_colors_fixed.ply` — dermatome toggle actor (~212,196 faces; must NOT be confused with older ~106,098-face variant)
- `female_derm_vertex_id.u8` — per-vertex dermatome ID map
- `female_derm_meta.json` — dermatome ID table + vertex counts

Path resolution via `codes/config.py`: `get_male_model_info()` / `get_female_model_info()` return dicts with all paths.

**Active painting model** must share the same vertex topology as the corresponding `.u8` dermatome map for IDs to align.

**DermatomeMapper** (`codes/dermatome_mapper.py`): loads `.u8` binary as numpy array; `derm_map[vertex_id]` → dermatome ID. Additional methods:
- `get_dermatome_order()` — returns IDs in cranial-to-caudal order (C1 → S5), excluding UNASSIGNED (0).
- `compute_metrics(stats, totals)` — converts raw `{derm_id: {vertices, level_sum}}` stats into per-dermatome metric rows (coverage, avg_pain, pain_index, body_share, severity). Sorted by pain_index descending.

**Centralized coverage engine** (`codes/dermatome_coverage.py`): VTK-free, UI-free pure computation module. Key functions:
- `compute_dermatome_coverage(point_levels, derm_map, ...)` — aggregates per-vertex paint data into dermatome metrics. Returns a structured dict with `analysis_type`, `overall`, and `dermatomes` list.
- `format_dermatome_coverage_for_display(result)` — formats result as plain text for the clinician panel.
- `serialize_dermatome_coverage(result)` — returns JSON-serializable version for `model_data["dermatome_coverage"]`.

**Coverage metrics per dermatome** (in `dermatome_coverage.py`):
- `weighted_pain_burden` = `level_sum / total_painted_mass` — primary ranking metric (relative share of body pain mass)
- `pain_area_share` = `painted_count / total_painted_vertices` — secondary ranking metric
- `local_involvement` = `painted_count / total_derm_vertices` — fraction of dermatome's own vertices painted
- `mean_local_intensity` = `level_sum / painted_count` — average pain level where painted (1–3)
- `segmental_spread` — cranial-caudal span in levels across meaningfully involved dermatomes
- `overlap_flag` — two adjacent dermatomes with close burden scores (potential radiculopathy ambiguity)

**Public API for coverage** (`RendererScene`):
- `compute_dermatome_coverage_result(session_manager=None)` — loads mapper if needed, runs the centralized engine, returns result dict. Safe to call from UI screens.
- `_compute_dermatome_stats_for_save(session_manager)` — internal; serializes result for saving to `model_data["dermatome_coverage"]`.

**Statistics** (low-level) computed in `RendererScene.compute_marked_dermatomes()`: iterates `interactor_style.point_levels`, looks up `derm_map[pid]`, accumulates `{derm_id: {"vertices": count, "level_sum": sum}}`.
Note: the dict key is `"vertices"` (was previously misnamed `"cells"`).

### Path Resolution

`codes/config.py::get_base_models_path()` returns `files/models/` for dev and `sys._MEIPASS/files/models/` for EXE. All model and dermatome file loads must go through this function.

For non-model files (pictures, fonts), `BaseScreen._get_base_path()` applies the same `sys._MEIPASS` pattern.

### BaseScreen

All screens extend `BaseScreen`, which provides:
- Light-blue background (`#BBDCDF`)
- Nunito font loading (with fallback to Arial)
- `create_button()` factory for styled `QPushButton`
- `session_manager` reference

Screens receive `on_load(**kwargs)` calls from `navigate_to()` for data handoff between screens.

---

## Key Design Decisions

- **Per-vertex painting** (not per-cell): enables accurate undo, supports dermatome mapping, avoids shared-vertex over-erase artifacts.
- **Lazy VTK init**: `RendererScene` is created in `showEvent()`, not `__init__()`, because VTK requires the widget to be visible before accessing `GetRenderWindow()`.
- **Fade transitions skip VTK screen**: `navigate_to()` skips `FaderWidget` when `show_model` is involved to avoid rendering artifacts.
- **Session folder is sticky**: `SessionManager.current_session_folder` is set on first save and reused for subsequent saves in the same session. It's cleared in `ShowModelScreen.hideEvent()`.

## Known Issues / In-Progress

- `RendererScene.save_session()` is a legacy method — use `save_full_session()` instead.
- Debug log is written to `paindicator_debug.log` in the working directory at runtime (not `codes/renderer_debug.log`).
- Session JSON key for dermatome data is now `"dermatome_coverage"` (new format). Old sessions use `"dermatome_analysis"` — the summary renderer handles both (legacy fallback in `session_manager.py`).
- L/R side markers: implemented as `vtkTextActor` badges reprojected before every render. If labels appear on the wrong side, the model's X-axis convention may need checking in `RendererScene._setup_lr_marker_positions()`.
- Edit session: after edit+save, `current_session_folder` is cleared in `hideEvent()` as usual. The edited session is correctly overwritten because `current_session_folder` was set before navigating.
- Female dermatome topology: `female_derm_vertex_colors_fixed.ply` (~212,196 faces) must be used for the toggle actor. The older `filled.ply` variant (~106,098 faces) is incompatible.

---

## Product Context & Future Direction (CRITICAL)

### Project Goal
PAINDICATOR is not just a visualization tool — it is a clinical decision-support system.

The goal is to:
- Digitize pain mapping
- Improve accuracy of pain localization
- Enable quantitative analysis (dermatomes, distribution)
- Support clinicians in diagnosis and tracking

---

### Dermatome System (Concept)

We have created a dermatome-mapped 3D model in Blender.

Key idea:
- Each vertex belongs to a dermatome (via `.u8` mapping file)
- Painting is per vertex → directly maps to dermatomes

Goal:
- Convert painted data → dermatome statistics

Outputs we want:
- % coverage per dermatome
- Dominant dermatomes
- Weighted pain distribution
- Future: visual heatmap

---

### Current State

The full dermatome pipeline is implemented for both male and female models:
- `.u8` + `DermatomeMapper` for both genders
- `dermatome_coverage.py` — centralized engine with full metrics
- Clinician panel displays coverage results (HTML table)
- Session JSON stores serialized coverage data
- Dermatome toggle in clinician view — fully working (swap actor + `toggle_model_view()`)
- Multi-session comparison overlay — fully working (blue/violet cool-tone overlay)
- Click-to-identify dermatome name — fully working (floating popup on model click)

Still lacking:

1. Visual heatmap representation of dermatome burden
2. Longitudinal tracking / quantitative multi-session comparison metrics

---

### Next Development Tasks

#### High Priority
- Verify female model topology consistency (painting model vs dermatome toggle PLY)

#### Medium Priority
- Visual heatmap of dermatome burden
- Improve screenshot consistency with fixed camera angles

#### Low Priority
- Longitudinal tracking and quantitative multi-session comparison
- AI/ML-based pattern recognition (rule-based foundation exists in `pain_analyzer.py`; ML model not yet trained)

---

### Engineering Guidelines

When modifying code:

- DO NOT break VTK interaction
- DO NOT change painting model (point_levels) unless necessary
- Always maintain compatibility with saved sessions
- Prefer extending existing systems over rewriting
- Be extremely careful with:
  - interactor lifecycle
  - renderer initialization
  - session saving pipeline

---

### Important Notes for Claude

This is a fragile system:
- UI + VTK tightly coupled
- Small changes can break interaction

Therefore:
- Make minimal, precise changes
- Explain reasoning before major changes
- When unsure → ask before implementing

## Working Rules (CRITICAL)

- Do not make broad refactors unless explicitly requested.
- Prefer minimal, local, safe changes.
- Preserve existing UI flow and screen names.
- Preserve session JSON compatibility.
- Do not rename files, classes, or public methods unless necessary.
- Do not change file structure unless explicitly instructed.
- When modifying code, avoid touching unrelated parts.

- When working with VTK:
  - Be extremely careful not to break interaction.
  - Do not change interactor lifecycle unless absolutely necessary.
  - Never call TerminateApp() or Finalize().
  - Use interactor.Disable() only when needed.

- Before editing code:
  1. Explain what the problem is
  2. Specify which files will be changed
  3. Explain why the change is safe

- When providing code:
  - Provide FULL updated code for each file (not partial snippets)
  - Keep all existing functionality intact
  - Keep code comments in English only

---

## Source of Truth

- SessionManager is the single source of truth for session data.
- RendererScene is the only owner of the VTK pipeline.
- CustomInteractorStyle is the only owner of painting, erase, and mouse interaction.
- Screens should not contain business logic — only UI and flow control.
- Saved session structure must remain backward compatible.

---

## Must Not Break

The following flows MUST always work:

1. Patient flow:
   role_selection → patient_id → gender_selection → questionnaire → show_model → save

2. Clinician flow:
   clinician_name → session_selection → view_session

3. VTK interaction:
   - VIEW mode: left drag rotates
   - MARK/ERASE: left paints, right rotates
   - Undo restores only last action correctly
   - Erase removes paint correctly
   - No painting through the body (normal gating)

4. Saving:
   - JSON is created correctly
   - TXT summary is created
   - Screenshots (front/back) are generated
   - Session folder structure remains unchanged

---

## Current Status Snapshot

### Working
- Full UI navigation flow (patient + clinician)
- Session saving/loading
- Painting system (per vertex, Paint V2)
- Erase
- Undo (per-stroke with granularity chunking)
- Clinician session view
- Screenshot capture (front + back, consistent camera)
- Dermatome coverage analysis pipeline (both male and female models): `dermatome_coverage.py` → `RendererScene.compute_dermatome_coverage_result()` → clinician panel display (HTML table) + session JSON save
- Dermatome toggle in clinician view: swap between painted model and dermatome-region view (`toggle_model_view()`)
- Click-to-identify dermatome: click on model in dermatome view → floating name popup
- Multi-session comparison overlay (cool-tone blue/violet overlay on same model)
- Pain pattern analyzer (rule-based clinical report from dermatome + questionnaire data)
- Patient age field in questionnaire (saved as `"age"` in questionnaire dict)
- L/R orientation labels on 3D model (`vtkTextActor` badges, auto-reprojected per render)
- Edit existing session from clinician session selection screen
- Two-finger pinch zoom (`TouchManager` + `RendererScene.apply_zoom()`)
- Two-finger rotation and pan (`TouchManager`)
- Stylus (tablet pen) painting via inject API
- Virtual keyboard auto-popup on Windows tablet (`TouchKeyboardFilter` in `app.py`)
- Auto-rotate / demo spin mode (navigation panel toggle)

### Partially Implemented / Fragile
- Model topology consistency (female painting model vs female dermatome toggle PLY — verify alignment)
- Screenshot consistency (fixed-camera screenshots partially implemented)
- Painting performance (large models may be slow on older tablets)
- L/R labels orientation — depends on model axis convention; verify L/R swap if labels appear on wrong side

### Not Implemented Yet
- Visual dermatome heatmap
- Quantitative longitudinal comparison metrics
- Product-level UI polish

---

## Dermatome System (IMPORTANT)

- Each vertex is mapped to a dermatome using a `.u8` file
- `dermatome_id = derm_map[vertex_id]`

**Pipeline** (both male and female models):
1. `point_levels` (per vertex) → `RendererScene.compute_dermatome_coverage_result()`
2. → `dermatome_coverage.compute_dermatome_coverage()` (pure math, VTK-free)
3. → structured result dict with `overall` stats and ranked `dermatomes` list
4. For display: `format_dermatome_coverage_for_display(result)` → plain text for clinician panel
5. For saving: `serialize_dermatome_coverage(result)` → stored in `model_data["dermatome_coverage"]`

Key metrics per dermatome: `weighted_pain_burden`, `pain_area_share`, `local_involvement`, `mean_local_intensity`, `segmental_spread`, `overlap_flag`.

Important constraints:
- Model topology must match between painting model and dermatome map
- `"dermatome_coverage"` is the current session JSON key; old sessions use `"dermatome_analysis"` (legacy fallback exists in `session_manager.py`)

---

## Current Priorities

1. Maintain system stability (highest priority)
2. Verify female model topology consistency (painting PLY vs toggle PLY)
3. Visual heatmap of dermatome burden
4. Ensure screenshot consistency
5. Improve painting robustness and performance

## Important Notes

- This is a fragile system: UI + VTK are tightly coupled
- Small mistakes can break interaction completely
- Always prefer minimal, precise fixes over large changes
- If unsure → ask before implementing