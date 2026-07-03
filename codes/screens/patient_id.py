"""
PatientIdScreen: The screen for entering a patient's identifier.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


class PatientIdScreen(BaseScreen):
    """
    UI screen for entering a patient ID.
    """

    def __init__(self, main_window, patient_data, **kwargs):
        super().__init__(main_window, patient_data, **kwargs)
        self.init_ui()

    def init_ui(self):
        """Sets up the widgets and layout for this screen."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(50), scale.sc(50), scale.sc(50), scale.sc(50))
        layout.setSpacing(scale.sc(20))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Instruction Label
        self.label = QLabel(t("patient_id_title"), self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            title_font = QFont(self.nunito_font)
            title_font.setPointSize(scale.sc(28))
            title_font.setBold(True)
            self.label.setFont(title_font)
        self.label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")

        # Input Field
        self.id_input = QLineEdit(self)
        self.id_input.setPlaceholderText(t("patient_id_placeholder"))
        self.id_input.setMinimumSize(scale.sc(400), scale.sc(60))
        self.id_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            input_font = QFont(self.nunito_font)
            input_font.setPointSize(scale.sc(18))
            self.id_input.setFont(input_font)

        font_family = "Nunito" if self.nunito_font else "Arial"
        self.id_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.9);
                border: 2px solid {theme.PRIMARY};
                border-radius: 12px;
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}';
                font-size: {scale.sc(20)}px;
                padding: 10px;
            }}
            QLineEdit:focus {{
                border: 2px solid {theme.PRIMARY_DARK};
            }}
        """)

        # Connect the return key (Enter) to the submission method
        self.id_input.returnPressed.connect(self._on_submit)

        # Continue Button
        self.continue_button = self.create_button(t("continue_btn"))
        self.continue_button.clicked.connect(self._on_submit)

        # --- Layout Assembly ---
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.label)
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addWidget(self.id_input, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addWidget(self.continue_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(layout)

    def resizeEvent(self, event):
        """Cap the input width at 90% of the screen so narrow/portrait displays don't clip it."""
        super().resizeEvent(event)
        if hasattr(self, "id_input"):
            new_w = min(scale.sc(400), max(scale.sc(240), int(self.width() * 0.9)))
            self.id_input.setMinimumWidth(new_w)

    def _refresh_text(self):
        self.label.setText(t("patient_id_title"))
        self.id_input.setPlaceholderText(t("patient_id_placeholder"))
        self.continue_button.setText(t("continue_btn"))

    def _on_submit(self):
        """
        Validate patient ID and route either patient or clinician flow.
        Also resets SessionManager when clinician starts a new session,
        and resets ShowModel if it exists.
        """
        patient_id = self.id_input.text().strip()
        if not patient_id:
            self.logger.warning("[PatientIDScreen] No patient ID entered.")
            return

        # Store patient ID for next screens
        self.patient_data["patient_id"] = patient_id

        # Update SessionManager with patient ID
        if self.session_manager:
            self.session_manager.set_subject_info(subject_id=patient_id)

        role = self.patient_data.get("role")
        if role == "clinician":
            # Clinician should not start a new patient session here.
            self.main_window.navigate_to("clinician_patients")
            return
        # --- PATIENT FLOW ---
        if role == "patient":
            clinician_name = self.patient_data.get("clinician_name", "")
            if self.session_manager:
                self.session_manager.start_new_session(
                    subject_id=patient_id,
                    clinician_name=clinician_name,
                )
            try:
                show_model = self.main_window.screens.get("show_model")
                if show_model is not None:
                    show_model.reset_for_new_session()
            except Exception as e:
                self.logger.error(f"[PatientIDScreen] Failed to reset ShowModelScreen: {e}")
            self.main_window.navigate_to("gender_selection")
            return

        # --- CLINICIAN FLOW (NEW SESSION) ---
        if self.session_manager:
            clinician_name = self.patient_data.get("clinician_name", "")

            # Start a completely fresh session
            self.session_manager.start_new_session(
                subject_id=patient_id,
                clinician_name=clinician_name,
            )

        # Reset ShowModelScreen state if it already exists
        try:
            show_model = self.main_window.screens.get("show_model")
            if show_model is not None:
                show_model.reset_for_new_session()
        except Exception as e:
            self.logger.error(f"[PatientIDScreen] Failed to reset ShowModelScreen: {e}")

        # Move to gender selection screen
        self.main_window.navigate_to("gender_selection")

    def on_load(self, **kwargs):
        """Clear the ID field every time this screen is navigated to."""
        self.reset_screen()

    def reset_screen(self):
        """Clear the ID field and internal patient_data when starting a new session."""
        self.id_input.clear()
        self.patient_data["patient_id"] = None
