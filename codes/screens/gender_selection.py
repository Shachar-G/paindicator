"""
GenderSelectionScreen: The screen for selecting the patient's gender.
"""

import os
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


class GenderSelectionScreen(BaseScreen):
    """
    UI screen for selecting a gender ('Male' or 'Female').
    This choice determines which 3D model to load.
    """

    def __init__(self, main_window, patient_data, **kwargs):
        super().__init__(main_window, patient_data, **kwargs)
        self.init_ui()
        self.subject_id = kwargs.get("subject_id", "")
        self.gender = kwargs.get("gender", "")

    def init_ui(self):
        """Sets up the widgets and layout for this screen."""
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(50), scale.sc(50), scale.sc(50), scale.sc(50))
        layout.setSpacing(scale.sc(20))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title Label
        self.title_label = QLabel(t("gender_title"), self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            title_font = QFont(self.nunito_font)
            title_font.setPointSize(scale.sc(28))
            title_font.setBold(True)
            self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")

        # --- Layout Assembly ---
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.title_label)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # --- Button Container ---
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(scale.sc(40))
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.male_button = self.create_button(t("gender_male"))
        self.female_button = self.create_button(t("gender_female"))

        self.male_button.clicked.connect(lambda: self._on_gender_selected("male"))
        self.female_button.clicked.connect(lambda: self._on_gender_selected("female"))

        button_layout.addWidget(self.male_button)
        button_layout.addWidget(self.female_button)

        layout.addWidget(button_container)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(layout)

    def on_load(self, **kwargs):
        """Re-enable buttons each time the screen is shown for a new session."""
        self.male_button.setEnabled(True)
        self.female_button.setEnabled(True)

    def _refresh_text(self):
        self.title_label.setText(t("gender_title"))
        self.male_button.setText(t("gender_male"))
        self.female_button.setText(t("gender_female"))

    # ----------------------------------------------------------------------
    # Gender selection logic
    # ----------------------------------------------------------------------
    def _on_gender_selected(self, gender: str):
        """
        Store the selected gender, compute model path, and navigate cleanly.
        """
        self.logger.info(f"Gender selected: {gender}")
        self.patient_data['gender'] = gender
        # Update SessionManager with the selected gender
        if self.session_manager:
            current_info = self.session_manager.data.get("subject_info", {})
            subject_id = current_info.get("subject_id", self.patient_data.get("patient_id", None))
            self.session_manager.set_subject_info(subject_id=subject_id, gender=gender)

        # Select model info based on gender
        if gender == "female":
            from codes.config import get_female_model_info
            model_info = get_female_model_info()
        else:
            from codes.config import get_male_model_info
            model_info = get_male_model_info()

        # Store model path and full info on main_window
        if self.main_window:
            self.main_window.selected_model_path = model_info["model_path"]
            self.main_window.selected_model_info = model_info
            self.logger.info(f"[GenderSelection] Model path set: {model_info['model_path']}")

            demo = self.session_manager and self.session_manager.demo_mode
            if demo:
                QTimer.singleShot(0, lambda: self.main_window.navigate_to("show_model"))
            else:
                QTimer.singleShot(0, lambda: self.main_window.navigate_to("questionnaire"))

    def showEvent(self, event):
        """Re-enable buttons, then lock the opposite gender if the patient already has sessions."""
        super().showEvent(event)
        self.male_button.setEnabled(True)
        self.female_button.setEnabled(True)
        self._lock_gender_if_returning_patient()

    def _lock_gender_if_returning_patient(self):
        """
        If the current patient already has saved sessions, disable the button
        for the opposite gender so they cannot switch.
        """
        if self.session_manager and self.session_manager.demo_mode:
            return  # always allow both genders in demo mode
        existing_gender = self._get_existing_patient_gender()
        if existing_gender is None:
            return  # first-time patient — both buttons stay enabled

        if existing_gender == "male":
            self.female_button.setEnabled(False)
        else:
            self.male_button.setEnabled(False)

    def _get_existing_patient_gender(self) -> str | None:
        """
        Return the gender recorded in the patient's most recent saved session,
        or None if no sessions exist yet.
        """
        try:
            subject_id = None
            if self.session_manager:
                subject_id = (self.session_manager.data.get("subject_info") or {}).get("subject_id")
            if not subject_id:
                subject_id = self.patient_data.get("patient_id")
            if not subject_id:
                return None

            patient_dir = os.path.join("data", "sessions", str(subject_id))
            if not os.path.isdir(patient_dir):
                return None

            # Find the most recent session folder
            folders = sorted(
                (f for f in os.listdir(patient_dir)
                 if os.path.isfile(os.path.join(patient_dir, f, "session.json"))),
                reverse=True,
            )
            if not folders:
                return None

            json_path = os.path.join(patient_dir, folders[0], "session.json")
            with open(json_path, "r", encoding="utf-8") as fh:
                data = __import__("json").load(fh)
            gender = (data.get("subject_info") or {}).get("gender", "").lower()
            return gender if gender in ("male", "female") else None

        except Exception as e:
            self.logger.warning(f"[GenderSelection] Could not determine existing gender: {e}")
            return None
