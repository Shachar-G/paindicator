# codes/dermatome_coverage.py
# Pure computation engine for anatomical dermatome coverage analysis.
# This module is VTK-free and has no UI dependencies — it only does math.
# NOTE: All comments are in English only.

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class DermatomeOptions:
    """Configurable thresholds for coverage analysis. Change here only."""
    # Number of top dermatomes to show in display
    top_n: int = 5
    # Absolute distance from rank-N burden to qualify as "close competitor"
    close_competitor_threshold: float = 0.03
    # Thresholds to count a dermatome as "meaningfully involved" for segmental spread
    meaningful_burden_threshold: float = 0.05
    meaningful_area_share_threshold: float = 0.05
    # Min burden to qualify for overlap detection
    overlap_burden_threshold: float = 0.05
    # Max relative difference between two adjacent dermatomes to flag as overlapping
    overlap_relative_diff: float = 0.30


def compute_dermatome_coverage(
    point_levels: List[int],
    derm_map,                               # array-like int[N_vertices] -> dermatome_id
    total_vertices_per_dermatome: Dict[int, int],
    id_to_name: Dict[int, str],
    dermatome_order: List[int],             # IDs ordered cranial→caudal, no UNASSIGNED(0)
    options: Optional[DermatomeOptions] = None,
) -> dict:
    """
    Compute anatomical dermatome coverage from per-vertex pain levels.

    Inputs:
      point_levels: one int per vertex (0=unpainted, 1/2/3=pain levels)
      derm_map:     array mapping vertex_id -> dermatome_id (0=UNASSIGNED)
      total_vertices_per_dermatome: {derm_id: total vertex count in dermatome}
      id_to_name:   {derm_id: name string}
      dermatome_order: list of derm IDs in cranial-to-caudal anatomical order
      options:      optional threshold configuration (uses defaults if None)

    Returns a structured dict:
      {
        "analysis_type": "anatomical_mapping_only" | "unavailable",
        "overall": { total_painted_vertices, total_painted_mass, segmental_spread,
                     top_n_displayed, overlap_flag, notes },
        "dermatomes": [ { id, name, rank, weighted_pain_burden, pain_area_share,
                          local_involvement, mean_local_intensity, painted_vertex_count,
                          total_vertices, is_close_competitor, is_overlap_candidate }, ... ]
      }

    Graceful failures:
      - derm_map is None → returns analysis_type="unavailable"
      - no painted vertices → returns empty dermatomes list
    """
    if options is None:
        options = DermatomeOptions()

    if derm_map is None:
        return {
            "analysis_type": "unavailable",
            "reason": "Dermatome map not loaded.",
            "overall": {},
            "dermatomes": [],
        }

    # --- Step 1: Aggregate per-dermatome painted counts ---
    painted_per_derm: Dict[int, int] = {}
    level_sum_per_derm: Dict[int, int] = {}

    n = min(len(point_levels), len(derm_map))
    for pid in range(n):
        lvl = int(point_levels[pid])
        if lvl <= 0:
            continue
        derm_id = int(derm_map[pid])
        if derm_id == 0:    # UNASSIGNED vertex — skip
            continue
        if derm_id not in painted_per_derm:
            painted_per_derm[derm_id] = 0
            level_sum_per_derm[derm_id] = 0
        painted_per_derm[derm_id] += 1
        level_sum_per_derm[derm_id] += lvl

    # --- Step 2: Global totals ---
    total_painted_vertices = sum(painted_per_derm.values())
    total_painted_mass = sum(level_sum_per_derm.values())

    if total_painted_vertices == 0 or total_painted_mass == 0:
        return {
            "analysis_type": "anatomical_mapping_only",
            "overall": {
                "total_painted_vertices": 0,
                "total_painted_mass": 0,
                "segmental_spread": 0,
                "top_n_displayed": 0,
                "overlap_flag": False,
                "notes": [],
            },
            "dermatomes": [],
        }

    # --- Step 3: Per-dermatome metrics ---
    derm_rows = []
    for derm_id in painted_per_derm:
        painted_count = painted_per_derm[derm_id]
        level_sum = level_sum_per_derm[derm_id]
        total_verts = total_vertices_per_dermatome.get(derm_id, 0)

        # PRIMARY ranking metric
        weighted_pain_burden = level_sum / total_painted_mass

        # SECONDARY ranking metric
        pain_area_share = painted_count / total_painted_vertices

        # Descriptive — fraction of the dermatome's own vertices that are painted
        local_involvement = painted_count / total_verts if total_verts > 0 else 0.0

        # Descriptive — average level among the painted vertices in this dermatome
        mean_local_intensity = level_sum / painted_count   # always > 0

        derm_rows.append({
            "id": derm_id,
            "name": id_to_name.get(derm_id, f"DERM_{derm_id}"),
            "weighted_pain_burden": weighted_pain_burden,
            "pain_area_share": pain_area_share,
            "local_involvement": local_involvement,
            "mean_local_intensity": mean_local_intensity,
            "painted_vertex_count": painted_count,
            "total_vertices": total_verts,
        })

    # --- Step 4: Rank (primary: burden DESC, tie-break: area_share, then local_involvement) ---
    derm_rows.sort(
        key=lambda x: (
            x["weighted_pain_burden"],
            x["pain_area_share"],
            x["local_involvement"],
        ),
        reverse=True,
    )
    for i, row in enumerate(derm_rows):
        row["rank"] = i + 1

    # --- Step 5: Close competitors (just below top-N, within threshold of rank-N burden) ---
    top_n = min(options.top_n, len(derm_rows))
    threshold_burden = derm_rows[top_n - 1]["weighted_pain_burden"] if top_n > 0 else 0.0
    for row in derm_rows:
        row["is_close_competitor"] = (
            row["rank"] > top_n
            and row["weighted_pain_burden"] >= threshold_burden - options.close_competitor_threshold
        )

    # --- Step 6: Segmental spread ---
    meaningful_ids = {
        row["id"]
        for row in derm_rows
        if (
            row["weighted_pain_burden"] >= options.meaningful_burden_threshold
            or row["pain_area_share"] >= options.meaningful_area_share_threshold
        )
    }

    segmental_spread = 0
    if len(meaningful_ids) >= 2:
        positions = [
            dermatome_order.index(did)
            for did in meaningful_ids
            if did in dermatome_order
        ]
        if len(positions) >= 2:
            segmental_spread = max(positions) - min(positions)

    # --- Step 7: Overlap flag (adjacent cranial-caudal dermatomes with close burden) ---
    overlap_flag = False
    overlap_candidates: set = set()

    burden_by_id = {row["id"]: row["weighted_pain_burden"] for row in derm_rows}

    # Collect IDs that are meaningfully painted, in cranial-caudal order
    meaningful_burden_ids = [
        did
        for did in dermatome_order
        if did in painted_per_derm
        and burden_by_id.get(did, 0) >= options.overlap_burden_threshold
    ]

    for i in range(len(meaningful_burden_ids) - 1):
        a = meaningful_burden_ids[i]
        b = meaningful_burden_ids[i + 1]
        # Only flag if they are directly adjacent in the anatomical order
        pos_a = dermatome_order.index(a)
        pos_b = dermatome_order.index(b)
        if abs(pos_b - pos_a) == 1:
            ba = burden_by_id.get(a, 0)
            bb = burden_by_id.get(b, 0)
            if ba > 0 and bb > 0:
                rel_diff = abs(ba - bb) / max(ba, bb)
                if rel_diff <= options.overlap_relative_diff:
                    overlap_flag = True
                    overlap_candidates.add(a)
                    overlap_candidates.add(b)

    for row in derm_rows:
        row["is_overlap_candidate"] = row["id"] in overlap_candidates

    # --- Step 8: Case-level notes ---
    notes = []
    if overlap_flag:
        notes.append("Overlap / uncertainty present across adjacent dermatomes.")
    if segmental_spread >= 5:
        notes.append(f"Wide segmental distribution detected ({segmental_spread} levels).")

    return {
        "analysis_type": "anatomical_mapping_only",
        "overall": {
            "total_painted_vertices": total_painted_vertices,
            "total_painted_mass": total_painted_mass,
            "segmental_spread": segmental_spread,
            "top_n_displayed": top_n,
            "overlap_flag": overlap_flag,
            "notes": notes,
        },
        "dermatomes": derm_rows,    # all painted dermatomes, sorted by rank
    }


def format_dermatome_coverage_for_display(result: dict) -> str:
    """
    Format a coverage result dict as plain text for the clinician panel.
    Returns a short "unavailable" message when data is missing.
    """
    analysis_type = result.get("analysis_type", "")

    if analysis_type == "unavailable":
        reason = result.get("reason", "Dermatome map not loaded.")
        return (
            "Dermatome Coverage Analysis\n\n"
            f"Analysis unavailable:\n  {reason}"
        )

    overall = result.get("overall", {})
    dermatomes = result.get("dermatomes", [])

    header = (
        "Dermatome Coverage Analysis (Anatomical Mapping Only)\n"
        "This analysis describes anatomical dermatome coverage only\n"
        "and is not a diagnosis.\n"
    )

    if not dermatomes:
        return header + "\nNo pain areas marked."

    lines = [header]

    if overall.get("overlap_flag"):
        lines.append("  Note: Overlap / uncertainty present across adjacent dermatomes.")
        lines.append("")

    top_n = overall.get("top_n_displayed", 5)
    lines.append("Leading Dermatomes:")
    lines.append(
        f"  {'#':<3}  {'Name':<6}  {'Pain Burden':>12}  {'Area Share':>11}  "
        f"{'Local Involvement':>18}  {'Mean Intensity':>14}"
    )
    lines.append("  " + "-" * 76)

    for row in dermatomes:
        if row["rank"] > top_n:
            continue
        flag = " *" if row.get("is_overlap_candidate") else "  "
        burden_str    = f"{row['weighted_pain_burden'] * 100:.1f}%"
        area_str      = f"{row['pain_area_share'] * 100:.1f}%"
        local_str     = f"{row['local_involvement'] * 100:.1f}%"
        intensity_str = f"{row['mean_local_intensity']:.2f}/3{flag}"
        lines.append(
            f"  {row['rank']:<3}  {row['name']:<6}  "
            f"{burden_str:>12}  "
            f"{area_str:>11}  "
            f"{local_str:>18}  "
            f"{intensity_str:>14}"
        )

    close = [r for r in dermatomes if r.get("is_close_competitor")]
    if close:
        lines.append("")
        lines.append("Additional close dermatomes:")
        for row in close:
            lines.append(
                f"  {row['name']:<6}  burden {row['weighted_pain_burden'] * 100:.1f}%  "
                f"area {row['pain_area_share'] * 100:.1f}%"
            )

    lines.append("")
    spread = overall.get("segmental_spread", 0)
    lines.append(f"Segmental spread: {spread} level{'s' if spread != 1 else ''}")
    lines.append(f"Total painted vertices: {overall.get('total_painted_vertices', 0):,}")

    notes = overall.get("notes", [])
    if notes:
        lines.append("")
        for note in notes:
            lines.append(f"  Note: {note}")

    if overall.get("overlap_flag"):
        lines.append("")
        lines.append("  * = overlap candidate")

    return "\n".join(lines)


def format_dermatome_coverage_as_html(result: dict) -> str:
    """
    Format a coverage result dict as HTML for display in the clinician panel.
    Uses a proper <table> so columns align regardless of font.
    """
    analysis_type = result.get("analysis_type", "")

    _base = (
        "font-family: inherit; font-size: 12px; color: #0A1628; text-align: center;"
    )
    _note_style = "color: #555; margin: 2px 0;"

    if analysis_type == "unavailable":
        reason = result.get("reason", "Dermatome map not loaded.")
        return (
            f'<div style="{_base}">'
            "<b>Dermatome Coverage Analysis</b><br><br>"
            f"Analysis unavailable:<br>{reason}"
            "</div>"
        )

    overall = result.get("overall", {})
    dermatomes = result.get("dermatomes", [])

    html = (
        f'<div style="{_base}">'
        "<b>Dermatome Coverage Analysis</b> "
        '<span style="color:#777; font-size:11px;">(Anatomical Mapping Only)</span><br>'
        '<p style="color:#555; font-size:11px; margin:2px 0;">'
        "This analysis describes anatomical dermatome coverage only and is not a diagnosis.</p>"
    )

    if not dermatomes:
        html += "<br>No pain areas marked.</div>"
        return html

    if overall.get("overlap_flag"):
        html += (
            f'<p style="{_note_style}">Note: Overlap / uncertainty present across adjacent dermatomes.</p>'
        )

    top_n = overall.get("top_n_displayed", 5)

    _th = (
        "background-color: rgba(0,206,209,0.15); color: #0A1628;"
        " font-weight: bold; text-align: center; padding: 3px 8px;"
        " border-bottom: 1px solid rgba(0,206,209,0.4);"
    )
    _td = "text-align: center; padding: 2px 8px;"

    html += (
        "<br><b>Leading Dermatomes:</b><br>"
        '<table style="border-collapse: collapse; width: 100%; font-size: 11px; margin: 0 auto;">'
        "<thead><tr>"
        f'<th style="{_th}">#</th>'
        f'<th style="{_th}">Name</th>'
        f'<th style="{_th}">Pain Burden</th>'
        f'<th style="{_th}">Area Share</th>'
        f'<th style="{_th}">Local Involvement</th>'
        f'<th style="{_th}">Mean Intensity</th>'
        "</tr></thead><tbody>"
    )

    for row in dermatomes:
        if row["rank"] > top_n:
            continue
        flag = " *" if row.get("is_overlap_candidate") else ""
        _row_bg = "background-color: rgba(0,206,209,0.04);" if row["rank"] % 2 == 0 else ""
        html += (
            f'<tr style="{_row_bg}">'
            f'<td style="{_td}">{row["rank"]}</td>'
            f'<td style="{_td}"><b>{row["name"]}</b>{flag}</td>'
            f'<td style="{_td}">{row["weighted_pain_burden"] * 100:.1f}%</td>'
            f'<td style="{_td}">{row["pain_area_share"] * 100:.1f}%</td>'
            f'<td style="{_td}">{row["local_involvement"] * 100:.1f}%</td>'
            f'<td style="{_td}">{row["mean_local_intensity"]:.2f}/3</td>'
            "</tr>"
        )

    html += "</tbody></table>"

    close = [r for r in dermatomes if r.get("is_close_competitor")]
    if close:
        html += "<br><b>Additional close dermatomes:</b><br>"
        for row in close:
            html += (
                f'{row["name"]} — burden {row["weighted_pain_burden"] * 100:.1f}%,'
                f' area {row["pain_area_share"] * 100:.1f}%<br>'
            )

    spread = overall.get("segmental_spread", 0)
    html += (
        f'<br><span style="color:#555;">Segmental spread: {spread} level{"s" if spread != 1 else ""}</span><br>'
        f'<span style="color:#555;">Total painted vertices: {overall.get("total_painted_vertices", 0):,}</span>'
    )

    notes = overall.get("notes", [])
    for note in notes:
        html += f'<br><span style="{_note_style}">Note: {note}</span>'

    if overall.get("overlap_flag"):
        html += '<br><span style="color:#888; font-size:10px;">* = overlap candidate</span>'

    html += "</div>"
    return html


def serialize_dermatome_coverage(result: dict) -> dict:
    """
    Return a JSON-serializable version of the coverage result, suitable for
    storing in model_data["dermatome_coverage"].
    Rounds float metrics to 4 decimal places.
    """
    if result.get("analysis_type") != "anatomical_mapping_only":
        return {"analysis_type": result.get("analysis_type", "unavailable")}

    def _r(v: float) -> float:
        try:
            return round(float(v), 4)
        except Exception:
            return v

    overall = result.get("overall", {})
    dermatomes = result.get("dermatomes", [])

    serialized = []
    for row in dermatomes:
        serialized.append({
            "id":                   row["id"],
            "name":                 row["name"],
            "rank":                 row["rank"],
            "weighted_pain_burden": _r(row["weighted_pain_burden"]),
            "pain_area_share":      _r(row["pain_area_share"]),
            "local_involvement":    _r(row["local_involvement"]),
            "mean_local_intensity": _r(row["mean_local_intensity"]),
            "painted_vertex_count": row["painted_vertex_count"],
            "total_vertices":       row["total_vertices"],
            "is_close_competitor":  bool(row.get("is_close_competitor", False)),
            "is_overlap_candidate": bool(row.get("is_overlap_candidate", False)),
        })

    return {
        "analysis_type": "anatomical_mapping_only",
        "overall": {
            "total_painted_vertices": overall.get("total_painted_vertices", 0),
            "total_painted_mass":     overall.get("total_painted_mass", 0),
            "segmental_spread":       overall.get("segmental_spread", 0),
            "top_n_displayed":        overall.get("top_n_displayed", 0),
            "overlap_flag":           bool(overall.get("overlap_flag", False)),
            "notes":                  list(overall.get("notes", [])),
        },
        "dermatomes": serialized,
    }
