"""
RoleSelectionScreen: The initial screen where the user selects their role.
"""

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSpacerItem, QSizePolicy, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


class RoleSelectionScreen(BaseScreen):
    """
    UI screen for selecting a role ('Clinician' or 'Patient').
    This is the first screen the user sees.
    """

    def __init__(self, main_window, patient_data, **kwargs):
        super().__init__(main_window, patient_data, **kwargs)
        self.init_ui()

    def init_ui(self):
        """Sets up the widgets and layout for this screen."""
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(50), scale.sc(10), scale.sc(50), scale.sc(50))
        layout.setSpacing(scale.sc(20))

        # --- Logo above title ---
        from PyQt6.QtGui import QPixmap
        import os, sys

        logo_label = QLabel(self)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Build EXE-safe path
        if hasattr(sys, "_MEIPASS"):
            base_path = os.path.join(sys._MEIPASS, "files", "pictures")
        else:
            base_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "files", "pictures"
            )

        logo_path = os.path.join(base_path, "HD Logo.png")

        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            dpr = self.devicePixelRatio() or 1.0
            target_width = int(scale.sc(580) * dpr)
            pixmap = pixmap.scaledToWidth(target_width, Qt.TransformationMode.SmoothTransformation)
            pixmap.setDevicePixelRatio(dpr)
            logo_label.setPixmap(pixmap)
        else:
            print(f"[RoleSelection] ⚠️ logo.png not found at: {logo_path}")

        layout.addWidget(logo_label)
        layout.addSpacing(scale.sc(10))

        # Title Label
        self.title_label = QLabel(t("role_welcome_title"), self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            title_font = QFont(self.nunito_font)
            title_font.setPointSize(scale.sc(22))
            title_font.setBold(True)
            self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; background-color: transparent;")

        # Subtitle Label
        self.subtitle_label = QLabel(t("role_welcome_subtitle"), self)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.nunito_font:
            subtitle_font = QFont(self.nunito_font)
            subtitle_font.setPointSize(scale.sc(18))
            self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet(f"color: {theme.TEXT_SECOND}; margin-top: 10px; background-color: transparent;")

        # --- Layout Assembly ---
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addSpacerItem(QSpacerItem(20, 60, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # --- Button Container ---
        button_container = QWidget()
        button_container.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        button_layout = QHBoxLayout(button_container)
        button_layout.setSpacing(40)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.clinician_button = self.create_button(t("role_clinician"))
        self.patient_button = self.create_button(t("role_patient"))

        self.clinician_button.clicked.connect(lambda: self._on_role_selected("clinician"))
        self.patient_button.clicked.connect(lambda: self._on_role_selected("patient"))

        button_layout.addWidget(self.clinician_button)
        button_layout.addWidget(self.patient_button)

        layout.addWidget(button_container)
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Demo button — bottom-right corner, same style as main buttons but smaller
        bottom_bar = QWidget()
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(0, 0, scale.sc(10), scale.sc(5))
        bottom_bar_layout.addStretch()
        font_family = "Nunito" if self.nunito_font else "Arial"
        self.demo_button = QPushButton("Demo")
        self.demo_button.setMinimumSize(scale.sc(130), scale.sc(44))
        self.demo_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.PRIMARY};
                color: white;
                font-family: '{font_family}';
                font-size: {scale.sc(14)}px;
                font-weight: 500;
                border-radius: 10px;
                padding: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {theme.PRIMARY_DARK};
            }}
            QPushButton:pressed {{
                background-color: {theme.PRIMARY_DARK};
            }}
        """)
        self.demo_button.clicked.connect(self._on_demo_selected)
        bottom_bar_layout.addWidget(self.demo_button)
        layout.addWidget(bottom_bar)

        self.setLayout(layout)

    def _refresh_text(self):
        self.title_label.setText(t("role_welcome_title"))
        self.subtitle_label.setText(t("role_welcome_subtitle"))
        self.clinician_button.setText(t("role_clinician"))
        self.patient_button.setText(t("role_patient"))
        self.demo_button.setText("Demo")

    def _on_role_selected(self, role: str):
        """
        Stores the selected role in the central state and navigates to the next screen.
        """
        self.logger.info(f"Role selected: {role}")
        self.patient_data['role'] = role
        if self.session_manager:
            self.session_manager.demo_mode = False
        self.main_window.navigate_to("clinician_name")

    def _on_demo_selected(self):
        """Skip patient details and go straight to gender selection for demo/conference use."""
        self.logger.info("Demo mode selected")
        if self.session_manager:
            self.session_manager.demo_mode = True
            self.session_manager.set_subject_info(subject_id="DEMO", gender=None)
        self.main_window.navigate_to("gender_selection")
