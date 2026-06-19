# codes/dermatome_mapper.py
# NOTE: All comments are in English only.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import os
import json
import numpy as np

# Standard dermatome name → ID mapping (C1 unused, IDs 2-30 = C2..S5)
_CANONICAL_NAME_TO_ID: Dict[str, int] = {
    "UNASSIGNED": 0, "C1": 1, "C1_UNUSED": 1,
    "C2": 2,  "C3": 3,  "C4": 4,  "C5": 5,  "C6": 6,  "C7": 7,  "C8": 8,
    "T1": 9,  "T2": 10, "T3": 11, "T4": 12, "T5": 13, "T6": 14,
    "T7": 15, "T8": 16, "T9": 17, "T10": 18, "T11": 19, "T12": 20,
    "L1": 21, "L2": 22, "L3": 23, "L4": 24, "L5": 25,
    "S1": 26, "S2": 27, "S3": 28, "S4": 29, "S5": 30,
}


@dataclass
class DermatomeHit:
    derm_id: int
    derm_name: str


class DermatomeMapper:
    """
    Loads a dermatome id map (uint8) and provides robust lookup utilities.

    Current supported mapping:
      - Per-VERTEX (Point) dermatome ids: len(map) ~ number_of_points
        -> Dermatome for a FACE/CELL is derived by majority-vote over its vertices.

    The mapper is designed to be safe:
      - Handles slightly short BIN files (e.g., missing last bytes)
      - Out-of-range ids -> treated as UNASSIGNED (0)
    """

    def __init__(self, bin_path: str, meta_path: str):
        self.bin_path = bin_path
        self.meta_path = meta_path

        self.derm_map: Optional[np.ndarray] = None  # uint8 array
        self.name_to_id: Dict[str, int] = {}
        self.id_to_name: Dict[int, str] = {}

        # Initialize totals before _load_meta() so that method can populate them.
        # (These must NOT be assigned after _load_meta(), or the loaded values get overwritten.)
        self.total_cells_per_dermatome: Dict[int, int] = {}
        self.total_vertices_per_dermatome: Dict[int, int] = {}

        self._load_meta()
        self._load_bin()
    # ------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------
    def _load_meta(self) -> None:
        if not os.path.exists(self.meta_path):
            raise FileNotFoundError(f"Dermatome meta json not found: {self.meta_path}")

        with open(self.meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        self.total_cells_per_dermatome = {}

        if "id_to_name" in meta:
            # New female-format: explicit id_to_name + distribution_by_id
            raw = meta["id_to_name"]
            self.id_to_name = {int(k): str(v) for k, v in raw.items()}
            self.name_to_id = {str(v): int(k) for k, v in self.id_to_name.items()}
            dist_by_id = meta.get("distribution_by_id") or {}
            self.total_vertices_per_dermatome = {int(k): int(v) for k, v in dist_by_id.items()}

        elif "distribution" in meta and "derm_id_table" not in meta:
            # New male-format: distribution by name only — infer IDs from canonical table
            distribution = meta["distribution"]
            self.name_to_id = {}
            self.id_to_name = {}
            self.total_vertices_per_dermatome = {}
            for name, count in distribution.items():
                nid = _CANONICAL_NAME_TO_ID.get(name)
                if nid is None:
                    continue
                self.name_to_id[name] = nid
                self.id_to_name[nid] = name
                self.total_vertices_per_dermatome[nid] = int(count)

        else:
            # Original format: derm_id_table + total_vertices_per_dermatome
            cells_totals = meta.get("total_cells_per_dermatome") or {}
            verts_totals = meta.get("total_vertices_per_dermatome") or {}
            self.total_cells_per_dermatome = {int(k): int(v) for k, v in cells_totals.items()}
            self.total_vertices_per_dermatome = {int(k): int(v) for k, v in verts_totals.items()}
            table = meta.get("derm_id_table") or {}
            self.name_to_id = {str(k): int(v) for k, v in table.items()}
            self.id_to_name = {int(v): str(k) for k, v in table.items()}

        # Ensure UNASSIGNED exists
        if 0 not in self.id_to_name:
            self.id_to_name[0] = "UNASSIGNED"
        if "UNASSIGNED" not in self.name_to_id:
            self.name_to_id["UNASSIGNED"] = 0

    def _load_bin(self) -> None:
        if not os.path.exists(self.bin_path):
            raise FileNotFoundError(f"Dermatome bin file not found: {self.bin_path}")

        with open(self.bin_path, "rb") as f:
            self.derm_map = np.fromfile(f, dtype=np.uint8)

        if self.derm_map is None or len(self.derm_map) == 0:
            raise RuntimeError("Dermatome bin loaded but is empty.")

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def derm_name(self, derm_id: int) -> str:
        return self.id_to_name.get(int(derm_id), "UNKNOWN")

    def get_dermatome_for_point(self, point_id: int) -> DermatomeHit:
        """
        Return dermatome id/name for a point index.
        Out-of-range -> UNASSIGNED.
        """
        if self.derm_map is None:
            return DermatomeHit(0, self.derm_name(0))

        pid = int(point_id)
        if pid < 0 or pid >= len(self.derm_map):
            return DermatomeHit(0, self.derm_name(0))

        did = int(self.derm_map[pid])
        return DermatomeHit(did, self.derm_name(did))

    def get_dermatome_for_cell(self, polydata, cell_id: int) -> DermatomeHit:
        """
        Compute dermatome for a cell (triangle) using majority vote of its vertices.
        Ties -> UNASSIGNED (0).
        """
        cid = int(cell_id)
        cell = polydata.GetCell(cid)
        if cell is None:
            return DermatomeHit(0, self.derm_name(0))

        ids = cell.GetPointIds()
        n = ids.GetNumberOfIds()
        if n <= 0:
            return DermatomeHit(0, self.derm_name(0))

        counts: Dict[int, int] = {}
        for i in range(n):
            pid = int(ids.GetId(i))
            hit = self.get_dermatome_for_point(pid)
            counts[hit.derm_id] = counts.get(hit.derm_id, 0) + 1

        # Majority vote with tie handling
        items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        if not items:
            return DermatomeHit(0, self.derm_name(0))

        if len(items) > 1 and items[0][1] == items[1][1]:
            return DermatomeHit(0, self.derm_name(0))

        did = int(items[0][0])
        return DermatomeHit(did, self.derm_name(did))

    def compute_marked_dermatomes(self, polydata, marks: Dict[int, int]) -> Dict[int, Dict[str, int]]:
        """
        Aggregate marked cells into dermatome statistics.

        Input:
          marks: {cell_id: level} where level > 0 means painted.

        Output:
          {
            derm_id: {
              "cells": <count of painted cells mapped to this derm>,
              "level_sum": <sum of pain levels for those cells>
            },
            ...
          }
        """
        stats: Dict[int, Dict[str, int]] = {}
        if not marks:
            return stats

        for cell_id, level in marks.items():
            try:
                cid = int(cell_id)
                lvl = int(level)
            except Exception:
                continue

            if lvl <= 0:
                continue

            hit = self.get_dermatome_for_cell(polydata, cid)
            did = hit.derm_id

            if did not in stats:
                stats[did] = {"vertices": 0, "level_sum": 0}

            stats[did]["vertices"] += 1
            stats[did]["level_sum"] += lvl

        return stats

    def get_dermatome_order(self) -> list:
        """
        Return dermatome IDs in cranial-to-caudal order (C1 → S5), excluding UNASSIGNED (0).
        In the current mapping the IDs are assigned in anatomical order (1=C1 … 30=S5),
        so sorting by ascending ID gives the correct sequence.
        """
        return sorted(did for did in self.id_to_name if did != 0)

    def compute_metrics(self, stats: Dict[int, Dict[str, int]], totals: Dict[int, int]) -> list:
        """
        Convert raw dermatome stats into per-dermatome metric rows.
        Excludes UNASSIGNED (id == 0). Sorted by pain_index descending.

        Input:
          stats:  {derm_id: {"vertices": count, "level_sum": sum}}
          totals: {derm_id: total_vertex_count}

        Output: list of dicts —
          derm_id, name, coverage (0–1), avg_pain (1–3), pain_index (0–1),
          body_share (0–1), severity (Mild/Moderate/Severe)
        """
        total_painted_mass = sum(v["level_sum"] for v in stats.values()) or 1

        rows = []
        for derm_id, v in stats.items():
            if derm_id == 0:
                continue
            painted_verts = v["vertices"]
            level_sum     = v["level_sum"]
            total_verts   = totals.get(derm_id, 0)

            coverage   = painted_verts / total_verts if total_verts > 0 else 0.0
            avg_pain   = level_sum / painted_verts   if painted_verts > 0 else 0.0
            pain_index = (avg_pain / 3.0) * coverage
            body_share = level_sum / total_painted_mass

            if avg_pain >= 2.5:
                severity = "Severe"
            elif avg_pain >= 1.5:
                severity = "Moderate"
            else:
                severity = "Mild"

            rows.append({
                "derm_id":    derm_id,
                "name":       self.derm_name(derm_id),
                "coverage":   coverage,
                "avg_pain":   avg_pain,
                "pain_index": pain_index,
                "body_share": body_share,
                "severity":   severity,
            })

        rows.sort(key=lambda x: x["pain_index"], reverse=True)
        return rows