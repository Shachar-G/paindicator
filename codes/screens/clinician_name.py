"""
ClinicianNameScreen: The screen for entering the clinician's name.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


class ClinicianNameScreen(BaseScreen):
    """
    UI screen for entering the clinician's name.
    """

    def __init__(self, main_window=None, patient_data=None, session_manager=None, **kwargs):
        super().__init__(main_window, patient_data, session_manager=session_manager, **kwargs)
        self.init_ui()

    def init_ui(self):
        """Sets up the widgets and layout for this screen."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(50), scale.sc(50), scale.sc(50), scale.sc(50))
        layout.setSpacing(scale.sc(20))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Instruction Label
        self.label = QLabel(t("clinician_name_title"), self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            title_font = QFont(self.nunito_font)
            title_font.setPointSize(scale.sc(28))
            title_font.setBold(True)
            self.label.setFont(title_font)
        self.label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")

        # Input Field
        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText(t("clinician_name_placeholder"))
        self.name_input.setMinimumSize(scale.sc(400), scale.sc(60))
        self.name_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            input_font = QFont(self.nunito_font)
            input_font.setPointSize(scale.sc(18))
            self.name_input.setFont(input_font)

        font_family = "Nunito" if self.nunito_font else "Arial"
        self.name_input.setStyleSheet(f"""
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

        self.name_input.returnPressed.connect(self._on_submit)

        # Continue Button
        self.continue_button = self.create_button(t("continue_btn"))
        self.continue_button.clicked.connect(self._on_submit)

        # Layout Assembly
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.label)
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addWidget(self.name_input, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        layout.addWidget(self.continue_button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(layout)

    def _refresh_text(self):
        self.label.setText(t("clinician_name_title"))
        self.name_input.setPlaceholderText(t("clinician_name_placeholder"))
        self.continue_button.setText(t("continue_btn"))

    def _on_submit(self):
        """
        Validates the input, stores the clinician name, and navigates to the next screen.
        """
        clinician_name = self.name_input.text().strip()
        if not clinician_name:
            self.logger.warning("Attempted to submit an empty clinician name.")
            return

        self.logger.info(f"Clinician name entered: {clinician_name}")

        # --- FIX: save clinician name into patient_data ---
        self.patient_data["clinician_name"] = clinician_name

        # Save to SessionManager
        current_info = self.session_manager.data.get("subject_info", {})
        subject_id = current_info.get("subject_id")
        gender = current_info.get("gender")

        self.session_manager.set_subject_info(
            subject_id=subject_id,
            gender=gender,
            clinician_name=clinician_name
        )

        # Clear input field for next use
        self.name_input.clear()

        # Navigate to patient ID screen
        role = self.patient_data.get("role")
        if role == "clinician":
            self.main_window.navigate_to("clinician_patients")
        else:
            self.main_window.navigate_to("patient_id")
