"""
Base class for all screens in the PAINDICATOR application.
Provides a unified background, font loading, and button styling.
"""

import os
import sys
import logging
from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtGui import QPalette, QColor, QFont, QFontDatabase
from codes import theme
from codes import scale
from codes.translations import lang_manager

class BaseScreen(QWidget):
    """
    Provides common functionality for all UI screens:
    - Unified light-blue background color (#BBDCDF).
    - Robust, EXE-safe loading of the 'Nunito' font.
    - A factory method for creating consistently styled buttons.
    - Holds references to the main window for navigation and the shared patient data.
    """

    def __init__(self, main_window, patient_data, session_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.main_window = main_window
        self.patient_data = patient_data
        self.session_manager = session_manager
        self.logger = logging.getLogger(self.__class__.__name__)

        self.nunito_font = self._load_font()
        self._setup_background()

        # Apply the loaded font to the entire widget and all its children
        if self.nunito_font:
            self.setFont(self.nunito_font)

        # Connect to language changes
        lang_manager.connect(self._on_language_changed)

    def _on_language_changed(self, lang: str):
        self._refresh_text()

    def _refresh_text(self):
        """Override in subclasses to update all translatable text."""
        pass

    def _setup_background(self):
        """Sets the consistent light-blue background color for the screen."""
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(theme.BACKGROUND))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    # Button variant palettes: (bg, bg_hover/pressed, text, border)
    _BUTTON_VARIANTS = {
        "primary":   (theme.PRIMARY,       theme.PRIMARY_DARK, theme.TEXT_ON_PRIMARY, "none"),
        "secondary": ("transparent",       theme.PRIMARY_LIGHT, theme.PRIMARY_DARK,
                      f"2px solid {theme.PRIMARY}"),
        "danger":    (theme.DANGER,        theme.DANGER_DARK,  theme.TEXT_ON_PRIMARY, "none"),
    }

    def create_button(self, text: str, min_width: int = 300, min_height: int = 70,
                      variant: str = "primary") -> QPushButton:
        """
        Creates a QPushButton with the standard application styling.

        variant: "primary" (filled teal, default), "secondary" (outlined),
                 or "danger" (filled red, for destructive actions).
        """
        btn = QPushButton(text)
        btn.setMinimumSize(scale.sc(min_width), scale.sc(min_height))
        font_family = "Nunito" if self.nunito_font else "Arial"  # Fallback font

        bg, bg_active, fg, border = self._BUTTON_VARIANTS.get(
            variant, self._BUTTON_VARIANTS["primary"])

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                font-family: '{font_family}';
                font-size: {scale.sc(theme.FONT_H2)}px;
                font-weight: 500;
                border-radius: {scale.sc(theme.RADIUS_MD)}px;
                padding: {scale.sc(10)}px;
                border: {border};
            }}
            QPushButton:hover {{
                background-color: {bg_active};
            }}
            QPushButton:pressed {{
                background-color: {bg_active};
            }}
            QPushButton:disabled {{
                background-color: {theme.DISABLED_BG};
                color: {theme.DISABLED_TEXT};
                border: none;
            }}
        """)
        return btn

    def _get_base_path(self) -> str:
        """
        Gets the base path, compatible with both development and PyInstaller (Rule #5).
        """
        if hasattr(sys, '_MEIPASS'):
            # Running in a PyInstaller bundle
            return sys._MEIPASS
        # Running in a normal Python environment
        # Assumes this file is in '.../PAINDICATOR/codes/screens/'
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    def _load_font(self) -> QFont | None:
        """
        Robustly loads the 'Nunito' font from the 'files/fonts' directory.
        """
        base_path = self._get_base_path()
        possible_paths = [
            os.path.join(base_path, "files", "fonts", "Nunito-Regular.ttf"),
            os.path.join(base_path, "files", "fonts", "Nunito", "static", "Nunito-Regular.ttf")
        ]

        for font_path in possible_paths:
            if os.path.exists(font_path):
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    if font_families:
                        self.logger.info(f"Successfully loaded font: {font_families[0]} from {font_path}")
                        font = QFont(font_families[0])
                        font.setPointSize(12)  # Default size
                        return font
                else:
                    self.logger.warning(f"Failed to register font file: {font_path}")

        self.logger.warning("Nunito font not found. Using system default.")
        return None
