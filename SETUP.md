# PAINDICATOR — New Machine Setup

## Prerequisites

- **Windows 10 or 11** (64-bit)
- **Python 3.11** (exact version required — VTK and PyQt6 wheels are version-specific)
  - Download from: https://www.python.org/downloads/release/python-3119/
  - During install: check "Add Python to PATH"

---

## Step 1 — Clone / restore the project

Copy the backed-up `PAINDICATOR/` folder to your target location, e.g.:

```
C:\Users\YourName\Documents\PAINDICATOR\
```

---

## Step 2 — Create the virtual environment

Open a terminal in the `PAINDICATOR/` folder:

```bash
python -m venv venv311
```

---

## Step 3 — Install dependencies

```bash
venv311\Scripts\activate
pip install -r requirements.txt
```

This installs:
| Package | Version | Purpose |
|---------|---------|---------|
| PyQt6 | 6.10.0 | UI framework |
| vtk | 9.5.2 | 3D rendering engine |
| numpy | 2.3.5 | Dermatome array ops |
| Pillow | 12.0.0 | Screenshot capture |
| pyinstaller | 6.17.0 | EXE build tool |

Installation takes a few minutes (VTK is ~200 MB).

---

## Step 4 — Run the application

Always run from the project root so relative paths resolve correctly:

```bash
venv311\Scripts\activate
python -m codes.app
```

---

## Step 5 — Verify it works

On first launch you should see the role selection screen (Clinician / Patient).
The 3D model loads from `files/models/`. Sessions are saved to `data/sessions/`.

---

## Building the EXE (optional)

```bash
venv311\Scripts\activate
pyinstaller app.spec
```

Output: `dist/app/` — copy the entire folder to deploy.

---

## Troubleshooting

**"No module named vtk"** — make sure you activated the venv before running.

**VTK window is blank / crashes on show** — known issue if the widget isn't visible before VTK init. The app handles this via lazy init in `showEvent()`. If it crashes, check that Python 3.11 is being used (not 3.12+).

**Tablet virtual keyboard doesn't appear** — requires Windows tablet mode or touch input enabled in system settings.

**Wrong L/R orientation labels** — if left/right appear swapped on the 3D model, see `RendererScene._add_side_markers()` in `codes/renderer_scene.py`.

---

## Project structure (quick reference)

```
PAINDICATOR/
  codes/           <- all Python source
  files/models/    <- 3D .ply models + dermatome .u8 maps
  files/fonts/     <- Nunito font
  data/sessions/   <- saved patient sessions (created at runtime)
  venv311/         <- virtual environment (do not commit)
  app.spec         <- PyInstaller build spec
  requirements.txt <- pinned dependencies
```

---

## For Claude Code

See `CLAUDE.md` for architecture details, design decisions, and working rules.
