# codes/widgets/navigation_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QPushButton, QSlider
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont
from codes import scale

_BTN = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 255, 255, 0.14),
            stop:1 rgba(100, 116, 139, 0.10));
        color: #E2EAF4;
        font-size: 16px;
        font-weight: 500;
        border-radius: 8px;
        border: 1px solid rgba(148, 163, 184, 0.30);
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
"""

_SLIDER = """
    QSlider {
        background: transparent;
    }
    QSlider::groove:vertical {
        background: rgba(255, 255, 255, 0.12);
        width: 2px;
        border-radius: 1px;
    }
    QSlider::handle:vertical {
        background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
            fx:0.5, fy:0.5,
            stop:0 #FFFFFF,
            stop:0.4 #BAE6FD,
            stop:1 rgba(0, 206, 209, 0.60));
        height: 14px;
        width: 14px;
        margin: 0 -6px;
        border-radius: 7px;
        border: 1px solid rgba(255, 255, 255, 0.70);
        box-shadow: 0 0 8px rgba(186, 230, 253, 0.85), 0 0 3px rgba(0, 206, 209, 0.90);
    }
    QSlider::sub-page:vertical {
        background: transparent;
        border-radius: 1px;
    }
    QSlider::add-page:vertical {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(0, 206, 209, 0.20),
            stop:0.5 rgba(0, 206, 209, 0.90),
            stop:1 rgba(0, 206, 209, 0.20));
        border-radius: 1px;
    }
"""

# Touch-friendly button size (medical/tablet guideline: >=44-48px).
# Panel width must fit 3 D-pad buttons: 3×46 + 2×3 spacing + 2×8 margins = 160px
_PANEL_WIDTH = 162
_BTN_SZ = 46


class NavigationPanel(QWidget):
    """
    Right-side navigation panel:
      Zoom:  [+] / flexible slider (sub-page = cyan = more = zoomed in) / [-]
      D-pad: ▲ / ◀ ⟳ ▶ / ▼  (90-degree rotations + reset)
      Auto-rotate: ⏵/⏸ toggle (demo/presentation spin mode)

    Call set_renderer(scene) after RendererScene initialises.
    Call set_renderer(None) on screen hide.
    """

    # Emitted when the user toggles auto-rotate; True = start, False = stop
    auto_rotate_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.renderer = None
        self._slider_busy = False
        self._auto_rotating = False

        self.setFixedWidth(scale.sc(_PANEL_WIDTH))
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            NavigationPanel {
                background-color: rgba(15, 23, 42, 0.62);
                border-left: 1px solid rgba(148, 163, 184, 0.25);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(scale.sc(8), scale.sc(10), scale.sc(8), scale.sc(10))
        layout.setSpacing(scale.sc(4))

        # ── Zoom in ────────────────────────────────────────
        self.zoom_in_btn = self._btn("+")
        self.zoom_in_btn.clicked.connect(self._zoom_in)
        layout.addWidget(self.zoom_in_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── Slider (value 100 = zoomed in, sub-page grows = colored) ──
        self.zoom_slider = QSlider(Qt.Orientation.Vertical)
        self.zoom_slider.setRange(1, 100)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setMinimumHeight(scale.sc(60))
        self.zoom_slider.setFixedWidth(scale.sc(36))  # wider hit area for finger drags
        self.zoom_slider.setStyleSheet(_SLIDER)
        self.zoom_slider.valueChanged.connect(self._on_slider_changed)
        layout.addWidget(self.zoom_slider, stretch=1, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ── Zoom out ───────────────────────────────────────
        self.zoom_out_btn = self._btn("−")
        self.zoom_out_btn.clicked.connect(self._zoom_out)
        layout.addWidget(self.zoom_out_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        layout.addSpacing(scale.sc(10))

        # ── D-pad (3 cols × 3 rows, each cell _BTN_SZ × _BTN_SZ) ────
        grid = QGridLayout()
        grid.setSpacing(scale.sc(3))
        grid.setContentsMargins(0, 0, 0, 0)

        up  = self._btn("▲");  up.clicked.connect(lambda: self._rotate("up"))
        lft = self._btn("◀");  lft.clicked.connect(lambda: self._rotate("left"))
        rst = self._btn("⟳");  rst.clicked.connect(self._reset)
        rgt = self._btn("▶");  rgt.clicked.connect(lambda: self._rotate("right"))
        dn  = self._btn("▼");  dn.clicked.connect(lambda: self._rotate("down"))

        grid.addWidget(up,  0, 1)
        grid.addWidget(lft, 1, 0)
        grid.addWidget(rst, 1, 1)
        grid.addWidget(rgt, 1, 2)
        grid.addWidget(dn,  2, 1)

        layout.addLayout(grid)

        layout.addSpacing(scale.sc(8))

        # ── Auto-rotate (demo spin) ────────────────────────
        self.auto_rotate_btn = self._btn("▶")
        self.auto_rotate_btn.setCheckable(True)
        self.auto_rotate_btn.clicked.connect(self._on_auto_rotate_clicked)
        layout.addWidget(self.auto_rotate_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

    # ── Internal factory ──────────────────────────────────
    def _btn(self, text: str) -> QPushButton:
        b = QPushButton(text)
        b.setFixedSize(QSize(scale.sc(_BTN_SZ), scale.sc(_BTN_SZ)))
        b.setStyleSheet(_BTN)
        # Force identical pixel size for all glyphs so ◀▶ don't render larger than ▲▼
        f = QFont()
        f.setPixelSize(scale.sc(20))
        b.setFont(f)
        return b

    # ── Public API ────────────────────────────────────────
    def set_renderer(self, scene):
        self.renderer = scene
        if scene and scene.camera:
            self._sync_slider()

    # ── Zoom ──────────────────────────────────────────────
    def _zoom_in(self):
        if self.renderer:
            self.renderer.apply_zoom(1.2)
            self._sync_slider()

    def _zoom_out(self):
        if self.renderer:
            self.renderer.apply_zoom(0.83)
            self._sync_slider()

    def _on_slider_changed(self, value):
        """
        On Windows, Qt vertical slider has minimum at TOP:
          val=1   → handle at TOP   → add-page (below) = full  = fully blue  = most zoomed in
          val=50  → handle at MIDDLE → add-page = half             = default (30°)
          val=100 → handle at BOTTOM → add-page (below) = empty = no colour  = most zoomed out
        """
        if self._slider_busy or not self.renderer or not self.renderer.camera:
            return
        # val=1 → 10° (zoomed in),  val=50 → 30° (default),  val=100 → ~50° (zoomed out)
        angle = 30.0 + (50 - value) * 20.0 / 49.0
        angle = max(10.0, min(60.0, angle))
        self.renderer.camera.SetViewAngle(angle)
        self.renderer.renderer.ResetCameraClippingRange()
        self.renderer.render_window.Render()

    def _sync_slider(self):
        """Sync slider to current camera view angle (no feedback loop)."""
        if not self.renderer or not self.renderer.camera:
            return
        angle = max(10.0, min(60.0, self.renderer.camera.GetViewAngle()))
        # angle=10° → val=1 (zoomed in, top), angle=30° → val=50, angle=50° → val=99
        val = int(round(50.0 + (30.0 - angle) * 49.0 / 20.0))
        val = max(1, min(100, val))
        self._slider_busy = True
        self.zoom_slider.setValue(val)
        self._slider_busy = False

    # ── Rotation / Reset ──────────────────────────────────
    def _rotate(self, direction: str):
        if self.renderer:
            self.renderer.rotate_direction(direction)

    def _reset(self):
        if self.renderer:
            self.renderer.reset_camera()
            self._sync_slider()

    # ── Auto-rotate ───────────────────────────────────────
    def _on_auto_rotate_clicked(self):
        self._auto_rotating = self.auto_rotate_btn.isChecked()
        self.auto_rotate_btn.setText("■" if self._auto_rotating else "▶")
        self.auto_rotate_toggled.emit(self._auto_rotating)

    def stop_auto_rotate(self):
        """Programmatically stop auto-rotate (e.g. on screen hide)."""
        if self._auto_rotating:
            self._auto_rotating = False
            self.auto_rotate_btn.setChecked(False)
            self.auto_rotate_btn.setText("▶")
            self.auto_rotate_toggled.emit(False)
