# codes/widgets/topbar_widget.py
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QApplication
import os, sys
from codes import theme
from codes import scale
from codes.config import get_base_icons_path
from codes.translations import lang_manager

class TopBar(QWidget):
    """Global top navigation bar for PAINDICATOR."""

    backClicked = pyqtSignal()
    homeClicked = pyqtSignal()
    infoClicked = pyqtSignal()
    closeClicked = pyqtSignal()
    fullscreenClicked = pyqtSignal()

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        self.setFixedHeight(scale.sc(50))

        # Always keep the topbar layout left-to-right regardless of app language direction
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(scale.sc(10), scale.sc(8), scale.sc(10), scale.sc(8))
        layout.setSpacing(scale.sc(10))
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # --- Buttons ---
        _icons = get_base_icons_path()
        def _icon_btn(filename):
            btn = QPushButton()
            btn.setIcon(QIcon(os.path.join(_icons, filename)))
            btn.setIconSize(QSize(scale.sc(20), scale.sc(20)))
            return btn

        self.close_btn = _icon_btn("close.png")
        self.full_btn  = _icon_btn("fullscreen.png")
        self.home_btn  = _icon_btn("home.png")
        self.back_btn  = _icon_btn("back.png")
        self.info_btn  = _icon_btn("info_black.png")

        # --- Language toggle button ---
        self.lang_btn = QPushButton("עב")
        self.lang_btn.setFixedSize(scale.sc(36), scale.sc(30))
        self.lang_btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {theme.PRIMARY};
                background: transparent;
                font-size: {scale.sc(13)}px;
                font-weight: bold;
                color: {theme.PRIMARY};
                border-radius: 6px;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 206, 209, 0.1);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 206, 209, 0.2);
            }}
        """)

        # --- Add left side ---
        layout.addWidget(self.close_btn)
        layout.addWidget(self.full_btn)
        layout.addWidget(self.home_btn)
        layout.addWidget(self.back_btn)
        layout.addStretch()
        # --- Add right side ---
        layout.addWidget(self.lang_btn)
        layout.addWidget(self.info_btn)

        # --- Style ---
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(255, 255, 255, 220);
                border-bottom: 1px solid rgba(200, 230, 235, 0.8);
            }}
            QPushButton {{
                border: none;
                background: transparent;
                font-size: 20px;
                color: {theme.TEXT_SECOND};
                padding: 4px 8px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                color: {theme.PRIMARY};
                background-color: {theme.PRIMARY_LIGHT};
            }}
            QPushButton:pressed {{
                color: {theme.PRIMARY_DARK};
                background-color: rgba(0, 206, 209, 0.25);
            }}
        """)
        # Re-apply lang_btn style after global stylesheet (it overrides the one above)
        self.lang_btn.setStyleSheet(f"""
            QPushButton {{
                border: 1px solid {theme.PRIMARY};
                background: transparent;
                font-size: {scale.sc(13)}px;
                font-weight: bold;
                color: {theme.PRIMARY};
                border-radius: 6px;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 206, 209, 0.1);
            }}
            QPushButton:pressed {{
                background-color: rgba(0, 206, 209, 0.2);
            }}
        """)

        # --- Signals ---
        self.close_btn.clicked.connect(self.on_close)
        self.full_btn.clicked.connect(self.on_fullscreen)
        self.home_btn.clicked.connect(self.on_home)
        self.back_btn.clicked.connect(self.on_back)
        self.info_btn.clicked.connect(self.on_info)
        self.lang_btn.clicked.connect(self._on_lang_toggle)


    # ---------------------------------------------------------
    # Language toggle
    # ---------------------------------------------------------
    def _on_lang_toggle(self):
        lang_manager.toggle()
        new_lang = lang_manager.get_language()
        self.lang_btn.setText("EN" if new_lang == "he" else "עב")

    # ---------------------------------------------------------
    # Button behaviors
    # ---------------------------------------------------------
    def on_close(self):
        if self.main_window:
            self.main_window.close()

    def on_fullscreen(self):
        if self.main_window:
            if self.main_window.isFullScreen():
                self.main_window.showNormal()
            else:
                self.main_window.showFullScreen()

    def on_home(self):
        """
        Return to the role selection screen.
        Reset the session manager completely,
        because going 'home' means the session is over.
        """
        if self.main_window:
            try:
                sm = self.main_window.session_manager
                if sm:
                    # Completely reset session data
                    sm.data = {
                        "subject_info": {},
                        "questionnaire": {},
                        "model_data": {},
                        "screenshots": {},
                        "timestamp": None
                    }

                    # Ensure next save will create a NEW session folder
                    sm.current_session_folder = None

                    print("[TopBar] SessionManager reset on HOME.")
            except Exception as e:
                print(f"[TopBar] Error resetting SessionManager on HOME: {e}")

            # Reset ShowModel screen when leaving to home
            try:
                show_model = self.main_window.screens.get("show_model")
                if show_model is not None:
                    show_model.reset_for_new_session()
            except Exception as e:
                print(f"[TopBar] Failed to reset ShowModelScreen on HOME: {e}")

        # Reset Patient ID screen if it exists
        try:
            pid_screen = self.main_window.screens.get("patient_id")
            if pid_screen is not None:
                pid_screen.reset_screen()
        except Exception as e:
            print(f"[TopBar] Failed to reset PatientIDScreen: {e}")

        # Now navigate home — clear history so back can't return to a stale session
        self.main_window._nav_history.clear()
        self.main_window.navigate_to("role_selection", _push_history=False)

        # Reset questionnaire if it was filled
        q_screen = self.main_window.screens.get("questionnaire")
        if q_screen:
            q_screen.reset_questionnaire()

    def on_back(self):
        if self.main_window:
            self.main_window.navigate_back()

    def on_info(self):
        if not self.main_window:
            return
        info_screen = self.main_window.screens.get("info")
        if info_screen is None:
            return
        current = self.main_window.stacked_widget.currentWidget()
        if current is info_screen:
            self.main_window.navigate_back()
        else:
            self.main_window.navigate_to("info")
