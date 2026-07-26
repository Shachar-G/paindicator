# codes/screens/clinician_patients.py
# NOTE: All comments are in English only.

import os
import shutil

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea, QWidget,
    QPushButton, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt
from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


class ClinicianPatientsScreen(BaseScreen):
    """
    Clinician dashboard:
      - Lists all patient folders under data/sessions/{patient_id}
      - Search by patient ID (local filter)
      - Click patient -> go to clinician_session_selection
    """

    def __init__(self, main_window, patient_data, session_manager=None, **kwargs):
        super().__init__(main_window, patient_data, session_manager=session_manager, **kwargs)
        self._all_patients = []  # list of dicts from SessionManager.list_all_sessions()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(40), scale.sc(20), scale.sc(40), scale.sc(40))
        layout.setSpacing(scale.sc(16))
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._title_label = QLabel(t("clinician_patients_title"), self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            f = self.nunito_font
            f.setPointSize(scale.sc(28))
            f.setBold(True)
            self._title_label.setFont(f)
        self._title_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        layout.addWidget(self._title_label)

        self._subtitle_label = QLabel(t("clinician_patients_subtitle"), self)
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle_label.setStyleSheet(f"color: {theme.TEXT_SECOND};")
        layout.addWidget(self._subtitle_label)

        self.search = QLineEdit(self)
        self.search.setPlaceholderText(t("clinician_search_placeholder"))
        self.search.textChanged.connect(self._refresh_list)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                background: white;
                border: 1px solid #D0D0D0;
                border-radius: 10px;
                padding: {scale.sc(10)}px {scale.sc(12)}px;
                font-size: {scale.sc(16)}px;
            }}
        """)
        layout.addWidget(self.search)

        # Scroll area
        outer_card = QWidget(self)
        outer_card.setStyleSheet("background-color: #FFFFFF; border-radius: 18px;")
        outer_layout = QVBoxLayout(outer_card)
        outer_layout.setContentsMargins(16, 16, 16, 16)

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
        self.list_layout.setSpacing(12)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.list_container)
        outer_layout.addWidget(scroll)
        layout.addWidget(outer_card, stretch=1)

        # Back button (optional)
        self._back_btn = self.create_button(t("clinician_back_btn"), min_width=220, min_height=55)
        self._back_btn.clicked.connect(lambda: self.main_window.navigate_back())
        layout.addWidget(self._back_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def _refresh_text(self):
        self._title_label.setText(t("clinician_patients_title"))
        self._subtitle_label.setText(t("clinician_patients_subtitle"))
        self.search.setPlaceholderText(t("clinician_search_placeholder"))
        self._back_btn.setText(t("clinician_back_btn"))
        self._refresh_list()

    def enter_screen(self):
        self._load_patients()
        self._refresh_list()

    def _load_patients(self):
        if not self.session_manager:
            self._all_patients = []
            return
        self._all_patients = self.session_manager.list_all_sessions()

    def _refresh_list(self):
        # clear
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = (self.search.text() or "").strip()

        patients = self._all_patients
        if query:
            patients = [p for p in patients if query in str(p.get("patient_id", ""))]

        if not patients:
            lbl = QLabel(t("clinician_no_patients"), self.list_container)
            lbl.setStyleSheet(f"color: {theme.TEXT_SECOND};")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.list_layout.addWidget(lbl)
            return

        for p in patients:
            pid = str(p.get("patient_id", ""))
            count = len(p.get("sessions") or [])
            patient_path = p.get("path", "")

            row_widget = QWidget(self.list_container)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            btn = QPushButton(f"{pid}   •   {count} {t('sessions_word')}", row_widget)
            btn.setMinimumHeight(scale.sc(60))
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #D0D0D0;
                    text-align: left;
                    padding: {scale.sc(12)}px {scale.sc(18)}px;
                    font-size: {scale.sc(16)}px;
                }}
                QPushButton:hover {{ background-color: rgba(0,206,209,0.08); border: 1px solid #00CED1; }}
                QPushButton:pressed {{ background-color: #E0F0F4; }}
            """)
            btn.clicked.connect(lambda _, patient_id=pid: self._select_patient(patient_id))

            del_btn = QPushButton(t("delete_btn"), row_widget)
            del_btn.setFixedSize(scale.sc(80), scale.sc(60))
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
            del_btn.clicked.connect(
                lambda _, patient_id=pid, path=patient_path, n=count:
                    self._confirm_delete_patient(patient_id, path, n)
            )

            row_layout.addWidget(btn, stretch=1)
            row_layout.addWidget(del_btn)
            self.list_layout.addWidget(row_widget)

        self.list_layout.addStretch(1)

    def _select_patient(self, patient_id: str):
        # Store selected patient id in shared state
        self.patient_data["patient_id"] = patient_id
        # Navigate to clinician session list
        self.main_window.navigate_to("clinician_session_selection")

    def _confirm_delete_patient(self, patient_id: str, patient_path: str, session_count: int):
        sessions_label = f"{session_count} session{'s' if session_count != 1 else ''}"
        reply = QMessageBox.question(
            self,
            t("delete_patient_title"),
            t("delete_patient_confirm").format(patient_id=patient_id, sessions_label=sessions_label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if patient_path and os.path.isdir(patient_path):
                shutil.rmtree(patient_path)
        except Exception as e:
            QMessageBox.critical(self, t("delete_error_title"), f"{t('delete_error_msg')}\n{e}")
            return

        self._load_patients()
        self._refresh_list()