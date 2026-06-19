"""
Dermatome remapping script — coordinate-based, clean boundaries.

Coordinate system (from PLY inspection):
  Z = height  (0 = feet, ~8.87 = top of head)
  Y = left-right  (symmetric, |Y| grows toward arms/hands)
  X = front-back  (positive = front/chest, negative = back)

Run from PAINDICATOR root:
  venv311\Scripts\python.exe remap_dermatomes.py
"""

import numpy as np
import struct
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
INPUT_PLY  = ROOT / "files/models/claudeV/male_derm_vertex_colors.ply"
OUTPUT_U8  = ROOT / "files/models/male_derm_vertex_id_v2.u8"
OUTPUT_PLY = ROOT / "files/models/male_derm_vertex_colors_v2.ply"
OUTPUT_META= ROOT / "files/models/male_derm_meta_v2.json"

# ---------------------------------------------------------------------------
# Dermatome ID table  (matches existing app convention)
# ---------------------------------------------------------------------------
DERM_NAMES = {
    0:"UNASSIGNED",
    2:"C2", 3:"C3", 4:"C4",
    5:"C5", 6:"C6", 7:"C7", 8:"C8",
    9:"T1",
    10:"T2",11:"T3",12:"T4",13:"T5",14:"T6",
    15:"T7",16:"T8",17:"T9",18:"T10",19:"T11",20:"T12",
    21:"L1",22:"L2",23:"L3",24:"L4",25:"L5",
    26:"S1",27:"S2",28:"S3",29:"S4",30:"S5",
}

# ---------------------------------------------------------------------------
# Visualization colors  (for the output PLY)
# ---------------------------------------------------------------------------
DERM_COLORS = {
    0: (128,128,128),   # unassigned — gray
    # Cervical — pink/magenta family
    2: (220, 80,180),   3: (210, 90,185),   4: (200,100,190),
    5: (190,110,195),   6: (180,120,200),   7: (170,130,205),   8: (160,140,210),
    # T1 — transition
    9: (230,130, 60),
    # Thoracic — yellow/orange bands (alternating for visibility)
    10:(255,220,100),  11:(240,200, 80),  12:(255,215, 90),  13:(240,195, 70),
    14:(255,200, 80),  15:(240,185, 65),  16:(255,195, 75),  17:(240,180, 60),
    18:(255,190, 70),  19:(235,175, 55),  20:(255,185, 65),
    # Lumbar — teal/cyan
    21:( 60,200,200),  22:( 50,190,210),  23:( 40,185,215),
    24:( 35,180,220),  25:( 45,175,215),
    # Sacral — red/coral
    26:(220, 70, 60),  27:(200, 80, 70),  28:(180, 90, 80),
    29:(160,100, 90),  30:(140,110,100),
}

# ---------------------------------------------------------------------------
# Thoracic Z-boundaries  (based on measured mean Z of existing mapping;
# boundaries placed at midpoints → perfectly horizontal cuts on trunk)
# ---------------------------------------------------------------------------
# Centers: T2=6.947, T3=6.791, T4=6.633, T5=6.455, T6=6.303, T7=6.134,
#          T8=5.975, T9=5.823, T10=5.648, T11=5.447, T12=5.291
# T1 trunk strip: Z = 6.869 – 7.10 (narrow axillary band, below C4)
# T2: Z = 6.712 – 6.869  (note: T1 strip sits ABOVE T2)
THORACIC_Z_BOUNDS = [
    (10, 6.712),   # T2  6.712 – 6.869
    (11, 6.544),   # T3  6.544 – 6.712
    (12, 6.379),   # T4  6.379 – 6.544
    (13, 6.219),   # T5  6.219 – 6.379
    (14, 6.055),   # T6  6.055 – 6.219
    (15, 5.899),   # T7  5.899 – 6.055
    (16, 5.736),   # T8  5.736 – 5.899
    (17, 5.548),   # T9  5.548 – 5.736
    (18, 5.369),   # T10 5.369 – 5.548
    (19, 5.190),   # T11 5.190 – 5.369
    (20, 5.020),   # T12 5.020 – 5.190
]
THORACIC_Z_MIN = 5.020   # below this → L1 / pelvic territory

def thoracic_band(z_val):
    for did, lower in THORACIC_Z_BOUNDS:
        if z_val >= lower:
            return did
    return 0   # shouldn't reach here (guarded by THORACIC_Z_MIN check)


# ---------------------------------------------------------------------------
# Arm boundary  — |Y| threshold varies linearly with height.
# Tuned so forearm at Z=4-5.5 is captured correctly.
# At shoulder (Z=6.8)  threshold ≈ 0.36
# At elbow    (Z=5.5)  threshold ≈ 0.52
# At wrist    (Z=4.0)  threshold ≈ 0.68
# Below Z=3.0 (legs)   no arm
# ---------------------------------------------------------------------------
def arm_threshold(z_val):
    if z_val >= 6.8:
        return 0.36
    elif z_val >= 5.5:
        t = (6.8 - z_val) / (6.8 - 5.5)
        return 0.36 + t * (0.52 - 0.36)
    elif z_val >= 4.0:
        t = (5.5 - z_val) / (5.5 - 4.0)
        return 0.52 + t * (0.68 - 0.52)
    else:
        return 0.72


def is_arm(abs_y, z_val):
    return 3.0 <= z_val <= 7.4 and abs_y > arm_threshold(z_val)


# ---------------------------------------------------------------------------
# Core assignment function
# ---------------------------------------------------------------------------
def assign(xi, yi, zi):
    abs_y = abs(yi)

    # ── ARMS ────────────────────────────────────────────────────────────────
    if is_arm(abs_y, zi):
        # arm_level: 0.0 = shoulder (Z=6.8), 1.0 = hand (Z=3.5)
        arm_lvl = (6.8 - zi) / (6.8 - 3.5)
        arm_lvl = max(0.0, min(1.0, arm_lvl))

        medial_dist = abs_y - arm_threshold(zi)   # 0 = arm edge, grows outward

        if arm_lvl < 0.35:
            # Shoulder / upper arm  (Z roughly 5.65 – 7.4)
            if xi > 0.0:           # anterior / deltoid
                return 5           # C5
            else:                  # posterior upper arm
                if medial_dist < 0.22:
                    return 9       # T1 — medial axillary strip
                return 5           # C5 posterior deltoid

        elif arm_lvl < 0.65:
            # Mid arm  (Z roughly 4.6 – 5.65)
            if xi > 0.05:          # anterior
                return 5           # C5 lateral
            elif medial_dist < 0.18:
                return 9           # T1 medial
            else:
                return 7           # C7 posterior

        else:
            # Forearm / wrist / hand  (Z roughly 3.0 – 4.6)
            if xi > 0.12:          # ventral → C6 (thumb side)
                return 6
            elif xi < -0.08:       # dorsal → C7
                return 7
            else:                  # medial/ulnar → C8
                return 8

    # ── HEAD ────────────────────────────────────────────────────────────────
    if zi > 7.75:
        return 2   # C2 — scalp, face, most of head

    # ── NECK ────────────────────────────────────────────────────────────────
    if zi > 7.35:
        return 3   # C3 — lower neck
    if zi > 7.10:
        return 4   # C4 — shoulder girdle level

    # ── T1 narrow strip (axillary / upper inner chest) ─────────────────────
    # Sits just below C4 and above T2
    if zi > 6.869:
        return 9   # T1

    # ── THORACIC TRUNK (T2 – T12) ──────────────────────────────────────────
    if zi > THORACIC_Z_MIN:
        return thoracic_band(zi)

    # ── L1 — lower abdomen / inguinal / groin ──────────────────────────────
    if zi > 3.80:
        return 21  # L1

    # ── PELVIC / PERINEAL TRANSITION (Z 3.4 – 3.8) ─────────────────────────
    if zi > 3.40:
        if abs_y < 0.18:
            if xi > -0.20:
                return 28  # S3 perineal
            else:
                return 29  # S4 perianal
        return 27  # S2 — inner thigh / lower buttock

    # ── LEGS ────────────────────────────────────────────────────────────────
    if zi > 2.80:
        # Upper thigh
        if xi > 0.05:
            return 22  # L2 anterior thigh
        else:
            return 27  # S2 posterior thigh

    if zi > 2.00:
        # Mid-thigh
        if xi > 0.05:
            return 23  # L3 anterior/medial thigh
        else:
            return 26  # S1 posterior thigh

    if zi > 1.20:
        # Knee + upper shin
        if xi > 0.05 and abs_y < 0.45:
            return 24  # L4 medial shin
        elif xi > 0.0:
            return 25  # L5 lateral shin
        else:
            return 26  # S1 posterior calf

    if zi > 0.50:
        # Ankle
        if xi > 0.0:
            return 25  # L5
        elif abs_y < 0.30:
            return 24  # L4 medial malleolus
        else:
            return 26  # S1 lateral heel

    # ── FEET ────────────────────────────────────────────────────────────────
    if xi > 0.0:
        return 25  # L5 dorsum
    return 26      # S1 plantar / lateral heel


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Reading PLY...")
    verts = []
    face_lines = []
    in_faces = False

    with open(INPUT_PLY, "r") as f:
        for line in f:
            if line.strip() == "end_header":
                break
        for line in f:
            parts = line.strip().split()
            if len(parts) == 6:
                verts.append([float(p) for p in parts[:3]])
            else:
                face_lines.append(line)
                in_faces = True

    verts = np.array(verts, dtype=np.float32)
    n = len(verts)
    print(f"  {n} vertices loaded")

    # Assign dermatome IDs
    print("Assigning dermatomes...")
    ids = np.zeros(n, dtype=np.uint8)
    x_arr, y_arr, z_arr = verts[:, 0], verts[:, 1], verts[:, 2]

    for i in range(n):
        ids[i] = assign(x_arr[i], y_arr[i], z_arr[i])

    # Coverage report
    print("\nDermatome coverage:")
    dist = {}
    for did, name in sorted(DERM_NAMES.items()):
        cnt = int((ids == did).sum())
        if cnt > 0:
            dist[name] = cnt
            pct = cnt / n * 100
            print(f"  {name:12s}: {cnt:6d}  ({pct:.2f}%)")

    unassigned = int((ids == 0).sum())
    coverage = (n - unassigned) / n * 100
    print(f"\n  Total coverage: {coverage:.2f}%  ({n - unassigned}/{n})")

    # Write .u8
    print(f"\nWriting {OUTPUT_U8} ...")
    OUTPUT_U8.write_bytes(ids.tobytes())

    # Write colored PLY
    print(f"Writing {OUTPUT_PLY} ...")
    with open(OUTPUT_PLY, "w") as f:
        f.write("ply\nformat ascii 1.0\n")
        f.write(f"element vertex {n}\n")
        f.write("property float x\nproperty float y\nproperty float z\n")
        f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write(f"element face {len(face_lines)}\n")
        f.write("property list uchar uint vertex_indices\n")
        f.write("end_header\n")
        for i in range(n):
            r, g, b = DERM_COLORS.get(int(ids[i]), (128, 128, 128))
            f.write(f"{verts[i,0]:.6f} {verts[i,1]:.6f} {verts[i,2]:.6f} {r} {g} {b}\n")
        for line in face_lines:
            f.write(line)

    # Write meta JSON
    meta = {
        "version": "v2-coordinate-based",
        "vertex_count": n,
        "coverage_percent": coverage,
        "distribution": dist,
        "notes": "Boundaries derived from 3D coordinates (Z=height, Y=lateral, X=front-back). Thoracic bands use Z-only cuts for smooth horizontal boundaries."
    }
    OUTPUT_META.write_text(json.dumps(meta, indent=2))
    print(f"Wrote {OUTPUT_META}")
    print("\nDone. Review the PLY in MeshLab/Blender, then copy the .u8 to production.")


if __name__ == "__main__":
    main()
