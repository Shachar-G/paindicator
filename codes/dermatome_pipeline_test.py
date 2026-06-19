# dermatome_pipeline_test.py
# Standalone dermatome computation test.
# Does NOT integrate with the main application.

import json
import vtk
from collections import defaultdict

ATLAS_PATH = r"C:\Users\GuttmanShachar\Documents\PAINDICATOR\files\models\Body_DermatomeAtlas_Test.ply"
SESSION_PATH = r"C:\Users\GuttmanShachar\Documents\PAINDICATOR\data\sessions\208580902\session_21-02-2026_13-59-02\session.json"
def load_atlas_cell_rgb(path):
    reader = vtk.vtkPLYReader()
    reader.SetFileName(path)
    reader.Update()

    poly = reader.GetOutput()
    rgb_arr = poly.GetPointData().GetArray("RGBA")
    if rgb_arr is None:
        raise RuntimeError("RGBA array not found in atlas.")

    cell_rgb = []
    ids = vtk.vtkIdList()

    for cid in range(poly.GetNumberOfCells()):
        poly.GetCellPoints(cid, ids)

        counts = defaultdict(int)

        for i in range(ids.GetNumberOfIds()):
            pid = ids.GetId(i)
            r, g, b, _ = rgb_arr.GetTuple(pid)
            rgb = (int(r), int(g), int(b))
            counts[rgb] += 1

        majority = max(counts.items(), key=lambda x: x[1])[0]
        cell_rgb.append(majority)

    return cell_rgb


def load_session_marks(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    marks = data.get("model_data", {}).get("marks", {})
    return {int(k): int(v) for k, v in marks.items()}


def summarize_dermatomes(painted_cells, cell_rgb):
    rgb_to_label = {
        (0, 0, 0): "UNLABELED",
        (254, 0, 0): "UPPER_BACK",
        (0, 0, 254): "LOWER_BACK",
    }

    counts = defaultdict(int)
    weighted = defaultdict(float)
    unmapped = 0

    for cid, lvl in painted_cells.items():
        if cid >= len(cell_rgb):
            continue

        rgb = cell_rgb[cid]
        label = rgb_to_label.get(rgb, "UNLABELED")

        if label == "UNLABELED":
            unmapped += 1
            continue

        counts[label] += 1
        weighted[label] += lvl

    print("\n=== Dermatome Summary ===")
    for label in sorted(counts.keys(), key=lambda x: counts[x], reverse=True):
        print(f"{label}: {counts[label]} cells | weighted pain = {weighted[label]}")

    print(f"\nUnmapped cells: {unmapped}")
    print(f"Total painted cells: {len(painted_cells)}")


def main():
    print("Loading atlas...")
    cell_rgb = load_atlas_cell_rgb(ATLAS_PATH)

    print("Loading session...")
    marks = load_session_marks(SESSION_PATH)

    summarize_dermatomes(marks, cell_rgb)


if __name__ == "__main__":
    main()