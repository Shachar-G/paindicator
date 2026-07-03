from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QButtonGroup, QAbstractButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen
from codes.widgets.comment_popup import CommentPopup
from codes.config import get_base_icons_path
from codes.translations import t, lang_manager
from codes import scale, theme
import os


class VTKToolBar(QWidget):
    """Toolbar for VTK 3D tools: View, Mark, Erase, Undo, Reset, Clear, Save, Comments."""

    # Emitted after a session is successfully saved
    session_saved = pyqtSignal()
    # Emitted when the user taps the "?" help button (screen shows the gesture overlay)
    help_requested = pyqtSignal()

    def __init__(self, renderer=None, parent=None):
        super().__init__(parent)
        self.renderer = renderer
        self.comments = []
        self.session_comments = []

        # State guards
        self._current_mode = "VIEW"                 # VIEW | MARK | ERASE
        self._allow_programmatic_switch = False     # Only True inside _switch_mode calls

        # UI shell — height sized for comfortable touch targets (>=48px pills)
        self.setFixedHeight(scale.sc(62))
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("""
            VTKToolBar {
                background-color: rgba(15, 23, 42, 0.82);
                border-bottom: 1px solid rgba(148, 163, 184, 0.22);
            }
        """)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        main_row = QHBoxLayout()
        main_row.setContentsMargins(scale.sc(10), 0, scale.sc(10), 0)
        main_row.setSpacing(scale.sc(12))
        outer.addLayout(main_row)

        # Left controls
        left_row = QHBoxLayout()
        left_row.setSpacing(scale.sc(12))
        main_row.addLayout(left_row, stretch=1)
        main_row.addStretch(1)

        # --- Styling helper ---
        def style_btn(b: QPushButton, persistent=False):
            """Apply uniform glassmorphism style; persistent=True keeps pressed highlight.
            Buttons are sized as touch targets (>=44-48px tall, scaled)."""
            b.setCheckable(persistent)
            b.setProperty("persistent", persistent)
            if b.text():
                b.setText(" " + b.text())
            b.setMinimumHeight(scale.sc(46))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(255, 255, 255, 0.14),
                        stop:1 rgba(100, 116, 139, 0.10));
                    color: #E2EAF4;
                    font-size: {scale.sc(14)}px;
                    font-weight: 500;
                    border-radius: 8px;
                    border: 1px solid rgba(148, 163, 184, 0.30);
                    padding: {scale.sc(8)}px {scale.sc(14)}px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 206, 209, 0.32),
                        stop:1 rgba(0, 206, 209, 0.16));
                    border: 1px solid rgba(0, 206, 209, 0.85);
                    color: #FFFFFF;
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 206, 209, 0.52),
                        stop:1 rgba(0, 206, 209, 0.32));
                    border: 1px solid {theme.PRIMARY};
                    color: #FFFFFF;
                }}
                QPushButton:checked {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 rgba(0, 206, 209, 0.62),
                        stop:1 rgba(0, 206, 209, 0.38));
                    border: 2px solid {theme.PRIMARY};
                    color: #FFFFFF;
                    font-weight: 700;
                }}
            """)

        # --- Mode buttons (persistent highlight) ---
        self.view_btn = QPushButton(t("toolbar_view"))
        style_btn(self.view_btn, persistent=True)
        self.mark_btn = QPushButton(t("toolbar_mark"))
        style_btn(self.mark_btn, persistent=True)
        self.erase_btn = QPushButton(t("toolbar_erase"))
        style_btn(self.erase_btn, persistent=True)

        # --- Action buttons (momentary: not checkable) ---
        self.undo_btn = QPushButton(t("toolbar_undo"))
        style_btn(self.undo_btn)
        self.reset_btn = QPushButton(t("toolbar_reset_camera"))
        style_btn(self.reset_btn)
        self.clear_btn = QPushButton(t("toolbar_clear"))
        style_btn(self.clear_btn)
        self.save_btn = QPushButton(t("toolbar_save"))
        style_btn(self.save_btn)
        self.save_btn.clicked.connect(self._on_save_clicked)

        # Set non-checkable buttons explicitly (ensures they cannot stay pressed)
        for b in [self.undo_btn, self.reset_btn, self.clear_btn, self.save_btn]:
            b.setCheckable(False)

        for b in [self.view_btn, self.mark_btn, self.erase_btn,
                  self.undo_btn, self.reset_btn, self.clear_btn, self.save_btn]:
            left_row.addWidget(b)

        # --- Right side (comments) ---
        right_row = QHBoxLayout()
        right_row.setSpacing(8)
        main_row.addLayout(right_row)

        self.comment_btn = QPushButton(t("toolbar_notes"))

        for b in [self.comment_btn]:
            style_btn(b)
            right_row.addWidget(b)

        # Help button — opens the touch-gesture hints overlay (handled by the screen).
        # Language-neutral "?" so it needs no translation.
        self.help_btn = QPushButton("?")
        style_btn(self.help_btn)
        self.help_btn.setText("?")          # style_btn prepends a space; keep it compact
        self.help_btn.setCheckable(False)
        self.help_btn.setFixedWidth(scale.sc(theme.TOUCH_TARGET_MIN))
        right_row.addWidget(self.help_btn)
        self.help_btn.clicked.connect(self.help_requested.emit)

        # --- Mark palette popup ---
        self.mark_palette_popup = MarkPalettePopup(self)
        self.mark_palette_popup.hide()
        self.mark_palette_popup.levelSelected.connect(self._on_palette_level_selected)
        self.mark_palette_popup.brushScaleChanged.connect(self._on_brush_scale_changed)

        # ---------------------------- Connections ---------------------------- #
        # Mode clicks (explicit, user-intended)
        self.view_btn.clicked.connect(lambda: self._switch_mode("VIEW"))
        self.mark_btn.clicked.connect(lambda: self._switch_mode("MARK"))
        self.erase_btn.clicked.connect(lambda: self._switch_mode("ERASE"))

        # Guard against spurious toggles (repaints, renders)
        self.view_btn.toggled.connect(lambda checked: self._on_mode_toggled_guard("VIEW", checked))
        self.mark_btn.toggled.connect(lambda checked: self._on_mode_toggled_guard("MARK", checked))
        self.erase_btn.toggled.connect(lambda checked: self._on_mode_toggled_guard("ERASE", checked))

        # Actions
        self.undo_btn.clicked.connect(lambda: self._perform_action("UNDO"))
        self.reset_btn.clicked.connect(lambda: self._perform_action("RESET"))
        self.clear_btn.clicked.connect(self._on_clear_clicked)

        # Comments
        self.comment_btn.clicked.connect(self.open_comment_popup)

        # --- Make non-persistent buttons release automatically ---
        def make_momentary(btn: QPushButton):
            btn.pressed.connect(lambda b=btn: b.setChecked(False))

        for btn in [self.undo_btn, self.reset_btn, self.clear_btn, self.save_btn,
                    self.comment_btn, self.help_btn]:
            make_momentary(btn)

        # --- Icons ---
        _icons = get_base_icons_path()

        def _tint(source, color: str) -> QPixmap:
            """Return a copy of the pixmap with all opaque pixels set to color.
            source may be a file path (str) or an already-rendered QPixmap."""
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

        def _mode_icon(grey, blue):
            icon = QIcon()
            icon.addPixmap(_tint(os.path.join(_icons, grey), "#E2EAF4"), QIcon.Mode.Normal, QIcon.State.Off)
            icon.addPixmap(_tint(os.path.join(_icons, blue), "#BAE6FD"), QIcon.Mode.Normal, QIcon.State.On)
            return icon

        def _action_icon(filename):
            path = os.path.join(_icons, filename)
            if filename.endswith(".svg"):
                return QIcon(path)
            return QIcon(_tint(path, "#E2EAF4"))

        self.view_btn.setIcon(_mode_icon("arrow_grey.png", "arrow_blue.png"))
        self.mark_btn.setIcon(_mode_icon("mark_grey.png", "mark_blue.png"))
        self.erase_btn.setIcon(_mode_icon("erase_grey.png", "erase_blue.png"))
        self.undo_btn.setIcon(_action_icon("undo_grey.png"))
        self.reset_btn.setIcon(_action_icon("camera.svg"))
        self.clear_btn.setIcon(_action_icon("trash_grey.png"))
        self.save_btn.setIcon(_action_icon("save.svg"))
        self.comment_btn.setIcon(_action_icon("comment_grey.png"))

        _icon_size = QSize(scale.sc(24), scale.sc(24))
        for b in [self.view_btn, self.mark_btn, self.erase_btn,
                  self.undo_btn, self.reset_btn, self.clear_btn,
                  self.save_btn, self.comment_btn]:
            b.setIconSize(_icon_size)

        # Initial visuals
        self._apply_visual_state("VIEW")

        # Connect language changes
        lang_manager.connect(self._refresh_text)

    def _refresh_text(self, lang=None):
        self.view_btn.setText(" " + t("toolbar_view"))
        self.mark_btn.setText(" " + t("toolbar_mark"))
        self.erase_btn.setText(" " + t("toolbar_erase"))
        self.undo_btn.setText(" " + t("toolbar_undo"))
        self.reset_btn.setText(" " + t("toolbar_reset_camera"))
        self.clear_btn.setText(" " + t("toolbar_clear"))
        self.save_btn.setText(" " + t("toolbar_save"))
        self.comment_btn.setText(" " + t("toolbar_notes"))
        self.mark_palette_popup.refresh_text()

    # ---------------------------- Guard against unintended toggles ---------------------------- #
    def _on_mode_toggled_guard(self, btn_mode: str, checked: bool):
        """Prevent unintended View selection after Clear/Render."""
        if not checked:
            return
        if self._allow_programmatic_switch:
            return
        if btn_mode != self._current_mode:
            print(f"[Toolbar] Blocked unintended toggle to {btn_mode}; keeping {self._current_mode}.")
            self._apply_visual_state(self._current_mode)

    # ---------------------------- Mode switching ---------------------------- #
    def _switch_mode(self, mode: str):
        """User-intended mode change."""
        mode = (mode or "VIEW").upper()
        if mode == self._current_mode:
            self._apply_visual_state(mode)
            if mode != "MARK":
                self.mark_palette_popup.hide()
            return

        self._allow_programmatic_switch = True
        try:
            if self.renderer:
                try:
                    self.renderer.toggle_mode(mode)
                except Exception as e:
                    print(f"[Toolbar] Renderer failed to switch mode {mode}: {e}")

            self._apply_visual_state(mode)

            if mode == "MARK":
                self._open_palette_under_button()
            else:
                self.mark_palette_popup.hide()

            self._current_mode = mode
            print(f"[Toolbar] Mode → {mode}")
        finally:
            self._allow_programmatic_switch = False

    def _apply_visual_state(self, mode: str):
        """Manually enforce exclusive check state for the three mode buttons."""
        mode = (mode or "VIEW").upper()
        self.view_btn.setChecked(mode == "VIEW")
        self.mark_btn.setChecked(mode == "MARK")
        self.erase_btn.setChecked(mode == "ERASE")

    # ---------------------------- Clear / Undo / Reset ---------------------------- #
    def _on_clear_clicked(self):
        """Clear markings only — no mode change, no button changes."""
        if not self.renderer:
            return
        try:
            has_any_paint = False
            if hasattr(self.renderer, "interactor_style") and hasattr(self.renderer.interactor_style, "cell_levels"):
                has_any_paint = len(self.renderer.interactor_style.cell_levels) > 0

            if not has_any_paint:
                print("[Toolbar] Clear skipped — no markings to clear.")
                self._apply_visual_state(self._current_mode)
                return

            self.renderer.clear_all()
            print("[Toolbar] Cleared all markings (mode unchanged).")

        except Exception as e:
            print(f"[Toolbar] Failed to clear markings: {e}")
        finally:
            self._apply_visual_state(self._current_mode)
            if self.renderer:
                try:
                    self.renderer.set_mode(self._current_mode)
                except Exception as e:
                    print(f"[Toolbar] Failed to reapply renderer mode: {e}")

            if self._current_mode == "MARK":
                if not self.mark_palette_popup.isVisible():
                    self._open_palette_under_button()
            else:
                self.mark_palette_popup.hide()

    def _perform_action(self, action: str):
        """Undo / Reset – no mode change."""
        if not self.renderer:
            return
        try:
            if action == "UNDO":
                self.renderer.undo()
            elif action == "RESET":
                self.renderer.reset_camera()
            print(f"[Toolbar] {action} executed (mode unchanged).")
        except Exception as e:
            print(f"[Toolbar] Failed to perform {action}: {e}")
        finally:
            self._apply_visual_state(self._current_mode)

    # ---------------------------- Palette ---------------------------- #
    def _open_palette_under_button(self):
        """Place the mark palette under the Mark button, clamped to the screen."""
        btn_rect = self.mark_btn.rect()
        global_pos = self.mark_btn.mapToGlobal(btn_rect.bottomLeft())
        self.mark_palette_popup.adjustSize()
        popup_w = self.mark_palette_popup.width()
        popup_h = self.mark_palette_popup.height()
        btn_w = self.mark_btn.width()
        x = global_pos.x() + (btn_w - popup_w) // 2
        y = global_pos.y() + 6

        # Clamp inside the available screen area so the popup never runs
        # off-screen (it grew wider with the brush-size control).
        try:
            screen = self.screen() or self.mark_btn.screen()
            if screen is not None:
                avail = screen.availableGeometry()
                x = max(avail.left() + 4, min(x, avail.right() - popup_w - 4))
                y = max(avail.top() + 4, min(y, avail.bottom() - popup_h - 4))
        except Exception:
            pass

        self.mark_palette_popup.move(x, y)
        self.mark_palette_popup.show()
        self.mark_palette_popup.raise_()

    def resizeEvent(self, event):
        """Reposition the palette popup when the toolbar resizes (e.g. window maximize)."""
        super().resizeEvent(event)
        if self.mark_palette_popup.isVisible():
            self._open_palette_under_button()

    def moveEvent(self, event):
        """Reposition the palette popup when the toolbar moves (e.g. window drag)."""
        super().moveEvent(event)
        if self.mark_palette_popup.isVisible():
            self._open_palette_under_button()

    def _on_palette_level_selected(self, level_id: int):
        """Pass mark intensity to renderer."""
        if self.renderer:
            print(f"[Toolbar] set_mark_level({level_id})")
            self.renderer.set_mark_level(level_id)

    def _on_brush_scale_changed(self, factor: float):
        """Pass user brush-size adjustment to renderer."""
        if self.renderer and hasattr(self.renderer, "set_brush_scale"):
            self.renderer.set_brush_scale(factor)

    # ---------------------------- Comments ---------------------------- #
    def open_comment_popup(self):
        popup = CommentPopup(self)
        popup.comments = list(self.comments)
        popup.refresh_list()
        popup.exec()
        self.comments = list(popup.comments)
        self.session_comments = list(popup.comments)
        print(f"[Toolbar] Comments updated: {len(self.comments)} total")

    # ---------------------------- Save ---------------------------- #
    def _on_save_clicked(self):
        """Triggered when user presses Save button."""
        if not self.renderer:
            print("[Toolbar] Save skipped — renderer not available.")
            return
        try:
            if not hasattr(self.renderer, "save_full_session"):
                print("[Toolbar] Renderer missing save_full_session()")
                return

            if hasattr(self.renderer, "session_manager"):
                session_manager = self.renderer.session_manager
            else:
                session_manager = getattr(self.renderer, "session_manager", None)

            if session_manager:
                self.renderer.save_full_session(session_manager, comments=self.session_comments)
                self.session_saved.emit()
            else:
                print("[Toolbar] SessionManager not attached to renderer.")

        except Exception as e:
            print(f"[Toolbar] Failed to save session: {e}")

    def clear_all_comments(self):
        """Reset all stored comments for a new session."""
        self.comments = []
        self.session_comments = []

    def reset_state(self):
        """Reset toolbar to VIEW mode and mark palette to level 1. Call on new session start."""
        self._allow_programmatic_switch = True
        try:
            self._current_mode = "VIEW"
            self._apply_visual_state("VIEW")
            self.mark_palette_popup.hide()
            # Fully reset palette to level 1 — button check AND the visible ring/dot.
            # (Plain setChecked left the cyan ring on the previously picked color.)
            self.mark_palette_popup.select_level(1)
            # Reset brush to the default size for the new session
            try:
                self.mark_palette_popup.reset_brush_scale()
            except Exception as e:
                print(f"[Toolbar] reset brush scale failed: {e}")
            # Keep the renderer's paint level in sync with the reset palette so the
            # shown color and the painted color agree on the next session.
            if self.renderer:
                try:
                    self.renderer.set_mark_level(1)
                except Exception as e:
                    print(f"[Toolbar] reset_state set_mark_level failed: {e}")
        finally:
            self._allow_programmatic_switch = False

# ---------------------------- Circular color button ---------------------------- #
class CircleColorButton(QAbstractButton):
    """Custom-painted circular button — bypasses Qt native style so border-radius
    issues on Windows do not apply. Drawn entirely with QPainter."""

    def __init__(self, color: str, diameter: int, parent=None):
        super().__init__(parent)
        self._fill = QColor(color)
        self.setFixedSize(diameter, diameter)
        self.setCheckable(True)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Filled circle (1px inset so the border ring fits inside the widget)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._fill)
        p.drawEllipse(1, 1, w - 2, h - 2)

        # Border ring
        if self.isChecked():
            pen_color = QColor(255, 255, 255, 255)
            pen_w = 3
        elif self.underMouse():
            pen_color = QColor(255, 255, 255, 191)
            pen_w = 2
        else:
            pen_color = QColor(255, 255, 255, 64)
            pen_w = 2
        p.setPen(QPen(pen_color, pen_w))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(2, 2, w - 4, h - 4)
        p.end()


# ---------------------------- Mark palette ---------------------------- #
class MarkPalettePopup(QWidget):
    levelSelected = pyqtSignal(int)
    # Emitted when the user adjusts brush size (multiplier of the default radius)
    brushScaleChanged = pyqtSignal(float)

    # Brush multiplier bounds/step (matches interactor clamp)
    _BRUSH_MIN = 0.4
    _BRUSH_MAX = 3.0
    _BRUSH_STEP = 0.3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("MarkPalettePopup")
        self.setStyleSheet("""
            QWidget#MarkPalettePopup {
                background-color: rgba(240, 244, 248, 0.97);
                border: 1px solid rgba(0, 206, 209, 0.30);
                border-radius: 12px;
            }
            QLabel {
                font-size: 11pt;
                color: #1E293B;
                background-color: transparent;
                border: none;
            }
        """)

        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(scale.sc(12), scale.sc(12), scale.sc(12), scale.sc(12))
        main_layout.setSpacing(scale.sc(14))
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        # Single source of truth for pain severity colors (see codes/theme.py)
        LEVEL_COLORS = theme.PAIN_LEVEL_COLORS

        # Store label refs for translation refresh, and dot indicators
        self._level_labels = []
        self._level_dots = {}   # level_id → QLabel indicator dot

        def add_color_column(color: str, text_key: str, level_id: int):
            vbox = QVBoxLayout()
            vbox.setSpacing(4)

            # Outer wrapper gives us the visible white/cyan ring on selection
            wrapper = QWidget()
            wrapper.setFixedSize(scale.sc(56), scale.sc(56))
            wrapper.setObjectName(f"lvl_wrap_{level_id}")
            wrapper.setStyleSheet(f"""
                QWidget#lvl_wrap_{level_id} {{
                    background-color: transparent;
                    border-radius: {scale.sc(24)}px;
                    border: 3px solid transparent;
                }}
            """)
            wrapper_inner = QHBoxLayout(wrapper)
            wrapper_inner.setContentsMargins(3, 3, 3, 3)

            btn = CircleColorButton(color, scale.sc(46))
            wrapper_inner.addWidget(btn)

            # Small dot indicator below — visible only when selected
            dot = QLabel("▲")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setStyleSheet(
                "color: #00CED1; font-size: 9px; background: transparent; border: none;"
            )
            dot.setFixedHeight(scale.sc(12))
            dot.setVisible(False)

            lbl = QLabel(t(text_key))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            vbox.addWidget(wrapper, alignment=Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(dot, alignment=Qt.AlignmentFlag.AlignCenter)
            vbox.addWidget(lbl)
            main_layout.addLayout(vbox)
            self.group.addButton(btn, level_id)
            self._level_labels.append((lbl, text_key))
            self._level_dots[level_id] = (wrapper, dot, color)

        add_color_column(LEVEL_COLORS[1], "toolbar_mild", 1)
        add_color_column(LEVEL_COLORS[2], "toolbar_moderate", 2)
        add_color_column(LEVEL_COLORS[3], "toolbar_severe", 3)
        self.group.idClicked.connect(self._on_level_selected)

        # --- Brush size control (vertical column at the end of the row) ---
        self._brush_scale = 1.0
        brush_col = QVBoxLayout()
        brush_col.setSpacing(scale.sc(4))

        self._brush_label = QLabel(t("toolbar_brush"))
        self._brush_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        brush_btn_row = QHBoxLayout()
        brush_btn_row.setSpacing(scale.sc(6))

        def _brush_btn(text: str) -> QPushButton:
            b = QPushButton(text)
            b.setFixedSize(scale.sc(44), scale.sc(44))
            b.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(0, 206, 209, 0.12);
                    color: #1E293B;
                    font-size: {scale.sc(20)}px;
                    font-weight: bold;
                    border-radius: {scale.sc(22)}px;
                    border: 1px solid rgba(0, 206, 209, 0.45);
                }}
                QPushButton:pressed {{
                    background-color: rgba(0, 206, 209, 0.40);
                }}
            """)
            return b

        self._brush_minus = _brush_btn("−")
        self._brush_plus = _brush_btn("+")
        self._brush_minus.clicked.connect(lambda: self._adjust_brush(-self._BRUSH_STEP))
        self._brush_plus.clicked.connect(lambda: self._adjust_brush(+self._BRUSH_STEP))

        # Live size preview dot between the buttons
        self._brush_preview = QLabel("●")
        self._brush_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._brush_preview.setFixedWidth(scale.sc(34))
        self._update_brush_preview()

        brush_btn_row.addWidget(self._brush_minus)
        brush_btn_row.addWidget(self._brush_preview)
        brush_btn_row.addWidget(self._brush_plus)

        brush_col.addLayout(brush_btn_row)
        brush_col.addWidget(self._brush_label)
        main_layout.addSpacing(scale.sc(6))
        main_layout.addLayout(brush_col)

        # Apply correct direction for initial language
        self._update_layout_direction()

    # ---------------------------- Brush size ---------------------------- #
    def _adjust_brush(self, delta: float):
        new_scale = max(self._BRUSH_MIN, min(self._BRUSH_MAX, self._brush_scale + delta))
        if abs(new_scale - self._brush_scale) < 1e-6:
            return
        self._brush_scale = new_scale
        self._update_brush_preview()
        self.brushScaleChanged.emit(self._brush_scale)

    def _update_brush_preview(self):
        # Map scale [0.4..3.0] to a visible dot size [8..26px]
        px = int(scale.sc(8 + (self._brush_scale - self._BRUSH_MIN)
                          / (self._BRUSH_MAX - self._BRUSH_MIN) * 18))
        self._brush_preview.setStyleSheet(
            f"color: #1E293B; font-size: {px}px; background: transparent; border: none;"
        )

    def reset_brush_scale(self):
        """Reset brush to default size (used on new session)."""
        self._brush_scale = 1.0
        self._update_brush_preview()
        self.brushScaleChanged.emit(1.0)

    def _update_layout_direction(self):
        is_rtl = lang_manager.get_language() == "he"
        direction = Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight
        self.setLayoutDirection(direction)

    def refresh_text(self):
        for lbl, key in self._level_labels:
            lbl.setText(t(key))
        self._brush_label.setText(t("toolbar_brush"))
        self._update_layout_direction()

    def _on_level_selected(self, level_id: int):
        self._apply_selection_visual(level_id)
        self.levelSelected.emit(level_id)

    def _apply_selection_visual(self, level_id: int):
        # Update the visual ring + dot for all levels
        for lid, (wrapper, dot, color) in self._level_dots.items():
            selected = lid == level_id
            dot.setVisible(selected)
            if selected:
                wrapper.setStyleSheet(f"""
                    QWidget#lvl_wrap_{lid} {{
                        background-color: transparent;
                        border-radius: {scale.sc(24)}px;
                        border: 3px solid #00CED1;
                    }}
                """)
            else:
                wrapper.setStyleSheet(f"""
                    QWidget#lvl_wrap_{lid} {{
                        background-color: transparent;
                        border-radius: {scale.sc(24)}px;
                        border: 3px solid transparent;
                    }}
                """)

    def select_level(self, level_id: int):
        """Programmatically select a level: check the button AND move the
        selection ring/dot. group.idClicked fires only on real user clicks, so
        setChecked() alone leaves the ring on the previously selected color.
        Does NOT emit levelSelected — used for resets to avoid side-effects."""
        btn = self.group.button(level_id)
        if btn is not None:
            btn.setChecked(True)
        self._apply_selection_visual(level_id)
