"""
Quick standalone preview for the new male dermatome model.
Run with:  python preview_model.py [clean|derm]
  clean  = base gray mesh
  derm   = dermatome-colored overlay [default]

Controls:
  VIEW mode  — left-drag rotates, scroll zooms
  PICK mode  — click on the model to highlight a dermatome
  P key      — toggle between VIEW and PICK mode
  Click the on-screen mode button to toggle as well.
"""

import sys
import os
import json
import  numpy as np

PLY_DIR   = os.path.join(os.path.dirname(__file__), "files", "models", "female final")
MAP_DIR   = os.path.join(os.path.dirname(__file__), "files", "models", "female model")
MODEL_DIR = PLY_DIR  # kept for window title

FILES = {
    "clean": "female_derm_vertex_colors_filled.ply",
    "derm":  "female_derm_vertex_colors_filled.ply",
}
U8_FILE   = os.path.join(MAP_DIR, "female_derm_vertex_id.u8")
META_FILE = os.path.join(MAP_DIR, "female_derm_meta.json")

mode = sys.argv[1] if len(sys.argv) > 1 else "derm"
if mode not in FILES:
    print(f"Unknown mode '{mode}'. Use: clean | derm")
    sys.exit(1)

ply_path = os.path.join(PLY_DIR, FILES[mode])
print(f"Loading: {ply_path}")

import vtk

# ── Dermatome map ─────────────────────────────────────────────────────────────
derm_map = np.fromfile(U8_FILE, dtype=np.uint8)
with open(META_FILE, "r", encoding="utf-8") as f:
    meta = json.load(f)

table = meta.get("derm_id_table") or {}
id_to_name = {int(v): str(k) for k, v in table.items()}
id_to_name[0] = "UNASSIGNED"
print(f"Dermatome map: {len(derm_map)} vertices, {len(id_to_name)} named groups")

# ── Color scheme by dermatome name (works for both male and female IDs) ────────
_GRAY = (200, 200, 200)
_NAME_COLORS = {
    "UNASSIGNED": _GRAY,
    "C1": _GRAY,
    "C2": (160,  40, 190), "C3": (225, 120, 235),
    "C4": (160,  40, 190), "C5": (225, 120, 235),
    "C6": (160,  40, 190), "C7": (225, 120, 235),
    "C8": (160,  40, 190),
    "T1":  (255, 230, 120), "T2":  (235, 165,  30),
    "T3":  (255, 230, 120), "T4":  (235, 165,  30),
    "T5":  (255, 230, 120), "T6":  (235, 165,  30),
    "T7":  (255, 230, 120), "T8":  (235, 165,  30),
    "T9":  (255, 230, 120), "T10": (235, 165,  30),
    "T11": (255, 230, 120), "T12": (235, 165,  30),
    "L1": (120, 230, 235), "L2": ( 30, 175, 190),
    "L3": (120, 230, 235), "L4": ( 30, 175, 190),
    "L5": (120, 230, 235),
    "S1": (210,  70,  55), "S2": (255, 135, 115),
    "S3": (210,  70,  55), "S4": (255, 135, 115),
    "S5": (210,  70,  55),
}

# ── Reader ────────────────────────────────────────────────────────────────────
reader = vtk.vtkPLYReader()
reader.SetFileName(ply_path)
reader.Update()

pd      = reader.GetOutput()
n_pts   = pd.GetNumberOfPoints()
n_cells = pd.GetNumberOfCells()
print(f"Vertices: {n_pts}  Faces: {n_cells}")

# Always apply dermatome colors from the .u8 map (works even without PLY vertex colors)
print("Applying dermatome colors…", end=" ", flush=True)
color_array = vtk.vtkUnsignedCharArray()
color_array.SetNumberOfComponents(3)
color_array.SetNumberOfTuples(n_pts)
color_array.SetName("DermColors")
usable = min(len(derm_map), n_pts)
for i in range(usable):
    name = id_to_name.get(int(derm_map[i]), "UNASSIGNED")
    r, g, b = _NAME_COLORS.get(name, _GRAY)
    color_array.SetTuple3(i, r, g, b)
for i in range(usable, n_pts):
    color_array.SetTuple3(i, *_GRAY)
pd.GetPointData().SetScalars(color_array)
has_colors = True
print("done")

# ── Build per-dermatome face lists (majority vote per cell) ───────────────────
print("Building dermatome cell index…", end=" ", flush=True)
derm_cell_index = {}
for cid in range(n_cells):
    cell   = pd.GetCell(cid)
    pt_ids = cell.GetPointIds()
    counts = {}
    for i in range(pt_ids.GetNumberOfIds()):
        pid = int(pt_ids.GetId(i))
        did = int(derm_map[pid]) if pid < len(derm_map) else 0
        counts[did] = counts.get(did, 0) + 1
    dominant = max(counts, key=counts.get) if counts else 0
    derm_cell_index.setdefault(dominant, []).append(cid)
print(f"done ({len(derm_cell_index)} groups)")

# ── Main mesh actor ───────────────────────────────────────────────────────────
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(reader.GetOutputPort())
if has_colors:
    mapper.ScalarVisibilityOn()
    mapper.SetColorModeToDirectScalars()
else:
    mapper.ScalarVisibilityOff()

actor = vtk.vtkActor()
actor.SetMapper(mapper)
if not has_colors:
    actor.GetProperty().SetColor(0.75, 0.75, 0.75)

# ── Highlight / glow actor ────────────────────────────────────────────────────
hi_mapper = vtk.vtkPolyDataMapper()
hi_mapper.ScalarVisibilityOff()

hi_actor = vtk.vtkActor()
hi_actor.SetMapper(hi_mapper)
hi_actor.GetProperty().SetColor(1.0, 0.92, 0.15)
hi_actor.GetProperty().SetAmbient(1.0)
hi_actor.GetProperty().SetDiffuse(0.2)
hi_actor.GetProperty().SetSpecular(0.8)
hi_actor.GetProperty().SetSpecularPower(60)
hi_actor.GetProperty().SetOpacity(0.72)
hi_actor.VisibilityOff()

# ── Dermatome label (bottom-left) ─────────────────────────────────────────────
derm_label = vtk.vtkTextActor()
tp = derm_label.GetTextProperty()
tp.SetFontSize(26)
tp.SetColor(1.0, 0.92, 0.15)
tp.SetBold(True)
tp.SetShadow(True)
tp.SetShadowOffset(2, -2)
derm_label.SetInput("")
derm_label.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
derm_label.SetPosition(0.03, 0.04)

# ── Mode button (top-right) ───────────────────────────────────────────────────
mode_btn = vtk.vtkTextActor()
tp2 = mode_btn.GetTextProperty()
tp2.SetFontSize(20)
tp2.SetBold(True)
tp2.SetShadow(True)
tp2.SetShadowOffset(1, -1)
mode_btn.GetPositionCoordinate().SetCoordinateSystemToNormalizedDisplay()
mode_btn.SetPosition(0.62, 0.93)

# ── Renderer / window ─────────────────────────────────────────────────────────
renderer = vtk.vtkRenderer()
renderer.AddActor(actor)
renderer.AddActor(hi_actor)
renderer.AddActor2D(derm_label)
renderer.AddActor2D(mode_btn)
renderer.SetBackground(0.15, 0.15, 0.15)
renderer.ResetCamera()

win = vtk.vtkRenderWindow()
win.SetWindowName(f"PAINDICATOR preview — {FILES[mode]}")
win.SetSize(900, 700)
win.AddRenderer(renderer)

iren = vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(win)

# ── Two interactor styles ─────────────────────────────────────────────────────
view_style = vtk.vtkInteractorStyleTrackballCamera()  # rotate + zoom
pick_style = vtk.vtkInteractorStyle()                 # no camera movement

# ── App mode state ────────────────────────────────────────────────────────────
app_mode = ["VIEW"]   # "VIEW" | "PICK"

def _update_mode_btn():
    if app_mode[0] == "VIEW":
        mode_btn.SetInput("[ VIEW ]  PICK   (P)")
        mode_btn.GetTextProperty().SetColor(0.5, 0.9, 1.0)
    else:
        mode_btn.SetInput("  VIEW  [ PICK ] (P)")
        mode_btn.GetTextProperty().SetColor(1.0, 0.92, 0.15)

def _toggle_mode():
    if app_mode[0] == "VIEW":
        app_mode[0] = "PICK"
        iren.SetInteractorStyle(pick_style)
    else:
        app_mode[0] = "VIEW"
        iren.SetInteractorStyle(view_style)
        _deselect()
    _update_mode_btn()
    print(f"Mode: {app_mode[0]}")
    win.Render()

# ── Geometry extraction (cached per dermatome) ────────────────────────────────
_hi_cache = {}

def _get_highlight_pd(derm_id):
    if derm_id in _hi_cache:
        return _hi_cache[derm_id]
    cell_ids = derm_cell_index.get(derm_id, [])
    if not cell_ids:
        return None
    id_list = vtk.vtkIdList()
    for cid in cell_ids:
        id_list.InsertNextId(cid)
    extract = vtk.vtkExtractCells()
    extract.SetInputData(pd)
    extract.SetCellList(id_list)
    extract.Update()
    geom = vtk.vtkGeometryFilter()
    geom.SetInputConnection(extract.GetOutputPort())
    geom.Update()
    result = geom.GetOutput()
    _hi_cache[derm_id] = result
    return result

# ── Picker logic ──────────────────────────────────────────────────────────────
picker       = vtk.vtkCellPicker()
picker.SetTolerance(0.005)
current_derm = [None]

def _deselect():
    current_derm[0] = None
    hi_actor.VisibilityOff()
    derm_label.SetInput("")
    win.Render()

def _do_pick(x, y):
    picker.Pick(x, y, 0, renderer)
    cell_id = picker.GetCellId()
    if cell_id < 0:
        _deselect()
        return

    cell   = pd.GetCell(cell_id)
    pt_ids = cell.GetPointIds()
    counts = {}
    for i in range(pt_ids.GetNumberOfIds()):
        pid = int(pt_ids.GetId(i))
        did = int(derm_map[pid]) if pid < len(derm_map) else 0
        counts[did] = counts.get(did, 0) + 1
    did = max(counts, key=counts.get) if counts else 0

    if did == current_derm[0]:
        _deselect()
        return

    current_derm[0] = did
    dname  = id_to_name.get(did, "UNKNOWN")
    hi_pd  = _get_highlight_pd(did)
    n_face = len(derm_cell_index.get(did, []))

    if hi_pd:
        hi_mapper.SetInputData(hi_pd)
        hi_actor.VisibilityOn()
    else:
        hi_actor.VisibilityOff()

    derm_label.SetInput(f"Dermatome: {dname}  ({n_face} faces)")
    print(f"Selected: {dname}  (id={did}, faces={n_face})")
    win.Render()

# ── Input observers ───────────────────────────────────────────────────────────
def _on_left_release(obj, event):
    x, y = iren.GetEventPosition()
    w, h = win.GetSize()
    # Click on mode button area (top-right ~38% width, top ~8% height)
    if y > h * 0.88 and x > w * 0.60:
        _toggle_mode()
        return
    # Pick only in PICK mode
    if app_mode[0] == "PICK":
        _do_pick(x, y)

def _on_key(obj, event):
    key = iren.GetKeySym()
    if key and key.lower() == "p":
        _toggle_mode()

iren.AddObserver("LeftButtonReleaseEvent", _on_left_release)
iren.AddObserver("KeyPressEvent",          _on_key)

# ── Start ─────────────────────────────────────────────────────────────────────
iren.SetInteractorStyle(view_style)
_update_mode_btn()
renderer.ResetCamera()
win.Render()
print("Window open.  P = toggle VIEW/PICK mode  |  Click button top-right  |  Close = exit")
iren.Initialize()
iren.Start()
