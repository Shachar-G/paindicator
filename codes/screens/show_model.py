# codes/screens/show_model.py
# All comments are in English only.

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QButtonGroup
from PyQt6.QtCore import Qt, QTimer, QObject, QEvent, QPointF, QRectF
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor, QFont

from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from codes.renderer_scene import RendererScene
from codes.widgets.vtk_toolbar_widget import VTKToolBar
from codes.widgets.navigation_panel import NavigationPanel


# ---------------------------------------------------------------------------
# Input diagnostics (TEMPORARY)
# ---------------------------------------------------------------------------
# Logs how pen / touch / mouse events actually arrive on the target tablet
# (Chuwi UBook X Pro 13 + GOOJODOQ stylus) so input tuning can be data-driven.
# This changes NO behavior — it only writes to input_diag.log in the working
# directory (next to app.exe). Set INPUT_DIAG = False to disable, or remove this
# block once tuning is locked.
# Touch interaction is now solved (touch delivery + synthesized-mouse suppression
# + rotation direction), so diagnostics are disabled for production.
INPUT_DIAG = False

_input_diag_logger = None


def _diag_log(msg: str):
    """Append a line to input_diag.log. No-op if disabled or if logging fails."""
    if not INPUT_DIAG:
        return
    global _input_diag_logger
    try:
        if _input_diag_logger is None:
            import os as _os
            lg = logging.getLogger("input_diag")
            lg.setLevel(logging.DEBUG)
            lg.propagate = False  # keep diagnostics out of the root/basicConfig logs
            if not lg.handlers:
                fh = logging.FileHandler(
                    _os.path.join(_os.getcwd(), "input_diag.log"), encoding="utf-8"
                )
                fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
                lg.addHandler(fh)
            _input_diag_logger = lg
        _input_diag_logger.debug(msg)
    except Exception:
        pass


class _AppTouchObserver(QObject):
    """
    TEMPORARY diagnostics — application-wide observer.

    Logs any Touch/Tablet event seen ANYWHERE in the app (not just on the VTK
    widget) and never consumes it (always returns False). This tells us whether
    Qt produces touch events at all: if finger input only ever shows up as MOUSE,
    the touch is being promoted to mouse at the OS/Qt-platform level before any
    QTouchEvent is created.
    """

    def eventFilter(self, obj, event):
        try:
            t = event.type()
            T = QEvent.Type
            if t in (T.TouchBegin, T.TouchUpdate, T.TouchEnd,
                     T.TabletPress, T.TabletMove, T.TabletRelease):
                tname = t.name if hasattr(t, "name") else str(t)
                _diag_log(f"APPLEVEL {tname} on={type(obj).__name__}")
        except Exception:
            pass
        return False  # never consume — purely observational


# ---------------------------------------------------------------------------
# Touch event filter — intercepts touch/tablet events for the VTK widget
# ---------------------------------------------------------------------------

def _is_pen_touch(pts) -> bool:
    """Return True if the first touch point comes from a stylus/pen."""
    try:
        from PyQt6.QtGui import QPointingDevice
        return bool(pts) and pts[0].pointerType() == QPointingDevice.PointerType.Pen
    except Exception:
        return False


class _VTKTouchFilter(QObject):
    """
    Qt event filter installed on the VTK widget.

    Gesture rules:
    - 1 finger, VIEW mode  : rotate model (azimuth + elevation)
    - 1 finger, MARK/ERASE : finger painting (same inject API as stylus)
    - 2 fingers             : pinch=zoom, midpoint=pan, twist=azimuth rotation
    - Stylus (TabletEvent)  : paint/erase via inject API (unchanged)
    - Mouse                 : passed through to VTK (unchanged)

    All touch events are consumed so VTK never generates conflicting
    synthetic mouse events from them.
    """

    def __init__(self, screen, parent=None):
        super().__init__(parent)
        self._s = screen  # ShowModelScreen reference
        self._diag_move_count = 0  # sampler for move/update diagnostics (see _diag_event)

    def eventFilter(self, obj, event):
        etype = event.type()

        # Diagnostics only — logs the event, never changes dispatch behavior.
        if INPUT_DIAG:
            self._diag_event(obj, event, etype)

        # ---- TOUCH (finger or stylus delivered as touch) ----
        if etype in (QEvent.Type.TouchBegin, QEvent.Type.TouchUpdate, QEvent.Type.TouchEnd):
            pts = event.points()
            is_pen = _is_pen_touch(pts)
            style = (self._s.scene.interactor_style
                     if self._s.scene and self._s.scene.interactor_style else None)

            if etype == QEvent.Type.TouchBegin:
                if is_pen and style:
                    pos = pts[0].position()
                    style.inject_paint_begin(int(pos.x()), int(pos.y()))
                elif len(pts) == 1:
                    mode = style.mode if style else "VIEW"
                    if mode in ("MARK", "ERASE") and style:
                        # MARK/ERASE: 1 finger paints, never moves the model
                        pos = pts[0].position()
                        style.inject_paint_begin(int(pos.x()), int(pos.y()))
                        self._s._finger_painting = True
                    else:
                        # VIEW: 1 finger rotates
                        self._s.touch_manager.handle_touch_begin(event)
                        self._s._finger_rotating = True
                else:
                    # 2+ fingers: start navigation gesture
                    self._s.touch_manager.handle_touch_begin(event)
                return True  # consume ALL — VTK must not see any touch events

            elif etype == QEvent.Type.TouchUpdate:
                if is_pen and style:
                    pos = pts[0].position()
                    if not style._left_button_down:
                        style.inject_paint_begin(int(pos.x()), int(pos.y()))
                    else:
                        style.inject_paint_move(int(pos.x()), int(pos.y()))
                elif len(pts) == 1:
                    if self._s._finger_painting and style:
                        # Continue painting stroke
                        pos = pts[0].position()
                        style.inject_paint_move(int(pos.x()), int(pos.y()))
                    elif self._s._finger_rotating:
                        # VIEW mode: rotate from 1-finger drag
                        tm = self._s.touch_manager
                        tm.handle_touch_update(event)
                        if self._s.scene and (tm.last_rotation_dx or tm.last_rotation_dy):
                            self._s.scene.apply_touch_rotation(
                                tm.last_rotation_dx, tm.last_rotation_dy)
                else:
                    # 2+ fingers: zoom + pan + twist rotation
                    # Guard: don't navigate mid-painting stroke
                    if not self._s._finger_painting:
                        tm = self._s.touch_manager
                        tm.handle_touch_update(event)
                        if self._s.scene:
                            if tm.last_pinch_scale != 1.0:
                                self._s.scene.apply_zoom(tm.last_pinch_scale)
                            if tm.last_pan_dx or tm.last_pan_dy:
                                self._s.scene.apply_pan(tm.last_pan_dx, tm.last_pan_dy)
                            if tm.last_twist_deg:
                                # Convert twist degrees → pixel-equivalent for apply_touch_rotation
                                # (sensitivity = 0.3 deg/px → 1° twist = 1° azimuth rotation)
                                self._s.scene.apply_touch_rotation(tm.last_twist_deg / 0.3, 0)
                return True

            elif etype == QEvent.Type.TouchEnd:
                if is_pen and style:
                    style.inject_paint_end()
                elif self._s._finger_painting:
                    if style:
                        style.inject_paint_end()
                    self._s._finger_painting = False
                elif self._s._finger_rotating:
                    self._s.touch_manager.handle_touch_end(event)
                    self._s._finger_rotating = False
                else:
                    self._s.touch_manager.handle_touch_end(event)
                return True

        # ---- STYLUS (proper QTabletEvent path) ----
        elif etype == QEvent.Type.TabletPress:
            if self._s.scene and self._s.scene.interactor_style:
                pos = event.position()
                self._s.scene.interactor_style.inject_paint_begin(int(pos.x()), int(pos.y()))
            return True

        elif etype == QEvent.Type.TabletMove:
            if self._s.scene and self._s.scene.interactor_style:
                pos = event.position()
                style = self._s.scene.interactor_style
                if not style._left_button_down and event.pressure() > 0:
                    style.inject_paint_begin(int(pos.x()), int(pos.y()))
                elif style._left_button_down:
                    style.inject_paint_move(int(pos.x()), int(pos.y()))
            return True

        elif etype == QEvent.Type.TabletRelease:
            if self._s.scene and self._s.scene.interactor_style:
                self._s.scene.interactor_style.inject_paint_end()
            return True

        # ---- MOUSE ----
        # Windows promotes every finger touch into a SYNTHESIZED mouse event in
        # addition to the QTouchEvent. We already handle all touch ourselves
        # (paint + gestures via TouchManager), so if these synthetic mouse events
        # also reach VTK the model is driven twice — VTK's raw trackball fights our
        # smoothed touch path (shaky/jumpy rotation) and the single jumping cursor
        # breaks two-finger pan/zoom. Swallow any mouse event that is NOT from a
        # real mouse; let a genuine USB mouse through (desktop/dev testing).
        elif etype in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease,
                       QEvent.Type.MouseMove, QEvent.Type.MouseButtonDblClick):
            try:
                from PyQt6.QtGui import QInputDevice
                if event.deviceType() != QInputDevice.DeviceType.Mouse:
                    return True  # synthesized-from-touch — consume so VTK never sees it
            except Exception:
                pass
            return False  # real mouse — pass through to VTK

        # Everything else (keyboard, wheel …) passes through to VTK unchanged
        return False

    # ------------------------------------------------------------------
    # Input diagnostics (TEMPORARY) — log-only, never alters dispatch.
    # ------------------------------------------------------------------
    def _diag_event(self, obj, event, etype):
        """
        Record how each pen/touch/mouse event arrives so input behavior can be
        tuned from real device data. Begin/End/Press/Release are logged in full;
        Move/Update are sampled (every 10th) to avoid flooding the log.
        """
        try:
            T = QEvent.Type
            try:
                dpr = float(obj.devicePixelRatioF())
            except Exception:
                dpr = -1.0

            # ---- Touch (finger, or pen delivered as touch) ----
            if etype in (T.TouchBegin, T.TouchUpdate, T.TouchEnd):
                if etype == T.TouchUpdate:
                    self._diag_move_count += 1
                    if self._diag_move_count % 10 != 0:
                        return
                name = {T.TouchBegin: "TouchBegin", T.TouchUpdate: "TouchUpdate",
                        T.TouchEnd: "TouchEnd"}[etype]
                pts = event.points()
                n = len(pts)
                is_pen = _is_pen_touch(pts)
                ptype = pressure = pos = "?"
                if pts:
                    p0 = pts[0]
                    try:
                        ptype = str(p0.pointerType())
                    except Exception:
                        pass
                    try:
                        pressure = f"{p0.pressure():.3f}"
                    except Exception:
                        pass
                    try:
                        pos = f"({p0.position().x():.1f},{p0.position().y():.1f})"
                    except Exception:
                        pass
                _diag_log(f"TOUCH {name} n={n} is_pen={is_pen} ptype={ptype} "
                          f"pressure={pressure} pos={pos} dpr={dpr:.3f}")

            # ---- Tablet (proper QTabletEvent path) ----
            elif etype in (T.TabletPress, T.TabletMove, T.TabletRelease):
                if etype == T.TabletMove:
                    self._diag_move_count += 1
                    if self._diag_move_count % 10 != 0:
                        return
                name = {T.TabletPress: "TabletPress", T.TabletMove: "TabletMove",
                        T.TabletRelease: "TabletRelease"}[etype]
                pressure = pos = ptype = dtype = "?"
                try:
                    pressure = f"{event.pressure():.3f}"
                except Exception:
                    pass
                try:
                    pos = f"({event.position().x():.1f},{event.position().y():.1f})"
                except Exception:
                    pass
                try:
                    ptype = str(event.pointerType())
                except Exception:
                    pass
                try:
                    dtype = str(event.deviceType())
                except Exception:
                    pass
                _diag_log(f"TABLET {name} ptype={ptype} dtype={dtype} "
                          f"pressure={pressure} pos={pos} dpr={dpr:.3f}")

            # ---- Mouse (desktop testing, or pen reported as mouse) ----
            elif etype in (T.MouseButtonPress, T.MouseMove, T.MouseButtonRelease):
                if etype == T.MouseMove:
                    self._diag_move_count += 1
                    if self._diag_move_count % 10 != 0:
                        return
                name = {T.MouseButtonPress: "MousePress", T.MouseMove: "MouseMove",
                        T.MouseButtonRelease: "MouseRelease"}[etype]
                pos = dtype = "?"
                try:
                    pos = f"({event.position().x():.1f},{event.position().y():.1f})"
                except Exception:
                    pass
                try:
                    dtype = str(event.deviceType())
                except Exception:
                    pass
                _diag_log(f"MOUSE {name} pos={pos} dtype={dtype} dpr={dpr:.3f}")
        except Exception:
            pass


class _GestureHelpOverlay(QWidget):
    """Translucent, tap-to-close overlay showing standard touch-gesture hints.

    Built as a frameless top-level Tool window (like the mark-palette popup) so it
    renders ABOVE the native VTK render window — a normal child overlay would be
    hidden behind it. Call show_over(vtk_widget) to position it over the 3D view.
    """

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)

    def show_over(self, widget):
        """Cover the given widget's on-screen rect, then show on top."""
        try:
            tl = widget.mapToGlobal(widget.rect().topLeft())
            self.setGeometry(tl.x(), tl.y(), max(widget.width(), 1), max(widget.height(), 1))
        except Exception:
            pass
        self.show()
        self.raise_()

    # Any tap / key / touch closes the overlay
    def mousePressEvent(self, event):
        self.hide()

    def keyPressEvent(self, event):
        self.hide()

    def event(self, ev):
        if ev.type() == QEvent.Type.TouchBegin:
            self.hide()
            return True
        return super().event(ev)

    # ---- drawing helpers ----
    def _finger(self, p, cx, cy, r=12):
        p.setBrush(QColor(0, 206, 209, 235))
        p.setPen(QPen(QColor(255, 255, 255, 210), 2))
        p.drawEllipse(QPointF(cx, cy), float(r), float(r))

    def _arrow(self, p, x1, y1, x2, y2, head=9):
        import math
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        ang = math.atan2(y2 - y1, x2 - x1)
        for s in (1, -1):
            a = ang + s * math.radians(26)
            p.drawLine(QPointF(x2, y2),
                       QPointF(x2 - head * math.cos(a), y2 - head * math.sin(a)))

    def _darrow(self, p, x1, y1, x2, y2, head=9):
        """Double-headed (bi-directional) arrow: one line with a head at each end."""
        self._arrow(p, x1, y1, x2, y2, head)
        self._arrow(p, x2, y2, x1, y1, head)

    def _glyph_rotate(self, p, cx, cy):
        import math
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(186, 230, 253, 235), 3))
        rad = 24
        p.drawArc(QRectF(cx - rad, cy - rad, 2 * rad, 2 * rad), 45 * 16, 270 * 16)
        end = math.radians(315)
        ex, ey = cx + rad * math.cos(end), cy - rad * math.sin(end)
        # Arrowhead must point along the arc's (counter-clockwise) travel direction at
        # the endpoint, i.e. the screen-space tangent. The previous formula used an
        # unrelated angle, which rendered the head as a reversed/inverted wedge.
        tip_ang = math.atan2(-math.cos(end), -math.sin(end))
        for s in (1, -1):
            a = tip_ang + s * math.radians(26)
            p.drawLine(QPointF(ex, ey), QPointF(ex - 9 * math.cos(a), ey - 9 * math.sin(a)))
        self._finger(p, cx, cy, 11)

    def _glyph_zoom(self, p, cx, cy):
        p.setPen(QPen(QColor(186, 230, 253, 235), 3))
        # Single bi-directional arrow between the two fingers (zoom in / out).
        self._darrow(p, cx - 34, cy, cx + 34, cy)
        self._finger(p, cx - 46, cy, 11)
        self._finger(p, cx + 46, cy, 11)

    def _glyph_move(self, p, cx, cy):
        p.setPen(QPen(QColor(186, 230, 253, 235), 3))
        self._arrow(p, cx, cy - 8, cx, cy - 30)
        self._arrow(p, cx, cy + 8, cx, cy + 30)
        # The two fingers sit at cx +/- 11 (radius 10), so they reach to cx +/- 21.
        # Start the horizontal arrows beyond that so the finger circles don't cover them.
        self._arrow(p, cx - 24, cy, cx - 44, cy)
        self._arrow(p, cx + 24, cy, cx + 44, cy)
        self._finger(p, cx - 11, cy, 10)
        self._finger(p, cx + 11, cy, 10)

    def paintEvent(self, event):
        try:
            from codes.translations import lang_manager
            he = lang_manager.get_language() == "he"
        except Exception:
            he = False
        title = "מחוות מגע" if he else "Touch controls"
        footer = "הקש כדי לסגור" if he else "Tap anywhere to close"
        rows = [
            (self._glyph_rotate, ("סיבוב" if he else "Rotate"),
             ("אצבע אחת" if he else "one finger")),
            (self._glyph_zoom, ("זום" if he else "Zoom"),
             ("צביטה בשתי אצבעות" if he else "pinch with two fingers")),
            (self._glyph_move, ("הזזה" if he else "Move"),
             ("גרירה בשתי אצבעות" if he else "drag with two fingers")),
        ]

        W, H = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(8, 13, 23, 210))

        cw = min(int(W * 0.84), 600)
        ch = min(int(H * 0.88), 430)
        cx0 = (W - cw) // 2
        cy0 = (H - ch) // 2
        p.setBrush(QColor(17, 24, 39, 240))
        p.setPen(QPen(QColor(0, 206, 209, 110), 2))
        p.drawRoundedRect(QRectF(cx0, cy0, cw, ch), 18, 18)

        p.setPen(QColor(226, 234, 244))
        f = QFont(); f.setBold(True); f.setPointSize(15); p.setFont(f)
        p.drawText(QRectF(cx0, cy0 + 16, cw, 36),
                   int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter), title)

        top = cy0 + 70
        bottom = cy0 + ch - 50
        row_h = (bottom - top) / 3.0
        glyph_cx = cx0 + 84
        tx = cx0 + 156
        tw = cw - (tx - cx0) - 24
        for i, (glyph, lbl, sub) in enumerate(rows):
            ry = top + row_h * i + row_h / 2.0
            glyph(p, glyph_cx, ry)
            p.setPen(QColor(226, 234, 244))
            f.setBold(True); f.setPointSize(14); p.setFont(f)
            p.drawText(QRectF(tx, ry - 24, tw, 26),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), lbl)
            p.setPen(QColor(148, 163, 184))
            f.setBold(False); f.setPointSize(11); p.setFont(f)
            p.drawText(QRectF(tx, ry + 2, tw, 22),
                       int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), sub)

        p.setPen(QColor(148, 163, 184))
        f.setBold(False); f.setPointSize(11); p.setFont(f)
        p.drawText(QRectF(cx0, cy0 + ch - 42, cw, 26),
                   int(Qt.AlignmentFlag.AlignHCenter), footer)
        p.end()


class ShowModelScreen(QWidget):
    """
    Main screen responsible for displaying the 3D model (VTK)
    and connecting toolbar actions to the RendererScene logic.
    """

    def __init__(self, model_path: str = None, main_window=None, patient_data=None,
                 session_manager=None, parent=None):
        super().__init__(parent)
        # --- Context references ---
        self.main_window = main_window
        self.patient_data = patient_data
        self.session_manager = session_manager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model_path = model_path or ""

        # --- Scene / Toolbar ---
        self.scene: RendererScene = None
        from codes.touch_manager import TouchManager
        self.touch_manager = TouchManager(self)
        self._finger_painting: bool = False   # True while a 1-finger paint stroke is active
        self._finger_rotating: bool = False   # True while a 1-finger VIEW-mode rotation is active
        self.toolbar: VTKToolBar = None
        self._scene_initialized = False
        self._edit_mode = False   # True when editing an existing saved session
        self._gesture_help = None  # lazy translucent touch-gesture hints overlay

        # Auto-rotate (demo/presentation spin mode)
        self._auto_rotate_timer = QTimer(self)
        self._auto_rotate_timer.setInterval(16)   # ~60 fps; 0.5°/frame ≈ one rotation per 12 s
        self._auto_rotate_timer.timeout.connect(self._do_auto_rotate_step)

        # --- Layout setup ---
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 10)
        self.main_layout.setSpacing(0)
        self.setLayout(self.main_layout)

        # --- Inner container for VTK + toolbar ---
        self.scene_container = QWidget(self)
        self.scene_layout = QVBoxLayout(self.scene_container)
        self.scene_layout.setContentsMargins(0, 0, 0, 0)
        self.scene_layout.setSpacing(0)

        # --- Set light blue background for the container (safe for VTK) ---
        self.scene_container.setStyleSheet("background-color: #8A99AB;")

        # --- Toolbar (TOP) ---
        self.toolbar = VTKToolBar(self.scene_container)
        self.scene_layout.addWidget(self.toolbar, alignment=Qt.AlignmentFlag.AlignTop)

        # --- VTK Widget + Navigation panel (side by side, fill remaining space) ---
        self.vtk_widget = QVTKRenderWindowInteractor(self.scene_container)
        self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.vtk_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Prevent VTK's render-window size from being used as a minimum size hint,
        # which would cause the main window to grow when layouts recalculate.
        self.vtk_widget.setMinimumSize(1, 1)

        self.nav_panel = NavigationPanel(self.scene_container)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)
        content_row.addWidget(self.vtk_widget, stretch=1)
        content_row.addWidget(self.nav_panel)
        self.scene_layout.addLayout(content_row, stretch=1)

        # Enable touch events and install our event filter (replaces monkey-patch).
        # The filter consumes ALL touch/tablet events so VTK never sees them and
        # cannot generate conflicting synthetic mouse events.
        self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
        self._vtk_touch_filter = _VTKTouchFilter(self)
        self.vtk_widget.installEventFilter(self._vtk_touch_filter)

        # TEMP diagnostics: app-wide observer to confirm whether Qt produces touch
        # events anywhere (see _AppTouchObserver). Never consumes events.
        if INPUT_DIAG:
            try:
                from PyQt6.QtWidgets import QApplication
                self._app_touch_observer = _AppTouchObserver(self)
                QApplication.instance().installEventFilter(self._app_touch_observer)
            except Exception as e:
                self.logger.error(f"[ShowModelScreen] Failed to install app touch observer: {e}")

        # Add the container to the main layout
        self.main_layout.addWidget(self.scene_container, stretch=1)

        # --- Toolbar connections ---
        self._setup_toolbar_connections()

    # ----------------------------------------------------------------------
    # Toolbar connections setup
    # ----------------------------------------------------------------------
    def _setup_toolbar_connections(self):
        """Connect toolbar buttons to scene actions."""
        # All modes are checkable
        self.toolbar.view_btn.setCheckable(True)
        self.toolbar.mark_btn.setCheckable(True)
        self.toolbar.erase_btn.setCheckable(True)

        # Group mutually exclusive modes
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.toolbar.view_btn)
        self.mode_group.addButton(self.toolbar.mark_btn)
        self.mode_group.addButton(self.toolbar.erase_btn)

        # Connect actions
        self.toolbar.view_btn.clicked.connect(lambda: self._on_mode_toggle("VIEW"))
        self.toolbar.mark_btn.clicked.connect(lambda: self._on_mode_toggle("MARK"))
        self.toolbar.undo_btn.clicked.connect(self._on_undo_clicked)
        self.toolbar.erase_btn.clicked.connect(lambda: self._on_mode_toggle("ERASE"))
        self.toolbar.reset_btn.clicked.connect(self._on_reset_camera)
        self.toolbar.clear_btn.clicked.connect(self._on_clear_all)
        self.toolbar.session_saved.connect(self._on_session_saved)
        self.toolbar.help_requested.connect(self._show_gesture_help)
        # Re-color the MARK cursor whenever the user picks a different paint level
        self.toolbar.mark_palette_popup.levelSelected.connect(
            lambda lvl: self._update_vtk_cursor("MARK", level=lvl)
        )

        # Default mode
        self.toolbar.view_btn.setChecked(True)
        self.logger.info("[ShowModelScreen] Toolbar connected with VIEW as default.")

    # ----------------------------------------------------------------------
    # Delayed initialization (safe VTK load after the screen is visible)
    # ----------------------------------------------------------------------
    def showEvent(self, event):
        """Called automatically when this widget becomes visible."""
        super().showEvent(event)

        if not self._scene_initialized:
            try:
                # Pull the selected model path from MainWindow if available
                if self.main_window and hasattr(self.main_window, "selected_model_path"):
                    self.model_path = self.main_window.selected_model_path

                # Initialize VTK only once (now the widget is visible)
                model_info = getattr(self.main_window, "selected_model_info", {}) or {}
                initial_azimuth = model_info.get("initial_azimuth", 0)
                self.scene = RendererScene(self.vtk_widget, self.model_path,
                                           session_manager=self.session_manager,
                                           initial_azimuth=initial_azimuth)
                self.toolbar.renderer = self.scene
                # Keep the actual paint level in sync with what the palette shows,
                # so the selected color and the painted color always match on
                # (re-)entry (a fresh interactor otherwise silently defaults to 1).
                try:
                    lvl = self.toolbar.mark_palette_popup.group.checkedId()
                    if lvl in (1, 2, 3):
                        self.scene.set_mark_level(lvl)
                except Exception as e:
                    self.logger.error(f"[ShowModelScreen] mark-level sync failed: {e}")
                self.nav_panel.set_renderer(self.scene)
                self.nav_panel.auto_rotate_toggled.connect(self._on_auto_rotate_toggled)
                # Sync slider on mouse-wheel zoom (VTK-level callback, reliable on all platforms)
                if self.scene.interactor_style:
                    self.scene.interactor_style._on_zoom_changed = self.nav_panel._sync_slider
                self._scene_initialized = True

                # In edit mode, restore existing paint marks from the loaded session
                if self._edit_mode and self.session_manager and self.session_manager.data:
                    model_data = self.session_manager.data.get("model_data") or {}
                    if model_data.get("paint_v2"):
                        try:
                            self.scene.apply_saved_marks(model_data)
                            self.logger.info("[ShowModelScreen] Restored existing marks (edit mode).")
                        except Exception as e:
                            self.logger.error(f"[ShowModelScreen] Failed to restore marks: {e}")

                # Give keyboard focus to VTK so camera navigation works immediately
                self.vtk_widget.setFocus()

                # Set default cursor (VIEW mode)
                self._update_vtk_cursor("VIEW")

                self.logger.info("[ShowModelScreen] RendererScene initialized on showEvent.")
            except Exception as e:
                self.logger.error(f"[ShowModelScreen] Failed to initialize RendererScene: {e}")

        # Force touch registration on the native VTK window.
        # QVTKRenderWindowInteractor creates a WA_PaintOnScreen native window inside
        # its __init__ (before we set WA_AcceptTouchEvents). On Windows that native
        # window can fail to register for touch, so the OS promotes finger input to
        # synthesized MOUSE events and NO QTouchEvent is ever generated (confirmed via
        # input_diag.log). Toggling the attribute now — after the window is realized
        # and shown — re-triggers Qt's touch registration. Mouse behavior is unaffected.
        try:
            self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, False)
            self.vtk_widget.setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents, True)
            self.logger.info("[ShowModelScreen] Re-registered VTK widget for touch events.")
        except Exception as e:
            self.logger.error(f"[ShowModelScreen] Touch re-registration failed: {e}")

    # ----------------------------------------------------------------------
    # Toolbar action handlers
    # ----------------------------------------------------------------------
    def _on_mode_toggle(self, mode: str):
        """Toggle between MARK, ERASE, and VIEW modes."""
        if not self.scene:
            return

        # Determine target mode
        btn = {
            "VIEW": self.toolbar.view_btn,
            "MARK": self.toolbar.mark_btn,
            "ERASE": self.toolbar.erase_btn
        }.get(mode)

        if not btn:
            return

        if btn.isChecked():
            self.scene.set_mode(mode)
            self._update_vtk_cursor(mode)
        else:
            self.scene.set_mode("VIEW")
            self.toolbar.view_btn.setChecked(True)
            self._update_vtk_cursor("VIEW")

        self.logger.debug(f"[ShowModelScreen] Mode toggled → {mode if btn.isChecked() else 'VIEW'}")

    def _on_reset_camera(self):
        """Reset camera position and orientation."""
        if self.scene:
            self.scene.reset_camera()
            self.logger.debug("[ShowModelScreen] Camera reset.")

    def _on_clear_all(self):
        if self.scene:
            self.scene.clear_all()
            self.toolbar.view_btn.setChecked(True)
            self._update_vtk_cursor("VIEW")
            self.logger.debug("[ShowModelScreen] Clear all executed and returned to VIEW mode.")

    # Optional: handle Undo from topbar/back button if needed
    def undo_last_action(self):
        if self.scene:
            self.scene.undo()
            self.logger.debug("[ShowModelScreen] Undo action triggered.")

    # ------------------------------------------------------------------
    # Custom cursor per interaction mode
    # ------------------------------------------------------------------
    # Paint level → cursor color (matches COLORS in vtk_interactor_custom.py)
    _LEVEL_COLORS = {
        1: QColor(255, 255, 0, 230),   # yellow
        2: QColor(255, 165, 0, 230),   # orange
        3: QColor(255, 0,   0, 230),   # red
    }

    def _update_vtk_cursor(self, mode: str, level: int = None):
        """Update the VTK widget cursor to reflect the active interaction mode.

        level — paint level (1/2/3) used to colorize the MARK circle.
                If None, reads current_mark_level from the active scene.
        """
        mode = (mode or "VIEW").upper()

        if mode == "VIEW":
            self.vtk_widget.setCursor(Qt.CursorShape.OpenHandCursor)
            return

        if mode == "MARK":
            if level is None:
                level = (self.scene.interactor_style.current_mark_level
                         if self.scene and self.scene.interactor_style else 1)
            color = self._LEVEL_COLORS.get(level, QColor(255, 255, 255, 220))

            size = 44
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(2, 2, size - 4, size - 4)
            # Center dot in the same color for precision aiming
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            mid = size // 2
            p.drawEllipse(mid - 2, mid - 2, 4, 4)
            p.end()
            self.vtk_widget.setCursor(QCursor(pix, size // 2, size // 2))
            return

        if mode == "ERASE":
            # Circle with X inside — same circular shape as MARK for easy aiming,
            # red color and X make it unambiguous that this is erase mode.
            size = 36
            pix = QPixmap(size, size)
            pix.fill(Qt.GlobalColor.transparent)
            p = QPainter(pix)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            erase_col = QColor(255, 80, 80, 230)
            p.setPen(QPen(erase_col, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(2, 2, size - 4, size - 4)
            # X lines inside the circle
            m = 10
            p.drawLine(m, m, size - m, size - m)
            p.drawLine(size - m, m, m, size - m)
            p.end()
            self.vtk_widget.setCursor(QCursor(pix, size // 2, size // 2))
            return

    # ------------------------------------------------------------------
    # Auto-rotate (demo / presentation spin mode)
    # ------------------------------------------------------------------
    def _on_auto_rotate_toggled(self, active: bool):
        if active:
            self._auto_rotate_timer.start()
            # Disable painting and navigation controls while spinning
            for btn in [self.toolbar.mark_btn, self.toolbar.erase_btn,
                        self.toolbar.undo_btn, self.toolbar.clear_btn, self.toolbar.save_btn]:
                btn.setEnabled(False)
            for btn in [self.nav_panel.zoom_in_btn, self.nav_panel.zoom_out_btn,
                        self.nav_panel.zoom_slider]:
                btn.setEnabled(False)
            if self.scene:
                self.scene.set_mode("VIEW")
                self.toolbar._switch_mode("VIEW")
        else:
            self._auto_rotate_timer.stop()
            for btn in [self.toolbar.mark_btn, self.toolbar.erase_btn,
                        self.toolbar.undo_btn, self.toolbar.clear_btn, self.toolbar.save_btn]:
                btn.setEnabled(True)
            for btn in [self.nav_panel.zoom_in_btn, self.nav_panel.zoom_out_btn,
                        self.nav_panel.zoom_slider]:
                btn.setEnabled(True)

    def _do_auto_rotate_step(self):
        if self.scene:
            self.scene.rotate_azimuth_step(0.3)

    # ------------------------------------------------------------------
    def hideEvent(self, event):
        """Called automatically when this screen is hidden (navigating away)."""
        super().hideEvent(event)
        self.nav_panel.stop_auto_rotate()

        # --- Close mark palette popup if it's open ---
        try:
            if hasattr(self, "toolbar") and hasattr(self.toolbar, "mark_palette_popup"):
                if self.toolbar.mark_palette_popup.isVisible():
                    self.toolbar.mark_palette_popup.close()
        except Exception as e:
            self.logger.error(f"[ShowModelScreen] Error while closing mark palette popup: {e}")

        # Close the gesture-help overlay if it is open
        try:
            if self._gesture_help is not None and self._gesture_help.isVisible():
                self._gesture_help.hide()
        except Exception:
            pass

        # Restore default cursor before VTK teardown
        try:
            self.vtk_widget.unsetCursor()
        except Exception:
            pass

        # Softly release the VTK interactor to avoid native crashes
        try:
            if self.scene:
                # Try to disable interaction cleanly (no TerminateApp / Finalize!)
                interactor = getattr(self.scene, "interactor", None)
                if interactor is not None:
                    self.logger.info("[ShowModelScreen] Softly releasing VTK interactor before leaving screen.")
                    try:
                        interactor.Disable()
                    except Exception as e:
                        self.logger.warning(f"[ShowModelScreen] interactor.Disable() failed: {e}")

                # Drop references so Python/Qt can clean up safely
                self.nav_panel.set_renderer(None)
                self.scene.interactor = None
                self.scene.render_window = None
                self.scene = None
                self._scene_initialized = False  # allow re-initialization on return

        except Exception as e:
            self.logger.error(f"[ShowModelScreen] Error while releasing VTK interactor: {e}")

        # --- Mark session as closed when leaving this screen ---
        # Ensures the next save creates a fresh session folder.
        try:
            if self.session_manager:
                self.session_manager.close_session()
                self.logger.info("[ShowModelScreen] current_session_folder reset (session closed).")
        except Exception as e:
            self.logger.error(f"[ShowModelScreen] Failed closing session: {e}")

    def _on_session_saved(self):
        """Called after the toolbar successfully saves — navigate back to home screen."""
        self._saved_since_paint = True
        if self.main_window:
            self.main_window.navigate_to("role_selection", _push_history=False)

    # ------------------------------------------------------------------
    # Unsaved-changes guard (queried by MainWindow.navigate_to)
    # ------------------------------------------------------------------
    def _has_unsaved_paint(self) -> bool:
        """
        True if the user performed paint/erase actions in this visit that have
        not been saved yet. Uses the undo stack (only user strokes push there),
        so paint restored from a session in edit mode does NOT count as dirty.
        """
        if getattr(self, "_saved_since_paint", False):
            return False
        if not self.scene:
            return False
        style = getattr(self.scene, "interactor_style", None)
        if style is None:
            return False
        return bool(getattr(style, "undo_stack", None))

    def confirm_leave(self) -> bool:
        """
        Ask the user to confirm leaving when there are unsaved pain markings.
        Returns True to allow navigation, False to stay on this screen.
        """
        if not self._has_unsaved_paint():
            return True
        try:
            from PyQt6.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self, "Unsaved Markings",
                "You have unsaved pain markings.\n"
                "If you leave now, they will be lost.\n\n"
                "Leave without saving?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return reply == QMessageBox.StandardButton.Yes
        except Exception as e:
            self.logger.warning(f"[ShowModelScreen] confirm_leave dialog failed: {e}")
            return True  # never trap the user on a broken dialog

    def _show_gesture_help(self):
        """Show the translucent touch-gesture hints overlay over the 3D view."""
        try:
            if self._gesture_help is None:
                self._gesture_help = _GestureHelpOverlay(self)
            self._gesture_help.show_over(self.vtk_widget)
        except Exception as e:
            self.logger.error(f"[ShowModelScreen] Failed to show gesture help: {e}")

    def _on_save_session(self):
        """Triggered when Save button is pressed."""
        try:
            if not self.scene:
                self.logger.warning("[ShowModelScreen] Scene not initialized, cannot save.")
                return

            if not hasattr(self.scene, "save_full_session"):
                self.logger.error("[ShowModelScreen] RendererScene missing save_full_session()")
                return

            # Use the integrated SessionManager (now contains ID, gender, clinician, etc.)
            self.scene.save_full_session(self.session_manager)
            self.logger.info("[ShowModelScreen] ✅ Full session saved successfully.")

        except Exception as e:
            self.logger.error(f"[ShowModelScreen] ❌ Failed to save full session: {e}")

    def on_load(self, **kwargs):
        self.subject_id = kwargs.get("subject_id", "")
        self.gender = kwargs.get("gender", "")
        self._edit_mode = kwargs.get("_edit_mode", False)
        self._saved_since_paint = False  # fresh visit — nothing saved yet
        self.logger.info(f"[ShowModelScreen] Loaded with subject_id={self.subject_id}, gender={self.gender}, edit_mode={self._edit_mode}")

    def _on_undo_clicked(self):
        """Undo last painting action (safe if history is empty)."""
        if self.scene:
            self.scene.undo()

    def reset_for_new_session(self):
        """
        Fully reset the model, toolbar, popup, and stored session data.
        Called whenever a NEW session begins.
        """
        self.logger.info("[ShowModelScreen] Resetting model for NEW session.")

        try:
            # Reset painting on the model
            if self.scene:
                self.scene.clear_all()

            # Reset SessionManager stored data
            if self.session_manager:
                md = self.session_manager.data.get("model_data", {})
                md["marks"] = {}
                md["comments"] = []

            # Reset toolbar stored comments and visual state
            if hasattr(self.toolbar, "clear_all_comments"):
                self.toolbar.clear_all_comments()
            if hasattr(self.toolbar, "reset_state"):
                self.toolbar.reset_state()

            # Reset popup state if exists
            if hasattr(self.toolbar, "comment_popup") and self.toolbar.comment_popup:
                try:
                    if hasattr(self.toolbar.comment_popup, "clear_all"):
                        self.toolbar.comment_popup.clear_all()
                    self.toolbar.comment_popup.hide()
                except Exception:
                    pass

        except Exception as e:
            self.logger.error(f"[ShowModelScreen] reset_for_new_session failed: {e}")
