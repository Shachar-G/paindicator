"""
Recolor a dermatome PLY file using a custom color scheme.
Reads the .u8 vertex ID map and rewrites vertex colors in the ASCII PLY.

Usage: python recolor_dermatome.py
Output: filesttt/male_derm_RECOLORED.ply
"""

import os
import numpy as np

BASE    = os.path.join(os.path.dirname(__file__), "files", "models", "claudeV")
U8_IN   = os.path.join(BASE, "male_derm_vertex_id.u8")
PLY_IN  = os.path.join(BASE, "male_derm_vertex_colors.ply")
PLY_OUT = os.path.join(BASE, "male_derm_vertex_colors.ply")

# --- Color scheme (RGB 0-255) ---
GRAY = (200, 200, 200)

DERM_COLORS = {
    0:  GRAY,  # UNASSIGNED
    1:  GRAY,  # C1 (unused)

    # Cervical C2-C8 — purple tones
    # Even ID = dark, odd ID = light
    2:  (160,  40, 190),  # C2 dark purple
    3:  (225, 120, 235),  # C3 light purple
    4:  (160,  40, 190),  # C4 dark purple
    5:  (225, 120, 235),  # C5 light purple
    6:  (160,  40, 190),  # C6 dark purple
    7:  (225, 120, 235),  # C7 light purple
    8:  (160,  40, 190),  # C8 dark purple

    # Thoracic T1-T12 — yellow/orange tones
    # Even ID = dark, odd ID = light
    9:  (255, 230, 120),  # T1 light yellow
    10: (235, 165,  30),  # T2 dark yellow/orange
    11: (255, 230, 120),  # T3 light yellow
    12: (235, 165,  30),  # T4 dark yellow/orange
    13: (255, 230, 120),  # T5 light yellow
    14: (235, 165,  30),  # T6 dark yellow/orange
    15: (255, 230, 120),  # T7 light yellow
    16: (235, 165,  30),  # T8 dark yellow/orange
    17: (255, 230, 120),  # T9 light yellow
    18: (235, 165,  30),  # T10 dark yellow/orange
    19: (255, 230, 120),  # T11 light yellow
    20: (235, 165,  30),  # T12 dark yellow/orange

    # Lumbar L1-L5 — cyan/light-blue tones
    # Even ID = dark, odd ID = light
    21: (120, 230, 235),  # L1 light cyan
    22: ( 30, 175, 190),  # L2 dark cyan
    23: (120, 230, 235),  # L3 light cyan
    24: ( 30, 175, 190),  # L4 dark cyan
    25: (120, 230, 235),  # L5 light cyan

    # Sacral S1-S5 — red tones
    # Even ID = dark, odd ID = light
    26: (210,  70,  55),  # S1 dark red
    27: (255, 135, 115),  # S2 light red
    28: (210,  70,  55),  # S3 dark red
    29: (255, 135, 115),  # S4 light red
    30: (210,  70,  55),  # S5 dark red
}

# --- Load dermatome ID map ---
derm_map = np.frombuffer(open(U8_IN, "rb").read(), dtype=np.uint8)
print(f"Loaded .u8: {len(derm_map)} vertices")

# --- Parse PLY header ---
with open(PLY_IN, "rb") as f:
    header_lines = []
    while True:
        line = f.readline()
        header_lines.append(line)
        if line.strip() == b"end_header":
            break
    body = f.read()

header = b"".join(header_lines).decode("ascii")
print("Header OK")

# --- Parse vertex count from header ---
n_verts = None
n_faces = None
for line in header_lines:
    l = line.decode("ascii").strip()
    if l.startswith("element vertex"):
        n_verts = int(l.split()[-1])
    elif l.startswith("element face"):
        n_faces = int(l.split()[-1])

print(f"Vertices: {n_verts}, Faces: {n_faces}")
assert n_verts == len(derm_map), f"Mismatch: PLY={n_verts}, u8={len(derm_map)}"

# --- Split body into vertex lines and face lines ---
lines = body.split(b"\n")
# Remove trailing empty
while lines and lines[-1].strip() == b"":
    lines.pop()

vertex_lines = lines[:n_verts]
face_lines   = lines[n_verts:]

print(f"Parsed {len(vertex_lines)} vertex lines, {len(face_lines)} face lines")

# --- Recolor vertices ---
new_vertex_lines = []
for i, vline in enumerate(vertex_lines):
    parts = vline.split()
    x, y, z = parts[0], parts[1], parts[2]
    derm_id = int(derm_map[i])
    r, g, b = DERM_COLORS.get(derm_id, GRAY)
    new_vertex_lines.append(f"{x.decode()} {y.decode()} {z.decode()} {r} {g} {b}".encode())

# --- Write output ---
new_body = b"\n".join(new_vertex_lines) + b"\n" + b"\n".join(face_lines) + b"\n"

with open(PLY_OUT, "wb") as f:
    f.write(header.encode("ascii"))
    f.write(new_body)

print(f"Written: {PLY_OUT}")
