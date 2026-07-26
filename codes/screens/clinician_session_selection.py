# codes/screens/clinician_session_selection.py
# NOTE: All comments are in English only.

import os
import json
import shutil
from datetime import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QPushButton,
    QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt

from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


class ClinicianSessionSelectionScreen(BaseScreen):
    """
    Clinician selects a session for a chosen patient_id.
    Loads session.json into SessionManager and opens clinician_view_session.
    """

    def __init__(self, main_window, patient_data, session_manager=None, **kwargs):
        super().__init__(main_window, patient_data, session_manager=session_manager, **kwargs)
        self.sessions = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(40), scale.sc(20), scale.sc(40), scale.sc(40))
        layout.setSpacing(scale.sc(18))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._title_label = QLabel(t("clinician_session_title"), self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            f = self.nunito_font
            f.setPointSize(scale.sc(28))
            f.setBold(True)
            self._title_label.setFont(f)
        self._title_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(self._title_label)

        self.info_label = QLabel("", self)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(f"color: {theme.TEXT_SECOND};")
        layout.addWidget(self.info_label)

        outer_card = QWidget(self)
        outer_card.setStyleSheet("background-color: #FFFFFF; border-radius: 18px;")
        outer_layout = QVBoxLayout(outer_card)
        outer_layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background-color: transparent; }
            QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
            QScrollBar::handle:vertical { background: rgba(0,206,209,0.5); min-height: 30px; border-radius: 3px; }
            QScrollBar::handle:vertical:hover { background: #00CED1; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(16)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.list_container)
        outer_layout.addWidget(scroll)
        layout.addWidget(outer_card, stretch=1)

        self._back_btn = self.create_button(t("clinician_back_to_patients"), min_width=280, min_height=55)
        back_btn = self._back_btn
        back_btn.clicked.connect(lambda: self.main_window.navigate_back())
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def _refresh_text(self):
        self._title_label.setText(t("clinician_session_title"))
        self._back_btn.setText(t("clinician_back_to_patients"))
        self._refresh_sessions()

    def enter_screen(self):
        self._refresh_sessions()

    def _refresh_sessions(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.session_manager:
            self.info_label.setText("No SessionManager available.")
            return

        patient_id = self.patient_data.get("patient_id")
        if not patient_id:
            self.info_label.setText("Missing patient ID (go back and select a patient).")
            return

        all_sessions = self.session_manager.list_all_sessions()
        patient_sessions = next((p for p in all_sessions if str(p.get("patient_id")) == str(patient_id)), None)

        if not patient_sessions or not patient_sessions.get("sessions"):
            self.info_label.setText(f"No previous sessions for patient {patient_id}.")
            return

        sessions = []
        for s in patient_sessions["sessions"]:
            meta = self._read_session_metadata(s.get("json"), s.get("folder"))
            sessions.append({"folder": s.get("folder"), "json": s.get("json"), "meta": meta})

        sessions.sort(key=lambda e: e["meta"]["datetime_obj"] or datetime.min, reverse=True)
        self.sessions = sessions

        total = len(self.sessions)
        for i, entry in enumerate(self.sessions):
            entry["meta"]["session_number"] = total - i

        self.info_label.setText(f"Patient ID: {patient_id}  •  {len(self.sessions)} saved sessions")

        for entry in self.sessions:
            self._add_session_card(entry)

        self.list_layout.addStretch(1)

    def _read_session_metadata(self, json_path, folder_name):
        meta = {
            "folder": folder_name or "",
            "timestamp_str": "",
            "date_str": "",
            "time_str": "",
            "clinician_name": "",
            "datetime_obj": None,
        }
        if not json_path or not os.path.exists(json_path):
            return meta

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return meta

        ts = data.get("timestamp")
        dt = None
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts)
            except Exception:
                dt = None

        meta["timestamp_str"] = ts or ""
        meta["datetime_obj"] = dt
        if dt:
            meta["date_str"] = dt.strftime("%d/%m/%Y")
            meta["time_str"] = dt.strftime("%H:%M")

        subject_info = data.get("subject_info") or {}
        meta["clinician_name"] = subject_info.get("clinician_name", "")
        return meta

    def _add_session_card(self, entry):
        meta = entry["meta"]
        num = meta.get("session_number", "?")

        title_line = f"{t('clinician_session_label')}{num}"
        datetime_line = ""
        if meta.get("date_str") and meta.get("time_str"):
            datetime_line = f"{meta['date_str']} • {meta['time_str']}"

        clinician_line = f"{t('clinician_clinician_label')}: {meta.get('clinician_name','')}" if meta.get("clinician_name") else ""

        lines = [title_line]
        if datetime_line:
            lines.append(datetime_line)
        if clinician_line:
            lines.append(clinician_line)

        # Row: main session button + Edit button side by side
        row_widget = QWidget(self)
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        session_btn = QPushButton(self)
        session_btn.setMinimumHeight(scale.sc(90))
        session_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        session_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #D0D0D0;
                text-align: left;
                padding: {scale.sc(12)}px {scale.sc(18)}px;
                font-size: {scale.sc(17)}px;
                line-height: 160%;
            }}
            QPushButton:hover {{ background-color: rgba(0,206,209,0.08); border: 1px solid #00CED1; }}
            QPushButton:pressed {{ background-color: #E0F0F4; }}
        """)
        session_btn.setText("\n".join(lines))

        edit_btn = QPushButton(t("clinician_session_edit"), self)
        edit_btn.setFixedSize(scale.sc(80), scale.sc(90))
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #00CED1;
                color: #00CED1;
                font-size: {scale.sc(15)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(0,206,209,0.12); }}
            QPushButton:pressed {{ background-color: rgba(0,206,209,0.25); }}
        """)

        del_btn = QPushButton(t("delete_btn"), self)
        del_btn.setFixedSize(scale.sc(80), scale.sc(90))
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 1px solid #E53935;
                color: #E53935;
                font-size: {scale.sc(14)}px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: rgba(229,57,53,0.08); }}
            QPushButton:pressed {{ background-color: rgba(229,57,53,0.18); }}
        """)

        json_path = entry.get("json")
        folder = meta.get("folder", "")
        session_num = meta.get("session_number", "?")
        date_str = meta.get("date_str", "")
        session_btn.clicked.connect(lambda _, p=json_path: self._on_session_selected(p))
        edit_btn.clicked.connect(lambda _, p=json_path, f=folder: self._on_edit_session(p, f))
        del_btn.clicked.connect(
            lambda _, p=json_path, n=session_num, d=date_str:
                self._confirm_delete_session(p, n, d)
        )

        row_layout.addWidget(session_btn, stretch=1)
        row_layout.addWidget(edit_btn)
        row_layout.addWidget(del_btn)
        self.list_layout.addWidget(row_widget)

    def _confirm_delete_session(self, json_path: str, session_num, date_str: str):
        label = f"#{session_num}" + (f"  ({date_str})" if date_str else "")
        reply = QMessageBox.question(
            self,
            t("delete_session_title"),
            t("delete_session_confirm").format(label=label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        session_folder = os.path.dirname(json_path) if json_path else ""
        try:
            if session_folder and os.path.isdir(session_folder):
                shutil.rmtree(session_folder)
        except Exception as e:
            QMessageBox.critical(self, t("delete_error_title"), f"{t('delete_error_msg')}\n{e}")
            return

        # If the patient folder is now empty, remove it too
        patient_folder = os.path.dirname(session_folder) if session_folder else ""
        if patient_folder and os.path.isdir(patient_folder):
            try:
                remaining = [
                    d for d in os.listdir(patient_folder)
                    if os.path.isdir(os.path.join(patient_folder, d))
                ]
                if not remaining:
                    shutil.rmtree(patient_folder)
                    # Navigate back since this patient no longer exists
                    self.main_window.navigate_back()
                    return
            except Exception:
                pass

        self._refresh_sessions()

    def _on_session_selected(self, json_path: str):
        if not json_path or not os.path.exists(json_path):
            self.logger.warning(f"[ClinicianSessionSelection] JSON not found: {json_path}")
            return

        try:
            self.session_manager.data = {}
            self.session_manager.load_from_file(json_path)
        except Exception as e:
            self.logger.error(f"[ClinicianSessionSelection] Failed to load: {e}")
            self._show_load_error(e)
            return

        self.main_window.navigate_to("clinician_view_session")

    def _show_load_error(self, err: Exception):
        """Inform the clinician that a session file could not be loaded."""
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self, "Session Load Failed",
                "This session could not be opened (the file may be corrupted).\n"
                f"Details: {err}"
            )
        except Exception:
            pass

    def _on_edit_session(self, json_path: str, folder_name: str):
        """Open an existing session in the show_model screen for editing."""
        if not json_path or not os.path.exists(json_path):
            self.logger.warning(f"[ClinicianSessionSelection] Edit: JSON not found: {json_path}")
            return

        try:
            self.session_manager.data = {}
            self.session_manager.load_from_file(json_path)
            # Restore the session folder so that saving overwrites the same session
            self.session_manager.current_session_folder = folder_name
        except Exception as e:
            self.logger.error(f"[ClinicianSessionSelection] Edit: Failed to load: {e}")
            self._show_load_error(e)
            return

        # Determine model path from loaded session gender
        subject_info = self.session_manager.data.get("subject_info") or {}
        gender = (subject_info.get("gender") or "female").lower()
        try:
            if gender == "female":
                from codes.config import get_female_model_info
                model_info = get_female_model_info()
            else:
                from codes.config import get_male_model_info
                model_info = get_male_model_info()
            self.main_window.selected_model_path = model_info["model_path"]
            self.main_window.selected_model_info = model_info
        except Exception as e:
            self.logger.error(f"[ClinicianSessionSelection] Edit: model info failed: {e}")
            return

        # Reset ShowModelScreen state so it re-initializes cleanly, then navigate
        try:
            show_model = self.main_window.screens.get("show_model")
            if show_model is not None:
                show_model.reset_for_new_session()
        except Exception:
            pass

        self.main_window.navigate_to("show_model", _edit_mode=True)