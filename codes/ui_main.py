import sys
import importlib
import logging
from PyQt6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QSizePolicy
)
from PyQt6.QtCore import (
    QTimer, QTimeLine, Qt
)
from PyQt6.QtGui import QPainter, QPixmap, QGuiApplication
from PyQt6.QtGui import QIcon
import os, sys


# --------------------------------------------------------------
# Logging Configuration
# --------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] [%(name)s] %(message)s')


# --------------------------------------------------------------
# FaderWidget Class (Fixed – perfectly aligned, no vertical shift)
# --------------------------------------------------------------
class FaderWidget(QWidget):
    """Widget that fades smoothly between two screens using QTimeLine."""
    def __init__(self, old_widget: QWidget, new_widget: QWidget):
        # Attach to same parent (the stacked_widget) to avoid layout offsets
        super().__init__(old_widget.parent())
        # grab() handles HiDPI correctly (captures at physical pixel resolution)
        self.old_pixmap = old_widget.grab()

        # Timeline-based fade animation
        self.timeline = QTimeLine(400, self)
        self.timeline.setFrameRange(0, 100)
        self.timeline.frameChanged.connect(self.repaint)
        self.timeline.finished.connect(self.deleteLater)
        self.timeline.start()

        # Match geometry of the old widget exactly
        self.resize(old_widget.size())
        self.move(old_widget.pos())
        self.show()
        self.raise_()



    def paintEvent(self, event):
        """Draw the fading overlay over the old widget without scaling or blur."""
        painter = QPainter(self)
        # Disable any smoothing or scaling interpolation
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        # Compute opacity from timeline (1.0 → 0.0)
        opacity = 1.0 - self.timeline.currentValue()
        painter.setOpacity(opacity)

        # Draw at exact geometry (no stretch)
        target_rect = self.rect()
        painter.drawPixmap(target_rect, self.old_pixmap, self.old_pixmap.rect())

        painter.end()


# --------------------------------------------------------------
# Main Window Class
# --------------------------------------------------------------
class MainWindow(QMainWindow):
    """Main application window – includes persistent TopBar and smooth fade transitions."""

    def __init__(self, session_manager=None):
        super().__init__()
        self.session_manager = session_manager  # ← נוספה שורה זו
        self._nav_history = []

        # --- Window Title and Icon Setup ---
        self.setWindowTitle("PAINDICATOR")

        # Build EXE-safe path
        if hasattr(sys, "_MEIPASS"):
            base_path = os.path.join(sys._MEIPASS, "files", "pictures")
        else:
            base_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "files", "pictures"
            )

        # Prefer .ico for Windows title bar
        icon_path = os.path.join(base_path, "logo.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_path, "logo.png")

        # Apply window icon
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            print(f"[MainWindow] ✅ Window icon set from: {icon_path}")
        else:
            print(f"[MainWindow] ⚠️ No logo icon found at: {icon_path}")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.setWindowTitle("PAINDICATOR")
        # Cap initial size to the available screen area so the window never
        # opens larger than the display (important for small/HiDPI screens).
        screen = QGuiApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            self.resize(
                min(1280, available.width()),
                min(800, available.height()),
            )
            # Hard cap: window can never grow beyond the available screen area,
            # even when child widgets report large sizeHints after a layout update.
            self.setMaximumSize(available.width(), available.height())
        else:
            self.resize(1280, 800)

        # Central state shared across screens
        self.patient_data = {}

        # ----------------------------------------------------------
        # Layout: TopBar + Screens
        # ----------------------------------------------------------
        from codes.widgets.topbar_widget import TopBar
        central_widget = QWidget()
        # Ignored size policy: QMainWindow will not auto-resize when child
        # widgets (e.g. VTK) report changed sizeHints after a language change.
        central_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- TopBar ---
        self.topbar = TopBar(main_window=self)
        layout.addWidget(self.topbar)

        # --- Stacked Screens ---
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        self.screens = {}

        # --- Register Screens ---
        screen_names = [
            "role_selection",
            "clinician_name",

            # clinician flow (NEW)
            "clinician_patients",
            "clinician_session_selection",
            "clinician_view_session",

            # patient flow
            "patient_id",
            "gender_selection",
            "questionnaire",
            "show_model",
            "info",
        ]
        self._register_screens(screen_names)



    # --------------------------------------------------------------
    # Register and Start
    # --------------------------------------------------------------
    def _register_screens(self, names: list[str]):
        """Dynamically import and register screens."""
        for name in names:
            try:
                module = importlib.import_module(f"codes.screens.{name}")
                class_name = "".join(part.capitalize() for part in name.split('_')) + "Screen"
                screen_class = getattr(module, class_name)
                instance = screen_class(main_window=self, patient_data=self.patient_data, session_manager=self.session_manager)
                self.screens[name] = instance
                self.stacked_widget.addWidget(instance)
                self.logger.info(f"Screen '{name}' registered successfully.")
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Failed to load screen '{name}': {e}")



    # --------------------------------------------------------------
    # Fade Transition Navigation (using FaderWidget)
    # --------------------------------------------------------------
    def showEvent(self, event):
        """Connect screen-change tracking once the native window exists."""
        super().showEvent(event)
        if not getattr(self, "_screen_change_hooked", False):
            handle = self.windowHandle()
            if handle is not None:
                handle.screenChanged.connect(self._on_screen_changed)
                self._screen_change_hooked = True

    def _on_screen_changed(self, qscreen):
        """Recompute the global UI scale when the window moves to another screen."""
        try:
            from codes import scale as _scale_mod
            if qscreen is not None and _scale_mod.update_scale(qscreen.availableGeometry()):
                self.logger.info(
                    f"UI scale updated for new screen: factor={_scale_mod.get():.2f}")
        except Exception as e:
            self.logger.warning(f"Scale update on screen change failed: {e}")

    def navigate_back(self):
        """Return to the previous screen. Does nothing if history is empty."""
        if not self._nav_history:
            return
        screen_name = self._nav_history.pop()
        self.navigate_to(screen_name, _push_history=False)

    def keyPressEvent(self, event):
        from PyQt6.QtCore import Qt
        if event.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
        else:
            super().keyPressEvent(event)

    def navigate_to(self, screen_name: str, _push_history: bool = True, **kwargs):
        """Switch screens with smooth fade (skip fade for VTK)."""
        if screen_name not in self.screens:
            self.logger.warning(f"Screen '{screen_name}' not found.")
            return

        current_widget = self.stacked_widget.currentWidget()
        widget_to_show = self.screens[screen_name]

        # --- Unsaved-changes guard ---
        # If the current screen defines confirm_leave() and it returns False,
        # the user chose to stay — abort navigation.
        if (current_widget is not None and current_widget is not widget_to_show
                and hasattr(current_widget, "confirm_leave")):
            try:
                if not current_widget.confirm_leave():
                    self.logger.info(f"Navigation to '{screen_name}' cancelled by user (unsaved changes).")
                    return
            except Exception as e:
                self.logger.warning(f"confirm_leave() failed: {e}")

        # Push current screen to history so navigate_back() can return here.
        if _push_history:
            current_name = self.current_screen_name()
            if current_name and current_name != screen_name:
                self._nav_history.append(current_name)

        # --- Optional pre-entry logic ---
        if hasattr(widget_to_show, "enter_screen") and callable(widget_to_show.enter_screen):
            widget_to_show.enter_screen()

        # --- Pass kwargs to on_load if available ---
        if hasattr(widget_to_show, "on_load") and callable(widget_to_show.on_load):
            try:
                widget_to_show.on_load(**kwargs)
            except Exception as e:
                self.logger.warning(f"[MainWindow] on_load error in '{screen_name}': {e}")

        # --- First load or same screen → show directly ---
        if current_widget is None or current_widget is widget_to_show or not self.isVisible():
            self.stacked_widget.setCurrentWidget(widget_to_show)
            self.logger.info(f"Navigating to screen: '{screen_name}'")
            return

        # --- Skip fade when entering a VTK screen (VTK may not be ready under the overlay) ---
        if screen_name in ["show_model", "clinician_view_session"]:
            self.stacked_widget.setCurrentWidget(widget_to_show)
            self.logger.info(f"Navigating (no fade): '{screen_name}'")
            return

        # --- Perform fade animation ---
        self.stacked_widget.setCurrentWidget(widget_to_show)

        # Create Fader directly under the stacked widget (no layout offset)
        fader = FaderWidget(current_widget, widget_to_show)
        fader.setParent(self.stacked_widget)
        fader.setGeometry(self.stacked_widget.rect())
        fader.show()
        fader.raise_()

        self.logger.info(f"Navigating with fade: '{screen_name}'")

    # --------------------------------------------------------------
    # Helper Methods
    # --------------------------------------------------------------
    def current_screen_name(self) -> str:
        """Return current screen name for logic checks."""
        current_widget = self.stacked_widget.currentWidget()
        for name, widget in self.screens.items():
            if widget is current_widget:
                return name
        return ""


# --------------------------------------------------------------
# Entry Point
# --------------------------------------------------------------
def main():
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
