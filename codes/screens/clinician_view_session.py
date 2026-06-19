# codes/screens/clinician_view_session.py
# NOTE: All comments are in English only.

import json
import logging
import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox,
    QPushButton, QSplitter,
)
from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from codes.config import get_base_icons_path
from codes.translations import t

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from codes.renderer_scene import RendererScene
from codes.config import get_base_models_path
from codes.pain_analyzer import analyze_pain
from codes.widgets.navigation_panel import NavigationPanel
from .base_screen import BaseScreen


class _ClinicianTouchFilter(QObject):
    """
    Replaces the old monkey-patch event filter for the clinician VTK widget.

    Gesture rules (clinician view is read-only — no painting):
    - 1 finger: dominant-direction rotation.
        |dx| >= |dy|  →  azimuth only  (horizontal swipe rotates left/right, no wobble)
        |dy| >  |dx|  →  elevation only (vertical swipe tilts up/down, no wobble)
    - 2 fingers: pinch = zoom, translate = pan, twist = azimuth rotation
    """

    def __init__(self, screen, parent=None):
        super().__init__(parent)
        self._s = screen

    def eventFilter(self, obj, event):
        etype = event.type()

        # Swallow touch-synthesized mouse events (deviceType != Mouse) so VTK's
        # trackball doesn't double-drive the camera; a real mouse passes through.
        if etype in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                     QEvent.Type.MouseMove, QEvent.Type.MouseButtonDblClick):
            try:
                from PyQt6.QtGui import QInputDevice
                if event.deviceType() != QInputDevice.DeviceType.Mouse:
                    return True
            except Exception:
                pass
            return False

        if etype not in (QEvent.Type.TouchBegin,
                         QEvent.Type.TouchUpdate,
                         QEvent.Type.TouchEnd):
            return False

        pts = event.points()

        if etype == QEvent.Type.TouchBegin:
            self._s._touch_manager.handle_touch_begin(event)
            return True

        if etype == QEvent.Type.TouchUpdate:
            tm = self._s._touch_manager
            tm.handle_touch_update(event)
            if self._s.scene:
                if len(pts) == 1:
                    dx = tm.last_rotation_dx
                    dy = tm.last_rotation_dy
                    # Lock to dominant axis to prevent diagonal wobble/tilt
                    if abs(dx) >= abs(dy):
                        self._s.scene.apply_touch_rotation(dx, 0)    # azimuth only
                    else:
                        self._s.scene.apply_touch_rotation(0, dy)    # elevation only
                else:
                    if tm.last_pinch_scale != 1.0:
                        self._s.scene.apply_zoom(tm.last_pinch_scale)
                        self._s.nav_panel._sync_slider()
                    if tm.last_pan_dx or tm.last_pan_dy:
                        self._s.scene.apply_pan(tm.last_pan_dx, tm.last_pan_dy)
                    if tm.last_twist_deg:
                        self._s.scene.apply_touch_rotation(tm.last_twist_deg / 0.3, 0)
            return True

        if etype == QEvent.Type.TouchEnd:
            self._s._touch_manager.handle_touch_end(event)
            return True

        return False


class ToggleSwitch(QWidget):
    """Pill-shaped sliding toggle switch painted with QPainter."""
    toggled_signal = pyqtSignal(bool)
    _W, _H = 44, 24

    def __init__(self, parent=None):
        super().__init__(parent)
        self._on = False
        self.setFixedSize(self._W, self._H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_on(self):
        return self._on

    def set_on(self, state: bool):
        self._on = state
        self.update()

    def mousePressEvent(self, event):
        if self.isEnabled():
            self._on = not self._on
            self.toggled_signal.emit(self._on)
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_h = self._H - 6
        if self._on:
            p.setBrush(QColor(0, 206, 209, 180))
            p.setPen(QColor(0, 206, 209, 220))
        else:
            p.setBrush(QColor(100, 116, 139, 80))
            p.setPen(QColor(148, 163, 184, 120))
        p.drawRoundedRect(1, 3, self._W - 2, track_h, track_h // 2, track_h // 2)
        r = track_h - 4
        x = self._W - r - 4 if self._on else 4
        alpha = 220 if self.isEnabled() else 90
        p.setBrush(QColor(255, 255, 255, alpha))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(x, (self._H - r) // 2, r, r)


def _severity_label(avg_pain: float) -> str:
    """Map average paint level (1.0–3.0) to a clinical severity label.
    Based on intensity alone — how hard the patient painted — not on spatial extent.
      1.0–1.49 → Mild     (yellow only)
      1.5–2.49 → Moderate (mix of yellow/orange)
      2.5–3.0  → Severe   (predominantly orange/red)
    """
    if avg_pain >= 2.5:
        return "Severe"
    if avg_pain >= 1.5:
        return "Moderate"
    return "Mild"


class _TextTouchScroller(QObject):
    """
    Event filter installed on the viewport of a read-only QTextEdit.
    Single-finger touch scrolls the widget instead of selecting text.
    """
    def __init__(self, text_edit):
        super().__init__(text_edit)
        self._te = text_edit
        self._active = False
        self._last_y = 0.0

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.TouchBegin:
            pts = event.points()
            if pts:
                self._active = True
                self._last_y = pts[0].position().y()
                event.accept()
                return True
        elif t == QEvent.Type.TouchUpdate:
            if not self._active:
                return False
            pts = event.points()
            if pts:
                y = pts[0].position().y()
                dy = self._last_y - y
                self._last_y = y
                bar = self._te.verticalScrollBar()
                bar.setValue(int(bar.value() + dy))
                event.accept()
            return True
        elif t == QEvent.Type.TouchEnd:
            self._active = False
            return False
        return False


class ClinicianViewSessionScreen(BaseScreen):
    """
    Clinician read-only session viewer.

    Features:
      - Loads the exact model the patient painted on (same topology → marks align)
      - Shows pain marks on the regular model (gray base + pain colors)
      - Toggle button switches to dermatome-region view
      - Dermatome statistics, questionnaire, and comments panels
      - Click on model while dermatome map is active → floating label shows dermatome name
      - Compare button overlays a previous session's marks in cool tones (blue/violet)
      - Analyze Pain Pattern button → AI clinical decision support report
    """

    def __init__(self, main_window, patient_data, session_manager=None, **kwargs):
        super().__init__(main_window, patient_data, session_manager=session_manager, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.scene = None
        self.vtk_widget = None
        self._showing_derm_view = False
        self._vtk_obs_tag = None        # VTK observer tag — removed on re-init
        self._comparison_active = False  # whether an overlay is currently shown

        # Auto-rotate (demo/presentation spin mode)
        self._auto_rotate_timer = QTimer(self)
        self._auto_rotate_timer.setInterval(16)
        self._auto_rotate_timer.timeout.connect(self._do_auto_rotate_step)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        _icons = get_base_icons_path()
        _ico_size = QSize(18, 18)

        # Tint helper — same approach as VTKToolBar
        def _tint(source, color: str) -> QPixmap:
            px = source if isinstance(source, QPixmap) else QPixmap(source)
            if px.isNull():
                return px
            tinted = QPixmap(px.size())
            tinted.fill(Qt.GlobalColor.transparent)
            p = QPainter(tinted)
            p.drawPixmap(0, 0, px)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            p.fillRect(tinted.rect(), QColor(color))
            p.end()
            return tinted

        def _icon(filename):
            path = os.path.join(_icons, filename)
            if filename.endswith(".svg"):
                return QIcon(path)
            return QIcon(_tint(path, "#E2EAF4"))

        # Glassmorphism button style — mirrors the VTKToolBar buttons
        _BTN_STYLE = """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.14),
                    stop:1 rgba(100, 116, 139, 0.10));
                color: #E2EAF4;
                font-size: 13px;
                font-weight: 500;
                border-radius: 8px;
                border: 1px solid rgba(148, 163, 184, 0.30);
                padding: 5px 14px;
                box-shadow: 0 0 6px rgba(186, 230, 253, 0.12);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 206, 209, 0.32),
                    stop:1 rgba(0, 206, 209, 0.16));
                border: 1px solid rgba(0, 206, 209, 0.85);
                color: #FFFFFF;
                box-shadow: 0 0 14px rgba(186, 230, 253, 0.55);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(0, 206, 209, 0.52),
                    stop:1 rgba(0, 206, 209, 0.32));
                border: 1px solid #00CED1;
                color: #FFFFFF;
                box-shadow: 0 0 20px rgba(186, 230, 253, 0.80);
            }
            QPushButton:disabled {
                background: rgba(100, 116, 139, 0.10);
                color: rgba(226, 234, 244, 0.35);
                border: 1px solid rgba(148, 163, 184, 0.12);
            }
        """

        def _btn(label, icon_file):
            b = QPushButton(label)
            b.setFixedHeight(36)
            b.setIcon(_icon(icon_file))
            b.setIconSize(_ico_size)
            b.setStyleSheet(_BTN_STYLE)
            return b

        # Keep the entire screen LTR so the model/nav/text panels never swap sides
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Dark header bar (title + datetime + action buttons) ──────────
        header_bar = QWidget(self)
        header_bar.setObjectName("clinicianHeader")
        header_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_bar.setStyleSheet("""
            QWidget#clinicianHeader {
                background-color: rgba(15, 23, 42, 0.92);
                border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            }
        """)
        header_bar.setFixedHeight(56)
        header_bar.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        # Grid layout: 3 equal columns → left | CENTER | right
        from PyQt6.QtWidgets import QGridLayout
        grid = QGridLayout(header_bar)
        grid.setContentsMargins(12, 0, 12, 0)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # ── Left group: Back · toggle switch · Compare ────────────────
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QHBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self._back_btn = _btn(t("clinician_view_back"), "back.png")
        self._back_btn.clicked.connect(lambda: self.main_window.navigate_back())
        left_layout.addWidget(self._back_btn)

        toggle_wrap = QWidget()
        toggle_wrap.setStyleSheet("background: transparent;")
        tw_layout = QHBoxLayout(toggle_wrap)
        tw_layout.setContentsMargins(8, 0, 4, 0)
        tw_layout.setSpacing(6)
        self._toggle_switch = ToggleSwitch()
        self._toggle_label = QLabel(t("clinician_view_dermatome_map"))
        self._toggle_label.setStyleSheet(
            "color: rgba(226, 234, 244, 0.55); font-size: 12px;"
            " background: transparent; border: none;"
        )
        tw_layout.addWidget(self._toggle_switch)
        tw_layout.addWidget(self._toggle_label)
        self._toggle_switch.toggled_signal.connect(lambda _: self._on_toggle_model_view())
        left_layout.addWidget(toggle_wrap)

        self.compare_btn = _btn(t("clinician_view_compare"), "compare.svg")
        self.compare_btn.clicked.connect(self._on_compare_clicked)
        left_layout.addWidget(self.compare_btn)

        self._reset_btn = _btn(t("clinician_view_reset_view"), "camera.svg")
        self._reset_btn.clicked.connect(self._on_reset_camera_clicked)
        left_layout.addWidget(self._reset_btn)

        left_layout.addStretch(1)

        grid.addWidget(left_widget, 0, 0, Qt.AlignmentFlag.AlignVCenter)

        # ── Center: patient ID + datetime (truly centered) ────────────
        center_widget = QWidget()
        center_widget.setStyleSheet("background: transparent;")
        center_col = QVBoxLayout(center_widget)
        center_col.setSpacing(1)
        center_col.setContentsMargins(0, 0, 0, 0)
        self.id_label = QLabel("—")
        self.id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.id_label.setStyleSheet(
            "color: #E2EAF4; font-size: 15px; font-weight: bold;"
            " background: transparent; border: none;"
        )
        self.datetime_label = QLabel("")
        self.datetime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.datetime_label.setStyleSheet(
            "color: rgba(186, 230, 253, 0.70); font-size: 11px;"
            " background: transparent; border: none;"
        )
        center_col.addWidget(self.id_label)
        center_col.addWidget(self.datetime_label)

        grid.addWidget(center_widget, 0, 1,
                       Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

        # ── Right: Analyze ────────────────────────────────────────────
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addStretch(1)
        self.analyze_btn = _btn(t("clinician_view_analyze"), "lightbulb.svg")
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        right_layout.addWidget(self.analyze_btn)

        grid.addWidget(right_widget, 0, 2, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addWidget(header_bar)

        # ── Content row ──────────────────────────────────────────────────
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(5)
        content_splitter.setStyleSheet(
            "QSplitter::handle { background: rgba(148, 163, 184, 0.25); }"
            "QSplitter::handle:hover { background: rgba(0, 206, 209, 0.55); }"
        )
        main_layout.addWidget(content_splitter, stretch=1)

        # Left: VTK + nav panel
        self._left_container = QWidget(self)
        self._left_container.setStyleSheet("background-color: #8A99AB;")
        left_layout = QVBoxLayout(self._left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        vtk_nav_row = QHBoxLayout()
        vtk_nav_row.setContentsMargins(0, 0, 0, 0)
        vtk_nav_row.setSpacing(0)

        self.vtk_widget = QVTKRenderWindowInteractor(self._left_container)
        self.vtk_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.vtk_widget.setMinimumSize(1, 1)
        self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self.nav_panel = NavigationPanel(self._left_container)

        from codes.touch_manager import TouchManager
        self._touch_manager = TouchManager(self)

        # Touch gestures via a PROPER installed event filter. A monkey-patched
        # self.vtk_widget.event = ... does not reliably get called by Qt's C++
        # event dispatch, so touch was never handled (one-finger "rotation" was
        # just mouse-promotion). installEventFilter mirrors show_model, which works.
        # 1 finger = rotate, 2 fingers = zoom/pan/twist; synthesized-from-touch
        # mouse is swallowed inside the filter. Mouse-wheel zoom still reaches VTK
        # and syncs the slider via the interactor's _on_zoom_changed callback
        # (set in _init_scene_from_session).
        self._vtk_touch_filter = _ClinicianTouchFilter(self)
        self.vtk_widget.installEventFilter(self._vtk_touch_filter)

        vtk_nav_row.addWidget(self.vtk_widget, stretch=1)
        vtk_nav_row.addWidget(self.nav_panel)
        left_layout.addLayout(vtk_nav_row, stretch=1)

        # Floating dermatome name label — child of left_container so coords match
        self._derm_popup = QLabel(self._left_container)
        self._derm_popup.setStyleSheet(
            "background-color: rgba(15, 23, 42, 0.88); color: #BAE6FD;"
            "border-radius: 6px; border: 1px solid rgba(0, 206, 209, 0.50);"
            "padding: 4px 12px; font-size: 14px; font-weight: bold;"
        )
        self._derm_popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._derm_popup.hide()

        content_splitter.addWidget(self._left_container)

        # Right: data panels
        _PANEL_LABEL = "color: #0A1628; font-size: 12px; font-weight: bold; padding: 2px 0px;"
        _PANEL_TEXT = (
            "QTextEdit {"
            "  background-color: rgba(255, 255, 255, 0.72);"
            "  border: 1px solid rgba(0, 206, 209, 0.30);"
            "  border-radius: 6px;"
            "  color: #0A1628;"
            "  font-size: 12px;"
            "  padding: 4px;"
            "}"
            "QScrollBar:vertical {"
            "  background: rgba(240, 244, 248, 0.60);"
            "  width: 6px;"
            "  border-radius: 3px;"
            "  margin: 0px;"
            "}"
            "QScrollBar::handle:vertical {"
            "  background: rgba(0, 206, 209, 0.55);"
            "  border-radius: 3px;"
            "  min-height: 20px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "  height: 0px;"
            "}"
        )

        right_container = QWidget(self)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 6, 6, 6)
        right_layout.setSpacing(4)

        self._d_label = QLabel(t("clinician_view_dermatome_analysis"), right_container)
        self._d_label.setStyleSheet(_PANEL_LABEL)
        self.d_text = QTextEdit(right_container)
        self.d_text.setReadOnly(True)
        self.d_text.setMinimumHeight(180)
        self.d_text.setStyleSheet(_PANEL_TEXT)

        self._q_label = QLabel(t("clinician_view_questionnaire"), right_container)
        self._q_label.setStyleSheet(_PANEL_LABEL)
        self.q_text = QTextEdit(right_container)
        self.q_text.setReadOnly(True)
        self.q_text.setStyleSheet(_PANEL_TEXT)

        self._c_label = QLabel(t("clinician_view_comments"), right_container)
        self._c_label.setStyleSheet(_PANEL_LABEL)
        self.c_text = QTextEdit(right_container)
        self.c_text.setReadOnly(True)
        self.c_text.setStyleSheet(_PANEL_TEXT)

        # Install touch-scroll on each read-only panel (finger scrolls, never selects)
        self._text_touch_scrollers = []
        for _te in (self.d_text, self.q_text, self.c_text):
            _te.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
            _ts = _TextTouchScroller(_te)
            _te.viewport().installEventFilter(_ts)
            self._text_touch_scrollers.append(_ts)

        right_layout.addWidget(self._d_label)
        right_layout.addWidget(self.d_text, stretch=2)
        right_layout.addWidget(self._q_label)
        right_layout.addWidget(self.q_text, stretch=1)
        right_layout.addWidget(self._c_label)
        right_layout.addWidget(self.c_text, stretch=1)

        content_splitter.addWidget(right_container)
        # Initial split: ~67% VTK / ~33% text panel (mirrors the old 4:2 stretch ratio)
        content_splitter.setSizes([660, 330])
        self.setLayout(main_layout)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self._init_scene_from_session()
        # Force touch registration on the native VTK window. QVTKRenderWindowInteractor
        # creates a WA_PaintOnScreen native window before WA_AcceptTouchEvents is set,
        # and on Windows that window can fail to register for touch — so finger input
        # arrives only as synthesized MOUSE events and two-finger zoom/pan never reach
        # TouchManager. Toggling the attribute now (window realized) re-triggers Qt's
        # touch registration. Same fix as ShowModelScreen.
        try:
            self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
            self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        except Exception as e:
            self.logger.error(f"[ClinicianView] Touch re-registration failed: {e}")

    # ------------------------------------------------------------------
    # Scene initialization
    # ------------------------------------------------------------------
    def _init_scene_from_session(self):
        if not self.session_manager:
            self.logger.warning("[ClinicianView] No SessionManager.")
            return

        # Stop any running auto-rotate before reinitialising the scene
        self.nav_panel.stop_auto_rotate()

        # Remove previous VTK observer (same interactor object is reused across sessions)
        self._remove_vtk_observer()

        # Reset comparison state
        self._comparison_active = False
        self.compare_btn.setText(t("clinician_view_compare_session"))

        data = self.session_manager.data or {}
        subject_info = data.get("subject_info") or {}
        model_data = data.get("model_data") or {}
        questionnaire = data.get("questionnaire") or {}

        # Patient ID + timestamp in center of header
        patient_id = subject_info.get("subject_id") or "—"
        self._current_patient_id = patient_id
        self.id_label.setText(f"{t('clinician_view_patient_label')}  {patient_id}")
        ts = data.get("timestamp")
        if isinstance(ts, str):
            try:
                dt_line = datetime.fromisoformat(ts).strftime("%d/%m/%Y  •  %H:%M")
            except Exception:
                dt_line = ts
            self.datetime_label.setText(dt_line)

        gender = (subject_info.get("gender") or "female").lower()

        if gender == "female":
            from codes.config import get_female_model_info
            _gender_info = get_female_model_info()
        else:
            from codes.config import get_male_model_info
            _gender_info = get_male_model_info()
        model_path = _gender_info["model_path"]

        try:
            self.scene = RendererScene(self.vtk_widget, model_path,
                                       session_manager=self.session_manager,
                                       initial_azimuth=_gender_info.get("initial_azimuth", 0))
            self.nav_panel.set_renderer(self.scene)
            self.nav_panel.auto_rotate_toggled.connect(self._on_auto_rotate_toggled)
            if self.scene.interactor_style:
                self.scene.interactor_style._on_zoom_changed = self.nav_panel._sync_slider
            self.logger.info(f"[ClinicianView] RendererScene initialized: {model_path}")
        except Exception as e:
            self.logger.error(f"[ClinicianView] Failed to init RendererScene: {e}")
            return

        # Apply saved PaintV2 marks
        try:
            self.scene.apply_saved_marks(model_data)
        except Exception as e:
            self.logger.error(f"[ClinicianView] Failed to apply saved marks: {e}")

        # Build the dermatome swap actor (male only)
        self._showing_derm_view = False
        self._derm_popup.hide()
        self._toggle_switch.set_on(False)
        self._toggle_label.setText(t("clinician_view_dermatome_map"))
        self._toggle_label.setStyleSheet(
            "color: rgba(226, 234, 244, 0.55); font-size: 12px;"
            " background: transparent; border: none;"
        )

        # _gender_info was set above when selecting the model path
        self.scene.set_dermatome_map_paths(_gender_info["derm_bin"], _gender_info["derm_meta"])
        ok = self.scene.build_dermatome_swap_actor(
            _gender_info["derm_swap_ply"],
            show_pain_overlay=_gender_info["swap_show_pain"],
        )
        self._toggle_switch.setEnabled(ok)
        if not ok:
            self.logger.warning("[ClinicianView] Dermatome swap actor could not be built.")

        # Compute and display dermatome stats (also loads the mapper)
        self._populate_dermatome_panel(gender)

        # Populate questionnaire and comments
        self._populate_text_panels(questionnaire, model_data)

        # Register VTK click observer for dermatome popup
        try:
            self._vtk_obs_tag = self.scene.interactor.AddObserver(
                "LeftButtonPressEvent", self._on_vtk_model_click
            )
        except Exception as e:
            self.logger.error(f"[ClinicianView] Could not add VTK observer: {e}")

        # Enable compare button only when there are other sessions to compare with
        other = self._find_other_sessions()
        self.compare_btn.setEnabled(len(other) > 0)

        # Enable analyze button — always available (works even without dermatome data)
        self.analyze_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Auto-rotate (demo / presentation spin mode)
    # ------------------------------------------------------------------
    def _on_auto_rotate_toggled(self, active: bool):
        if active:
            self._auto_rotate_timer.start()
            for btn in [self.nav_panel.zoom_in_btn, self.nav_panel.zoom_out_btn,
                        self.nav_panel.zoom_slider]:
                btn.setEnabled(False)
        else:
            self._auto_rotate_timer.stop()
            for btn in [self.nav_panel.zoom_in_btn, self.nav_panel.zoom_out_btn,
                        self.nav_panel.zoom_slider]:
                btn.setEnabled(True)

    def _do_auto_rotate_step(self):
        if self.scene:
            self.scene.rotate_azimuth_step(0.3)

    # ------------------------------------------------------------------
    def _remove_vtk_observer(self):
        """Remove the previously registered VTK left-click observer if any."""
        if self._vtk_obs_tag is not None:
            try:
                interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
                interactor.RemoveObserver(self._vtk_obs_tag)
            except Exception:
                pass
            self._vtk_obs_tag = None

    # ------------------------------------------------------------------
    # VTK click → dermatome popup
    # ------------------------------------------------------------------
    def _on_vtk_model_click(self, obj, event):
        """
        VTK LeftButtonPressEvent observer.
        Always closes the existing popup; opens a new one when the dermatome
        map is active and the click lands on a named dermatome.
        """
        self._derm_popup.hide()

        if not self._showing_derm_view or self.scene is None:
            return

        vtk_x, vtk_y = obj.GetEventPosition()
        name = self.scene.get_dermatome_name_at(vtk_x, vtk_y)
        if not name:
            return

        self._derm_popup.setText(name)
        self._derm_popup.adjustSize()
        self._derm_popup.move(12, 12)
        self._derm_popup.show()
        self._derm_popup.raise_()

    # ------------------------------------------------------------------
    # Session comparison
    # ------------------------------------------------------------------
    def _find_other_sessions(self) -> list[dict]:
        """
        Return a list of other saved sessions for the same patient, excluding
        the currently displayed session.
        Each entry: {"label": str, "json_path": str}
        """
        if not self.session_manager:
            return []

        subject_info = self.session_manager.data.get("subject_info") or {}
        patient_id = subject_info.get("subject_id") or ""
        if not patient_id:
            return []

        current_folder = self.session_manager.current_session_folder or ""
        patient_dir = os.path.join("data", "sessions", str(patient_id))
        if not os.path.isdir(patient_dir):
            return []

        sessions = []
        for folder in sorted(os.listdir(patient_dir), reverse=True):
            if folder == current_folder:
                continue
            session_path = os.path.join(patient_dir, folder)
            json_path = os.path.join(session_path, "session.json")
            if not os.path.isfile(json_path):
                continue
            # Try to format a human-readable label from the folder name
            # Folder format: session_DD-MM-YYYY_HH-MM-SS
            label = folder
            try:
                parts = folder.replace("session_", "", 1).split("_")
                if len(parts) == 2:
                    date_str, time_str = parts
                    dt = datetime.strptime(f"{date_str}_{time_str}", "%d-%m-%Y_%H-%M-%S")
                    label = dt.strftime("%d/%m/%Y  %H:%M:%S")
            except Exception:
                pass
            sessions.append({"label": label, "json_path": json_path})

        return sessions

    def _pick_session_dialog(self, sessions: list[dict]) -> str | None:
        """
        Show a modal dialog listing available sessions.
        Returns the json_path of the selected session, or None if cancelled.
        """
        dialog = QDialog(self)
        dialog.setWindowTitle(t("clinician_compare_dialog_title"))
        dialog.setMinimumWidth(380)

        layout = QVBoxLayout(dialog)

        info = QLabel(t("clinician_compare_dialog_info"))
        info.setWordWrap(True)
        layout.addWidget(info)

        list_widget = QListWidget()
        for s in sessions:
            item = QListWidgetItem(s["label"])
            item.setData(Qt.ItemDataRole.UserRole, s["json_path"])
            list_widget.addItem(item)
        list_widget.setCurrentRow(0)
        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        selected = list_widget.currentItem()
        if selected is None:
            return None
        return selected.data(Qt.ItemDataRole.UserRole)

    def _load_point_levels(self, json_path: str) -> list | None:
        """Load point_levels from a session.json file."""
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            paint_v2 = (data.get("model_data") or {}).get("paint_v2") or {}
            levels = paint_v2.get("point_level")
            if isinstance(levels, list) and len(levels) > 0:
                return levels
        except Exception as e:
            self.logger.error(f"[ClinicianView] Could not load point_levels from {json_path}: {e}")
        return None

    def _on_compare_clicked(self):
        if self.scene is None:
            return

        # If overlay already active → remove it
        if self._comparison_active:
            self.scene.remove_comparison_overlay()
            self._comparison_active = False
            self.compare_btn.setText(t("clinician_view_compare_session"))
            return

        # Find and let user pick a session
        sessions = self._find_other_sessions()
        if not sessions:
            return

        json_path = self._pick_session_dialog(sessions)
        if json_path is None:
            return

        point_levels = self._load_point_levels(json_path)
        if point_levels is None:
            self.logger.warning(f"[ClinicianView] No paint data in selected session: {json_path}")
            return

        ok = self.scene.add_comparison_overlay(point_levels)
        if ok:
            self._comparison_active = True
            self.compare_btn.setText(t("clinician_view_remove_compare"))

    # ------------------------------------------------------------------
    # Dermatome statistics
    # ------------------------------------------------------------------
    def _populate_dermatome_panel(self, gender: str):
        """Compute dermatome coverage and display using the centralized engine."""
        from codes.dermatome_coverage import format_dermatome_coverage_as_html

        try:
            # Paths were already set via set_dermatome_map_paths() during scene init
            ok = self.scene.load_dermatome_mapper()
            if not ok:
                self.d_text.setPlainText(t("clinician_view_derm_load_fail"))
                return

            result = self.scene.compute_dermatome_coverage_result(self.session_manager)
            self.d_text.setHtml(format_dermatome_coverage_as_html(result))

        except Exception as e:
            self.logger.error(f"[ClinicianView] Dermatome panel failed: {e}")
            self.d_text.setPlainText(t("clinician_view_derm_fail"))

    # ------------------------------------------------------------------
    # Pain pattern analysis
    # ------------------------------------------------------------------
    def _collect_patient_data(self) -> dict:
        """
        Build the patient_data dict expected by analyze_pain().
        Merges questionnaire fields with dermatome names and severity_map
        derived from the current marking stats (works for both genders).

        Dermatomes are ranked by weighted_pain_burden (centralized coverage engine).
        Intensity label is descriptive only — not a clinical severity classification.
        """
        data = self.session_manager.data or {}
        questionnaire = dict(data.get("questionnaire") or {})

        dermatomes = []
        severity_map = {}

        if self.scene and self.scene.dermatome_mapper:
            try:
                # Pass the session manager so the gender-correct map is used if the
                # mapper ever needs to be (re)loaded (female vs male).
                result = self.scene.compute_dermatome_coverage_result(self.session_manager)
                top_n = result.get("overall", {}).get("top_n_displayed", 5)
                for row in result.get("dermatomes", []):
                    if row["rank"] > top_n:
                        continue
                    dermatomes.append(row["name"])
                    # Descriptive intensity label for AI context (not clinical diagnosis)
                    mli = row["mean_local_intensity"]
                    if mli >= 2.5:
                        label = "High intensity"
                    elif mli >= 1.5:
                        label = "Moderate intensity"
                    else:
                        label = "Low intensity"
                    severity_map[row["name"]] = label
            except Exception as e:
                self.logger.error(f"[ClinicianView] _collect_patient_data failed: {e}")

        questionnaire["dermatomes"] = dermatomes
        questionnaire["severity_map"] = severity_map
        return questionnaire

    def _on_analyze_clicked(self):
        """Run the pain analyzer and display the report in a styled dialog."""
        if not self.session_manager:
            return
        try:
            patient_data = self._collect_patient_data()
            report = analyze_pain(patient_data)
        except Exception as e:
            self.logger.error(f"[ClinicianView] Pain analysis error: {e}")
            report = f"Analysis failed:\n{e}"

        self._show_analysis_dialog(report)

    def _show_analysis_dialog(self, text: str):
        """Display the analysis report in a read-only modal dialog with Save and Close options."""
        dialog = QDialog(self)
        dialog.setWindowTitle(t("clinician_analyze_dialog_title"))
        dialog.resize(640, 500)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        text_edit = QTextEdit(dialog)
        text_edit.setReadOnly(True)
        text_edit.setPlainText(text)
        text_edit.setStyleSheet(
            "background-color: #f4f6f8; color: #1a1a1a;"
            "font-family: 'Courier New', Courier, monospace;"
            "font-size: 13px; border: 1px solid #ccc;"
            "border-radius: 6px; padding: 8px;"
        )
        layout.addWidget(text_edit, stretch=1)

        _BTN = "QPushButton { border-radius: 6px; font-size: 14px; font-weight: 500; padding: 6px 20px; }"

        save_btn = QPushButton(t("clinician_analyze_save_btn"))
        save_btn.setFixedHeight(40)
        save_btn.setStyleSheet(
            _BTN +
            "QPushButton { background-color: #00CED1; color: white; border: none; }"
            "QPushButton:hover { background-color: #0099A8; }"
            "QPushButton:disabled { background-color: #5a8a9a; color: rgba(255,255,255,0.5); }"
        )

        def _save_report():
            try:
                subject_info = (self.session_manager.data or {}).get("subject_info") or {}
                subject_id = subject_info.get("subject_id") or "unknown"
                folder_name = self.session_manager.current_session_folder
                if not folder_name:
                    save_btn.setText(t("clinician_analyze_no_folder"))
                    return
                session_folder = os.path.join("data", "sessions", str(subject_id), folder_name)
                os.makedirs(session_folder, exist_ok=True)
                report_path = os.path.join(session_folder, "pain_analysis_report.txt")
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(text)
                # Also append to the bilingual session summary
                if self.session_manager:
                    self.session_manager.append_analysis_to_summary(session_folder, text)
                save_btn.setText(t("clinician_analyze_saved"))
                save_btn.setEnabled(False)
                self.logger.info(f"[ClinicianView] Analysis report saved → {report_path}")
            except Exception as e:
                save_btn.setText(t("clinician_analyze_save_failed"))
                self.logger.error(f"[ClinicianView] Failed to save report: {e}")

        save_btn.clicked.connect(_save_report)

        close_btn = QPushButton(t("clinician_analyze_close_btn"))
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet(
            _BTN +
            "QPushButton { background-color: rgba(100,116,139,0.20); color: #1a1a1a;"
            " border: 1px solid rgba(100,116,139,0.35); }"
            "QPushButton:hover { background-color: rgba(100,116,139,0.35); }"
        )
        close_btn.clicked.connect(dialog.close)

        btn_row = QHBoxLayout()
        btn_row.addWidget(save_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        dialog.exec()

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _on_reset_camera_clicked(self):
        if self.scene:
            try:
                self.scene.reset_camera()
            except Exception as e:
                self.logger.error(f"[ClinicianView] Reset camera failed: {e}")

    def _on_toggle_model_view(self):
        if not self.scene:
            self._toggle_switch.set_on(not self._toggle_switch.is_on())
            return
        try:
            self.scene.toggle_model_view()
            self._showing_derm_view = not self._showing_derm_view
            self._derm_popup.hide()
            self._toggle_switch.set_on(self._showing_derm_view)
            color = "#BAE6FD" if self._showing_derm_view else "rgba(226, 234, 244, 0.55)"
            self._toggle_label.setStyleSheet(
                f"color: {color}; font-size: 12px; background: transparent; border: none;"
            )
        except Exception as e:
            self._toggle_switch.set_on(not self._toggle_switch.is_on())
            self.logger.error(f"[ClinicianView] Toggle model view failed: {e}")

    # ------------------------------------------------------------------
    # Text panels
    # ------------------------------------------------------------------
    def _refresh_text(self):
        self._back_btn.setText(t("clinician_view_back"))
        self._toggle_label.setText(t("clinician_view_dermatome_map"))
        self.compare_btn.setText(
            t("clinician_view_remove_compare") if self._comparison_active
            else t("clinician_view_compare_session") if self.scene
            else t("clinician_view_compare")
        )
        self._reset_btn.setText(t("clinician_view_reset_view"))
        self.analyze_btn.setText(t("clinician_view_analyze"))
        self._d_label.setText(t("clinician_view_dermatome_analysis"))
        self._q_label.setText(t("clinician_view_questionnaire"))
        self._c_label.setText(t("clinician_view_comments"))
        # Update title label with translated prefix, keeping the stored patient ID
        pid = getattr(self, "_current_patient_id", "—")
        self.id_label.setText(f"{t('clinician_view_patient_label')}  {pid}")
        # Re-render questionnaire in the new language
        if self.session_manager and self.session_manager.data:
            data = self.session_manager.data or {}
            self._populate_text_panels(
                data.get("questionnaire") or {},
                data.get("model_data") or {},
            )

    def _populate_text_panels(self, questionnaire: dict, model_data: dict):
        from codes.translations import lang_manager
        from codes.session_manager import format_questionnaire_for_display
        lang = lang_manager.get_language()

        q_formatted = format_questionnaire_for_display(questionnaire, lang)
        self.q_text.setPlainText(q_formatted if q_formatted else t("clinician_view_no_questionnaire"))

        comments = model_data.get("comments") or []
        if isinstance(comments, str):
            comments = [comments]
        if comments:
            self.c_text.setPlainText("\n".join(f"- {c}" for c in comments))
        else:
            self.c_text.setPlainText(t("clinician_view_no_comments"))

    # ------------------------------------------------------------------
