# codes/session_manager.py
import json
import os
from datetime import datetime


# ---------------------------------------------------------------------------
# Questionnaire structure — maps questionnaire save-keys → translation keys
# Matches the section/field order of questionnaire.py
# ---------------------------------------------------------------------------
_Q_SECTIONS = [
    ("q_section_patient_info", [
        ("age", "q_patient_age"),
    ]),
    ("q_section_pain_intensity", [
        ("pain anamnesis",  "q_pain_during_anamnesis"),
        ("pain average",    "q_pain_average"),
        ("pain peak",       "q_pain_acute"),
    ]),
    ("q_section_pain_frequency", [
        ("frequency",          None),             # list → use section name as label
        ("frequency comment",  "q_freq_comment"),
    ]),
    ("q_section_pain_characteristics", [
        ("radiation",              "q_char_radiation"),
        ("pain begin",             "q_char_when_began"),
        ("pain variation",         "q_char_varies_day"),
        ("pain character",         "q_char_character_section"),
        ("pain character comment", "q_char_comment"),
    ]),
    ("q_section_factors", [
        ("alleviating factors", "q_factor_alleviating"),
        ("aggravating factors", "q_factor_aggravating"),
        ("associated symptoms", "q_factor_associated"),
    ]),
    ("q_section_impact", [
        ("life impact",  None),             # list → use section name as label
        ("life comment", "q_impact_comments"),
    ]),
    ("q_section_exam_date", [
        ("examination date", None),         # use section name as label
    ]),
]


def format_questionnaire_for_display(questionnaire: dict, lang: str) -> str:
    """
    Format questionnaire data as a structured, section-grouped string that
    mirrors the visual layout of the questionnaire screen.
    Returns an empty string if questionnaire is empty.
    """
    if not questionnaire:
        return ""

    from codes.translations import STRINGS

    def _lbl(key, default=""):
        if not key:
            return default
        entry = STRINGS.get(key, {})
        v = entry.get(lang, "") or entry.get("en", "")
        return v if v else default

    lines = []
    for section_key, fields in _Q_SECTIONS:
        section_title = _lbl(section_key, section_key)
        section_lines = []
        for q_key, trans_key in fields:
            if q_key not in questionnaire:
                continue
            value = questionnaire[q_key]
            field_label = _lbl(trans_key, q_key) if trans_key else section_title
            if isinstance(value, list):
                if value:
                    section_lines.append(f"  {field_label}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, (int, float)):
                section_lines.append(f"  {field_label}: {value}")
            elif value and str(value).strip():
                section_lines.append(f"  {field_label}: {value}")

        if section_lines:
            lines.append(f"  {section_title}")
            lines.extend(section_lines)
            lines.append("")

    return "\n".join(lines).rstrip()


class SessionManager:
    """
    Centralized session manager for PAINDICATOR.
    Stores subject info (including clinician), questionnaire answers, model data, and screenshots.
    Organizes files as:
      data/sessions/{patient_id}/session_{DD-MM-YYYY_HH-MM-SS}/
        - session.json
        - front.png
        - back.png
    """

    def __init__(self):
        self.data = {
            "subject_info": {},   # {"subject_id": str, "gender": str|None, "clinician_name": str|None}
            "questionnaire": {},  # dict of future questionnaire answers
            "model_data": {},     # {"mode": "...", "camera": {...}, "marks": [...], "paint_v2": {...}, "comments": [...]}
            "screenshots": {},    # {"front": "front.png", "back": "back.png"} (filenames within the session folder)
            "timestamp": None
        }
        self.current_session_folder = None
        self.demo_mode = False

    # --------------------------- Session lifecycle --------------------------- #
    def start_new_session(
            self,
            subject_id: str,
            gender: str | None = None,
            clinician_name: str | None = None,
    ) -> None:
        """
        Reset all session data and start a clean session for the given subject.

        This should be called when:
          - A clinician starts a brand new session for a patient.
          - A patient chooses 'Start New Session'.
        """
        # Reset all stored data
        self.data = {
            "subject_info": {},
            "questionnaire": {},
            "model_data": {},
            "screenshots": {},
            "timestamp": None,
        }

        # Ensure the next save creates a brand new folder
        self.current_session_folder = None

        # Store basic subject info using the regular setter
        self.set_subject_info(
            subject_id=subject_id,
            gender=gender,
            clinician_name=clinician_name,
        )

    def close_session(self) -> None:
        """
        Mark the current session as closed.

        This does not delete data, it only clears the folder pointer so that the
        next save will start a completely new session folder.
        """
        self.current_session_folder = None

    # --------------------------- Setters --------------------------- #
    def set_subject_info(self, subject_id: str, gender: str | None = None, clinician_name: str | None = None):
        """Update subject info incrementally (ID first, then clinician, then gender)."""
        info = dict(self.data.get("subject_info") or {})
        if subject_id is not None:
            info["subject_id"] = str(subject_id)
        if gender is not None:
            info["gender"] = gender
        if clinician_name is not None:
            info["clinician_name"] = clinician_name
        self.data["subject_info"] = info

    def set_questionnaire(self, answers: dict):
        """Replace questionnaire answers (to be called by the questionnaire screen later)."""
        self.data["questionnaire"] = dict(answers or {})

    def set_model_data(self, model_dict: dict):
        """Replace model-related data snapshot (called by renderer before saving)."""
        self.data["model_data"] = dict(model_dict or {})

    def set_screenshots(self, front_filename: str, back_filename: str):
        """
        Store screenshot filenames (relative to the session folder).
        Do NOT store absolute paths to keep the session folder portable.
        """
        self.data["screenshots"] = {
            "front": front_filename,
            "back": back_filename
        }

    # --------------------------- Folder logic --------------------------- #
    def get_session_folder(self, base_dir: str = "data/sessions") -> str:
        """
        Return the folder for the *current* session.
        - On the first save of a new session, create a new folder name and remember it
          in self.current_session_folder.
        - On subsequent saves in the same session, reuse the same folder.
        Folder structure:
          data/sessions/{patient_id}/session_{DD-MM-YYYY_HH-MM-SS}/
        """
        subject_info = self.data.get("subject_info") or {}
        subject_id = subject_info.get("subject_id") or "unknown"

        # Base folder for this patient
        patient_dir = os.path.join(base_dir, str(subject_id))
        os.makedirs(patient_dir, exist_ok=True)

        # If this is the first save in this session, generate a new folder name
        if not self.current_session_folder:
            now = datetime.now()
            self.current_session_folder = now.strftime("session_%d-%m-%Y_%H-%M-%S")

        # Reuse the same folder name for all subsequent saves in this session
        session_folder = os.path.join(patient_dir, self.current_session_folder)
        os.makedirs(session_folder, exist_ok=True)
        return session_folder

    # --------------------------- JSON save/load --------------------------- #
    def export_dict(self) -> dict:
        """Return a complete dict snapshot (with ISO timestamp) for JSON writing."""
        snapshot = dict(self.data)
        snapshot["timestamp"] = datetime.now().isoformat()
        return snapshot

    def save_to_file(self, session_folder: str) -> str:
        """
        Write session.json into the given folder (folder must exist).
        Returns the full path to the saved JSON.
        """
        os.makedirs(session_folder, exist_ok=True)
        json_path = os.path.join(session_folder, "session.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.export_dict(), f, indent=2)
        print(f"[SessionManager] Saved session → {json_path}")
        return json_path

    def load_from_file(self, json_path: str) -> dict:
        """
        Load an existing session.json.
        - Stores its content into self.data
        - Updates current_session_folder so that subsequent saves
          will overwrite/update the same session folder.
        Returns the loaded dict.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"Session file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        # Derive the session folder name from the JSON path
        # Example: data/sessions/123456789/session_29-10-2025_14-48-09/session.json
        session_dir = os.path.dirname(json_path)  # .../session_29-10-2025_14-48-09
        folder_name = os.path.basename(session_dir)  # session_29-10-2025_14-48-09
        self.current_session_folder = folder_name

        print(f"[SessionManager] Loaded session ← {json_path}")
        return self.data

    def get_marks(self) -> dict:
        """
        Return the marks dict from model_data in a safe, normalized form.
        Expected format: {cell_id: level}, where level > 0 means painted.
        """
        model_data = self.data.get("model_data") or {}
        marks = model_data.get("marks") or {}

        # If already dict, return directly
        if isinstance(marks, dict):
            return marks

        # Robust fallback (convert list or str formats if needed)
        normalized = {}
        try:
            for k, v in dict(marks).items():
                try:
                    cid = int(k)
                    lvl = int(v)
                    normalized[cid] = lvl
                except Exception:
                    continue
        except Exception:
            pass
        return normalized

    def get_paint_v2(self) -> dict:
        """
        Return paint_v2 dict from model_data in a safe form.

        Expected format:
          {
            "point_level": [int ...] length N_points,
            "point_intensity": [float ...] length N_points
          }
        """
        model_data = self.data.get("model_data") or {}
        paint_v2 = model_data.get("paint_v2") or {}
        if isinstance(paint_v2, dict):
            return paint_v2
        return {}

    def _count_painted_triangles(self) -> int:
        """
        Count how many cells (triangles) are painted with level > 0.
        Used for the human-readable session summary (legacy marks-based).
        """
        marks = self.get_marks()
        count = 0
        for _, level in marks.items():
            try:
                if int(level) > 0:
                    count += 1
            except Exception:
                continue
        return count

    def _count_painted_points(self) -> int:
        """
        Count how many points are painted (opacity > 0) based on paint_v2.
        Used for the human-readable session summary (soft-brush / per-point).
        """
        paint_v2 = self.get_paint_v2()
        intensities = paint_v2.get("point_intensity") or []
        count = 0
        for v in intensities:
            try:
                if float(v) > 0.0:
                    count += 1
            except Exception:
                continue
        return count

    def _build_summary_lines(self, lang: str) -> list:
        """
        Build summary lines for a given language code ("en" or "he").
        Questionnaire keys are translated using the STRINGS table when available.
        Dermatome analysis content is always written in English (analysis not yet translated).
        """
        from codes.translations import STRINGS

        def _lbl(key, default):
            entry = STRINGS.get(key, {})
            v = entry.get(lang, "")
            return v if v else entry.get("en", default)

        subject_info = self.data.get("subject_info") or {}
        questionnaire = self.data.get("questionnaire") or {}
        model_data = self.data.get("model_data") or {}
        comments = model_data.get("comments") or []
        if isinstance(comments, str):
            comments = [comments]

        lines = []
        lines.append(f"{_lbl('summary_patient_id', 'Patient ID')}: {subject_info.get('subject_id', 'N/A')}")
        raw_gender = (subject_info.get('gender') or '').lower()
        gender_key = "gender_male" if raw_gender == "male" else "gender_female" if raw_gender == "female" else None
        gender_display = _lbl(gender_key, raw_gender) if gender_key else (raw_gender or "N/A")
        lines.append(f"{_lbl('summary_gender', 'Gender')}: {gender_display}")
        lines.append(f"{_lbl('summary_clinician_name', 'Clinician Name')}: {subject_info.get('clinician_name', 'N/A')}")
        lines.append("")

        lines.append(f"{_lbl('summary_questionnaire', 'Questionnaire')}:")
        q_formatted = format_questionnaire_for_display(questionnaire, lang)
        if q_formatted:
            lines.extend(q_formatted.split("\n"))
        else:
            lines.append(f"  {_lbl('summary_no_questionnaire', '(No questionnaire data)')}")
        lines.append("")

        lines.append(f"{_lbl('summary_comments', 'Comments')}:")
        if comments:
            for c in comments:
                lines.append(f"  - {c}")
        else:
            lines.append(f"  {_lbl('summary_no_comments', '(No comments)')}")
        lines.append("")

        lines.append("----------------------------")
        if self.get_paint_v2():
            painted_count = self._count_painted_points()
            painted_label = _lbl("summary_painted_points", "Painted Points")
        else:
            painted_count = self._count_painted_triangles()
            painted_label = _lbl("summary_painted_triangles", "Painted Triangles")
        lines.append(f"{painted_label}: {painted_count}")

        # Dermatome coverage — always in English regardless of lang (not yet translated).
        # Reads new "dermatome_coverage" key first; falls back to legacy "dermatome_analysis"
        # so that old saved sessions continue to render correctly.
        derm_coverage = model_data.get("dermatome_coverage")
        if derm_coverage and derm_coverage.get("analysis_type") == "anatomical_mapping_only":
            lines.append("")
            lines.append("Dermatome Coverage Analysis (Anatomical Mapping Only):")
            overall = derm_coverage.get("overall", {})
            spread = overall.get("segmental_spread", 0)
            lines.append(f"  Segmental spread: {spread} level{'s' if spread != 1 else ''}")
            if overall.get("overlap_flag"):
                lines.append("  Note: Overlap / uncertainty present across adjacent dermatomes.")
            top_n = overall.get("top_n_displayed", 5)
            for entry in derm_coverage.get("dermatomes", []):
                if entry.get("rank", 99) > top_n:
                    continue
                lines.append(
                    f"  {entry.get('name', '?'):<6}  "
                    f"burden {entry.get('weighted_pain_burden', 0) * 100:.1f}%  "
                    f"area {entry.get('pain_area_share', 0) * 100:.1f}%  "
                    f"local {entry.get('local_involvement', 0) * 100:.1f}%  "
                    f"intensity {entry.get('mean_local_intensity', 0):.2f}/3"
                )
        elif model_data.get("dermatome_analysis"):
            # Legacy format from sessions saved before the new engine was introduced
            lines.append("")
            lines.append("Dermatome Analysis (legacy):")
            for entry in model_data["dermatome_analysis"]:
                name       = entry.get("name", "?")
                coverage   = entry.get("coverage_pct", 0)
                intensity  = entry.get("avg_pain", 0)
                index      = entry.get("pain_index_pct", 0)
                body_share = entry.get("body_share_pct", 0)
                severity   = entry.get("severity", "N/A")
                lines.append(
                    f"  {name:<6}  coverage {coverage:.1f}%  "
                    f"intensity {intensity:.2f}/3  "
                    f"index {index:.1f}%  "
                    f"body_share {body_share:.1f}%  [{severity}]"
                )

        return lines

    def save_to_human_readable_file(self, session_folder: str) -> str:
        """
        Create a bilingual (English + Hebrew) human-readable summary of the session.
        Format:
          [English]
          ...

          ========================================

          [עברית]
          ...
        """
        os.makedirs(session_folder, exist_ok=True)
        summary_path = os.path.join(session_folder, "session_summary.txt")

        _SEP = "=" * 40
        en_lines = self._build_summary_lines("en")
        he_lines = self._build_summary_lines("he")

        content = (
            "[English]\n"
            + "\n".join(en_lines)
            + "\n\n" + _SEP + "\n\n"
            + "[עברית]\n"
            + "\n".join(he_lines)
        )

        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[SessionManager] Saved human-readable summary → {summary_path}")
        return summary_path

    def append_analysis_to_summary(self, session_folder: str, analysis_text: str) -> bool:
        """
        Append an analysis report to session_summary.txt in both language sections.
        The analysis content itself stays in English; a note is added in the Hebrew section.
        Returns True on success.
        """
        summary_path = os.path.join(session_folder, "session_summary.txt")
        if not os.path.exists(summary_path):
            return False

        _SEP = "=" * 40
        try:
            from codes.translations import STRINGS
            _he_label = (STRINGS.get("summary_analysis_report", {}).get("he", None)
                         or "דוח ניתוח")
            _he_note = (STRINGS.get("summary_analysis_english_only", {}).get("he", None)
                        or "(ניתוח זמין באנגלית בלבד)")

            with open(summary_path, "r", encoding="utf-8") as f:
                content = f.read()

            if _SEP in content:
                idx = content.index(_SEP)
                en_part = content[:idx].rstrip()
                he_part = content[idx + len(_SEP):].lstrip()
            else:
                en_part = content.rstrip()
                he_part = ""

            en_part += f"\n\n--- Analysis Report ---\n{analysis_text}"

            if he_part:
                he_part = he_part.rstrip()
                he_part += f"\n\n--- {_he_label} ---\n{_he_note}"
                new_content = en_part + "\n\n" + _SEP + "\n\n" + he_part
            else:
                new_content = en_part

            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            print(f"[SessionManager] Appended analysis → {summary_path}")
            return True
        except Exception as e:
            print(f"[SessionManager] append_analysis_to_summary failed: {e}")
            return False

    # --------------------------- Listing (for future Session Browser) --------------------------- #
    def list_all_sessions(self, base_dir: str = "data/sessions") -> list[dict]:
        """
        Return a structured list of all saved sessions:
        [
          {
            "patient_id": "123456789",
            "path": "data/sessions/123456789",
            "sessions": [
               {"folder": "session_29-10-2025_14-48-09", "json": ".../session.json"},
               ...
            ]
          },
          ...
        ]
        """
        results: list[dict] = []
        if not os.path.isdir(base_dir):
            return results

        for patient_id in sorted(os.listdir(base_dir)):
            patient_path = os.path.join(base_dir, patient_id)
            if not os.path.isdir(patient_path):
                continue
            items = []
            for folder in sorted(os.listdir(patient_path)):
                session_path = os.path.join(patient_path, folder)
                if not os.path.isdir(session_path):
                    continue
                json_path = os.path.join(session_path, "session.json")
                items.append({"folder": folder, "json": json_path})
            results.append({
                "patient_id": patient_id,
                "path": patient_path,
                "sessions": items
            })
        return results