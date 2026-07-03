# codes/screens/questionnaire.py

import os
import tempfile

from PyQt6.QtWidgets import (
    QVBoxLayout, QScrollArea, QWidget, QLabel, QSpinBox, QSlider,
    QTextEdit, QCheckBox, QDateEdit, QAbstractSpinBox, QHBoxLayout, QSizePolicy, QAbstractButton
)
from PyQt6.QtCore import Qt, QDate, QPoint, QEvent, QObject, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QPolygon
from .base_screen import BaseScreen
from codes.translations import t
from codes import scale, theme


# Shared teal scrollbar style — used on QScrollArea and QTextEdit scrollbars
_SCROLLBAR_STYLE = """
    QScrollBar:vertical {
        background: rgba(0, 206, 209, 0.12);
        width: 8px;
        margin: 4px 2px;
        border-radius: 3px;
    }
    QScrollBar::handle:vertical {
        background: rgba(0, 206, 209, 0.75);
        min-height: 12px;
        border-radius: 3px;
    }
    QScrollBar::handle:vertical:hover {
        background: #00CED1;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
        background: none;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""


# Calendar year-spinbox arrow images — generated once into a temp file
_ARROW_UP_PATH = None
_ARROW_DN_PATH = None


def _ensure_arrow_pngs():
    """Generate small white triangle PNGs for the calendar year-spinbox up/down buttons."""
    global _ARROW_UP_PATH, _ARROW_DN_PATH
    if _ARROW_UP_PATH and os.path.exists(_ARROW_UP_PATH):
        return

    tmp_dir = tempfile.gettempdir()
    for direction, fname in [("up", "paindicator_arrow_up.png"), ("down", "paindicator_arrow_dn.png")]:
        path = os.path.join(tmp_dir, fname)
        pm = QPixmap(10, 6)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        if direction == "up":
            poly = QPolygon([QPoint(5, 0), QPoint(0, 6), QPoint(10, 6)])
        else:
            poly = QPolygon([QPoint(0, 0), QPoint(10, 0), QPoint(5, 6)])
        painter.drawPolygon(poly)
        painter.end()
        pm.save(path, "PNG")
        if direction == "up":
            _ARROW_UP_PATH = path
        else:
            _ARROW_DN_PATH = path


class ClickableDateEdit(QDateEdit):
    """QDateEdit that opens the calendar popup when clicking anywhere on the field."""
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # After base handler: if calendar is still hidden, click the dropdown button
        try:
            cw = self.calendarWidget()
            if cw is not None and not cw.isVisible():
                for btn in self.findChildren(QAbstractButton):
                    btn.click()
                    break
        except Exception:
            pass


class TouchScrollFilter(QObject):
    """
    Installed on QScrollArea.viewport().
    A single-finger or stylus drag scrolls the area with kinetic deceleration.
    When the touch lands on a QTextEdit, the keyboard is explicitly shown.
    """
    def __init__(self, scroll_area):
        super().__init__(scroll_area)
        self._scroll_area = scroll_area
        self._active = False
        self._last_y = 0.0
        self._velocity = 0.0

        self._decel_timer = QTimer(self)
        self._decel_timer.setInterval(16)   # ~60 fps
        self._decel_timer.timeout.connect(self._decelerate)

    def _decelerate(self):
        try:
            if abs(self._velocity) < 1.0:
                self._decel_timer.stop()
                return
            bar = self._scroll_area.verticalScrollBar()
            bar.setValue(int(bar.value() + self._velocity))
            self._velocity *= 0.90  # decay factor — higher = more momentum
        except Exception:
            self._decel_timer.stop()

    def _hit_textbox(self, pos):
        """Return the QTextEdit at viewport-coords pos, or None."""
        widget = self._scroll_area.viewport().childAt(pos)
        while widget is not None:
            if isinstance(widget, QTextEdit):
                return widget
            widget = widget.parent()
        return None

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.TouchBegin:
            pts = event.points()
            if not pts:
                return False
            self._decel_timer.stop()
            pos = pts[0].position().toPoint()
            tb = self._hit_textbox(pos)
            if tb is not None:
                # Focus the text box — TouchFocusReason not always available, use OtherFocusReason
                try:
                    tb.setFocus(Qt.FocusReason.OtherFocusReason)
                except Exception:
                    tb.setFocus()
                self._active = False
                return False  # let QTextEdit handle it
            self._active = True
            self._last_y = pts[0].position().y()
            self._velocity = 0.0
            event.accept()
            return True
        elif t == QEvent.Type.TouchUpdate:
            if not self._active:
                return False
            pts = event.points()
            if not pts:
                return True
            y = pts[0].position().y()
            dy = self._last_y - y
            self._last_y = y
            self._velocity = dy   # remember last velocity for momentum
            bar = self._scroll_area.verticalScrollBar()
            bar.setValue(int(bar.value() + dy))
            event.accept()
            return True
        elif t == QEvent.Type.TouchEnd:
            if self._active:
                self._active = False
                # Kick off momentum for any noticeable flick
                if abs(self._velocity) > 0.5:
                    self._decel_timer.start()
                event.accept()
                return True
            return False
        return False


class QuestionnaireScreen(BaseScreen):
    """
    Full questionnaire screen, shown only in Start New Session,
    before GenderSelection, styled as mobile capsule inputs.
    """

    def __init__(self, main_window, patient_data, session_manager=None, **kwargs):
        super().__init__(main_window, patient_data,
                         session_manager=session_manager, **kwargs)
        self.init_ui()

    # ---------------------------------------------------------
    # STYLES
    # ---------------------------------------------------------
    def capsule_style(self):
        return """
            background-color: #F6F6F6;
            border: 1px solid #D0D0D0;
            border-radius: 14px;
            padding: 10px;
        """

    def capsule_text_style(self):
        return """
            QTextEdit {
                background-color: #F6F6F6;
                border: 1px solid #D0D0D0;
                border-radius: 14px;
                padding: 10px;
                font-size: 20px;
            }
        """

    def capsule_date_style(self):
        return """
            QDateEdit {
                background-color: #F6F6F6;
                border: 1px solid #D0D0D0;
                border-radius: 14px;
                padding-left: 10px;
                font-size: 18px;
                height: 50px;
            }
        """

    # ---------------------------------------------------------
    # VAS slider capsule — horizontal teal slider 1–10
    # ---------------------------------------------------------
    def add_capsule_slider(self):
        capsule = QWidget()
        capsule.setStyleSheet(self.capsule_style())
        capsule.setMinimumHeight(scale.sc(58))
        capsule.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Always LTR: slider on left, number on right, regardless of app language
        capsule.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        layout = QHBoxLayout(capsule)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        lbl_min = QLabel("1")
        lbl_min.setStyleSheet(
            f"font-size: {scale.sc(13)}px; color: {theme.TEXT_HINT}; background: transparent; border: none;"
        )

        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(1, 10)
        sl.setValue(1)
        sl.setTickPosition(QSlider.TickPosition.TicksBelow)
        sl.setTickInterval(1)
        sl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sl.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(0, 206, 209, 0.18);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 206, 209, 0.50),
                    stop:1 rgba(0, 206, 209, 1.0));
                height: 6px;
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: rgba(0, 206, 209, 0.12);
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #FFFFFF,
                    stop:0.4 #BAE6FD,
                    stop:1 rgba(0, 206, 209, 0.80));
                width: 22px;
                height: 22px;
                margin: -8px 0;
                border-radius: 11px;
                border: 1px solid rgba(0, 206, 209, 0.70);
            }
            QSlider::handle:horizontal:hover {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #FFFFFF,
                    stop:0.3 #00CED1,
                    stop:1 rgba(0, 150, 160, 0.90));
            }
        """)

        lbl_max = QLabel("10")
        lbl_max.setStyleSheet(
            f"font-size: {scale.sc(13)}px; color: {theme.TEXT_HINT}; background: transparent; border: none;"
        )

        # Editable spinbox — no arrows, bidirectionally synced with the slider
        val_spin = QSpinBox()
        val_spin.setRange(1, 10)
        val_spin.setValue(1)
        val_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        val_spin.setFixedWidth(scale.sc(42))
        val_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_spin.setStyleSheet(f"""
            QSpinBox {{
                font-size: {scale.sc(14)}px;
                font-weight: bold;
                color: #00CED1;
                background: transparent;
                border: none;
            }}
        """)

        # Bidirectional sync — Qt suppresses signals when value is unchanged, no loop
        sl.valueChanged.connect(val_spin.setValue)
        val_spin.valueChanged.connect(sl.setValue)

        layout.addWidget(lbl_min)
        layout.addWidget(sl)
        layout.addWidget(lbl_max)
        layout.addWidget(val_spin)
        return capsule, sl

    def add_capsule_date(self):
        capsule = QWidget()
        capsule.setMinimumHeight(scale.sc(50))
        capsule.setStyleSheet(self.capsule_style())
        capsule.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(capsule)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(0)

        de = ClickableDateEdit()
        de.setCalendarPopup(True)
        de.setDate(QDate.currentDate())
        de.setDisplayFormat("dd/MM/yyyy")
        de.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Hide spin up/down arrows — calendar popup and typing are sufficient
        de.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        de.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Style the calendar popup
        cw = de.calendarWidget()
        cw.setMinimumWidth(320)

        # Replace old platform arrow icons on prev/next month buttons
        for btn in cw.findChildren(QAbstractButton):
            if btn.objectName() == "qt_calendar_prevmonth":
                btn.setIcon(QIcon())
                btn.setText("‹")
            elif btn.objectName() == "qt_calendar_nextmonth":
                btn.setIcon(QIcon())
                btn.setText("›")

        # Generate white arrow PNGs for the year spinbox (Qt cannot render CSS triangles)
        _ensure_arrow_pngs()
        up_url = (_ARROW_UP_PATH or "").replace("\\", "/")
        dn_url = (_ARROW_DN_PATH or "").replace("\\", "/")

        cw.setStyleSheet(f"""
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: rgba(0, 206, 209, 0.08);
                border-bottom: 1px solid rgba(0, 206, 209, 0.25);
                padding: 2px;
            }}
            QCalendarWidget QToolButton {{
                color: #0a1628;
                background: transparent;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                font-weight: bold;
                padding: 4px 8px;
                min-width: 28px;
                min-height: 28px;
            }}
            QCalendarWidget QToolButton:hover {{
                background: rgba(0, 206, 209, 0.20);
                color: #007a7a;
            }}
            QCalendarWidget QToolButton:pressed {{
                background: rgba(0, 206, 209, 0.38);
            }}
            QCalendarWidget QSpinBox {{
                color: #0a1628;
                background: transparent;
                border: 1px solid rgba(0, 206, 209, 0.35);
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
                padding: 2px 4px;
                selection-background-color: rgba(0, 206, 209, 0.30);
            }}
            QCalendarWidget QSpinBox::up-button {{
                width: 18px;
                border: none;
                background: rgba(0, 206, 209, 0.18);
                border-radius: 0 3px 0 0;
            }}
            QCalendarWidget QSpinBox::down-button {{
                width: 18px;
                border: none;
                background: rgba(0, 206, 209, 0.18);
                border-radius: 0 0 3px 0;
            }}
            QCalendarWidget QSpinBox::up-button:hover,
            QCalendarWidget QSpinBox::down-button:hover {{
                background: rgba(0, 206, 209, 0.45);
            }}
            QCalendarWidget QSpinBox::up-arrow {{
                image: url({up_url});
                width: 10px;
                height: 6px;
            }}
            QCalendarWidget QSpinBox::down-arrow {{
                image: url({dn_url});
                width: 10px;
                height: 6px;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: #1a1a1a;
                background-color: #ffffff;
                selection-background-color: rgba(0, 206, 209, 0.35);
                selection-color: #0a1628;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: #aaaaaa;
            }}
            QCalendarWidget QAbstractItemView::item:hover {{
                background-color: #e0e0e0;
                color: #1a1a1a;
            }}
        """)

        de.setStyleSheet("""
            QDateEdit {
                background: transparent;
                border: none;
                font-size: 20px;
                padding: 0px;
            }
        """)

        layout.addWidget(de)
        return capsule, de

    def add_capsule_age(self):
        """Age input: integer spinbox 0–120 inside a capsule row."""
        capsule = QWidget()
        capsule.setMinimumHeight(scale.sc(58))
        capsule.setStyleSheet(self.capsule_style())
        capsule.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        capsule.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

        layout = QHBoxLayout(capsule)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(10)

        spin = QSpinBox()
        spin.setRange(0, 120)
        spin.setValue(0)
        spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        spin.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spin.setStyleSheet(f"""
            QSpinBox {{
                font-size: {scale.sc(22)}px;
                font-weight: bold;
                color: #0A1628;
                background: transparent;
                border: none;
            }}
        """)

        lbl_unit = QLabel("yr")
        lbl_unit.setStyleSheet(
            f"font-size: {scale.sc(14)}px; color: {theme.TEXT_HINT}; background: transparent; border: none;"
        )

        layout.addWidget(spin)
        layout.addWidget(lbl_unit)
        return capsule, spin

    # ---------------------------------------------------------
    # BUILD UI
    # ---------------------------------------------------------
    def init_ui(self):
        # Stores (widget, translation_key) pairs for _refresh_text
        self._tr_labels = []   # QLabel items: (lbl, key)
        self._tr_checks = []   # QCheckBox items: (cb, key)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, scale.sc(20), 0, scale.sc(20))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; } " + _SCROLLBAR_STYLE)
        self._scroll_area = scroll
        main.addWidget(scroll)

        # Enable single-finger / stylus scrolling on touchscreens.
        # The filter passes touches through to QTextEdit widgets unchanged.
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_AcceptTouchEvents)
        self._touch_scroll_filter = TouchScrollFilter(scroll)
        scroll.viewport().installEventFilter(self._touch_scroll_filter)

        wrapper = QWidget()
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        scroll.setWidget(wrapper)

        container = QWidget()
        container.setFixedWidth(scale.sc(550))
        container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._form_container = container  # stored for resizeEvent width adjustment

        self.form = QVBoxLayout(container)
        self.form.setAlignment(Qt.AlignmentFlag.AlignTop)
        wrapper_layout.addWidget(container)

        def add_title(key):
            lbl = QLabel(t(key))
            font = QFont(self.nunito_font)
            font.setPointSize(scale.sc(22))
            font.setBold(True)
            lbl.setFont(font)
            lbl.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; margin-top:15px; margin-bottom:5px;")
            self.form.addWidget(lbl)
            self._tr_labels.append((lbl, key))

        def add_label(key):
            lbl = QLabel(t(key))
            font = QFont(self.nunito_font)
            font.setPointSize(scale.sc(16))
            lbl.setFont(font)
            lbl.setStyleSheet(f"color:{theme.TEXT_PRIMARY}; margin-top:8px; margin-bottom:3px;")
            self.form.addWidget(lbl)
            self._tr_labels.append((lbl, key))

        def add_capsule_textbox(h=70):
            tb = QTextEdit()
            tb.setFixedHeight(scale.sc(h))
            tb.setStyleSheet(self.capsule_text_style())
            # Apply scrollbar style directly — avoids border-radius clipping issues
            tb.verticalScrollBar().setStyleSheet(_SCROLLBAR_STYLE)
            return tb

        def add_capsule_checkbox(key):
            cb = QCheckBox(t(key))
            cb.setStyleSheet("font-size:16px; margin-top:6px;")
            self._tr_checks.append((cb, key))
            return cb

        # ---------------------------------------------------------
        # Patient Information
        # ---------------------------------------------------------
        add_title("q_section_patient_info")
        add_label("q_patient_age")
        age_capsule, self.age_spin = self.add_capsule_age()
        self.form.addWidget(age_capsule)

        # ---------------------------------------------------------
        # VAS
        # ---------------------------------------------------------
        add_title("q_section_pain_intensity")

        add_label("q_pain_during_anamnesis")
        capsule, self.vas_anamnesis = self.add_capsule_slider()
        self.form.addWidget(capsule)

        add_label("q_pain_average")
        capsule, self.vas_average = self.add_capsule_slider()
        self.form.addWidget(capsule)

        add_label("q_pain_acute")
        capsule, self.vas_peak = self.add_capsule_slider()
        self.form.addWidget(capsule)

        # ---------------------------------------------------------
        # Frequency
        # ---------------------------------------------------------
        add_title("q_section_pain_frequency")

        self.freq_related = add_capsule_checkbox("q_freq_specific_event")
        self.freq_sudden = add_capsule_checkbox("q_freq_sudden_onset")
        self.freq_other = add_capsule_checkbox("q_freq_other")
        self.freq_constant = add_capsule_checkbox("q_freq_constant")
        self.freq_intermit = add_capsule_checkbox("q_freq_intermittent")

        for cb in [
            self.freq_related, self.freq_sudden, self.freq_other,
            self.freq_constant, self.freq_intermit
        ]:
            self.form.addWidget(cb)

        add_label("q_freq_comment")
        self.freq_comment = add_capsule_textbox(70)
        self.form.addWidget(self.freq_comment)

        # ---------------------------------------------------------
        # Characteristics
        # ---------------------------------------------------------
        add_title("q_section_pain_characteristics")

        add_label("q_char_radiation")
        self.radiation = add_capsule_textbox(60)
        self.form.addWidget(self.radiation)

        add_label("q_char_when_began")
        self.begin = add_capsule_textbox(60)
        self.form.addWidget(self.begin)

        add_label("q_char_varies_day")
        self.variation = add_capsule_textbox(60)
        self.form.addWidget(self.variation)

        add_label("q_char_character_section")
        self.char_press = add_capsule_checkbox("q_char_pressing")
        self.char_burn = add_capsule_checkbox("q_char_burning")
        self.char_stab = add_capsule_checkbox("q_char_stabbing")
        self.char_hot = add_capsule_checkbox("q_char_hot")
        self.char_tingle = add_capsule_checkbox("q_char_tingling")
        self.char_sharp = add_capsule_checkbox("q_char_sharp")
        self.char_dull = add_capsule_checkbox("q_char_dull")
        self.char_pulse = add_capsule_checkbox("q_char_pulsating")
        self.char_neuro = add_capsule_checkbox("q_char_neuropathic")
        self.char_other = add_capsule_checkbox("q_char_other")

        for cb in [
            self.char_press, self.char_burn, self.char_stab, self.char_hot,
            self.char_tingle, self.char_sharp, self.char_dull,
            self.char_pulse, self.char_neuro, self.char_other
        ]:
            self.form.addWidget(cb)

        add_label("q_char_comment")
        self.char_comment = add_capsule_textbox(70)
        self.form.addWidget(self.char_comment)

        # ---------------------------------------------------------
        # Factors
        # ---------------------------------------------------------
        add_title("q_section_factors")

        add_label("q_factor_alleviating")
        self.alleviate = add_capsule_textbox(60)
        self.form.addWidget(self.alleviate)

        add_label("q_factor_aggravating")
        self.aggravate = add_capsule_textbox(60)
        self.form.addWidget(self.aggravate)

        add_label("q_factor_associated")
        self.symptoms = add_capsule_textbox(60)
        self.form.addWidget(self.symptoms)

        # ---------------------------------------------------------
        # Impact
        # ---------------------------------------------------------
        add_title("q_section_impact")

        self.life_sleep = add_capsule_checkbox("q_impact_sleep")
        self.life_appetite = add_capsule_checkbox("q_impact_appetite")
        self.life_rest = add_capsule_checkbox("q_impact_rest")
        self.life_activity = add_capsule_checkbox("q_impact_physical")
        self.life_walk = add_capsule_checkbox("q_impact_walking")
        self.life_study = add_capsule_checkbox("q_impact_educational")
        self.life_mood = add_capsule_checkbox("q_impact_mood")
        self.life_conc = add_capsule_checkbox("q_impact_concentration")
        self.life_family = add_capsule_checkbox("q_impact_family")
        self.life_social = add_capsule_checkbox("q_impact_social")

        for cb in [
            self.life_sleep, self.life_appetite, self.life_rest,
            self.life_activity, self.life_walk, self.life_study,
            self.life_mood, self.life_conc, self.life_family, self.life_social
        ]:
            self.form.addWidget(cb)

        add_label("q_impact_comments")
        self.life_comment = add_capsule_textbox(70)
        self.form.addWidget(self.life_comment)

        # ---------------------------------------------------------
        # Date
        # ---------------------------------------------------------
        add_title("q_section_exam_date")
        capsule, self.exam_date = self.add_capsule_date()
        self.form.addWidget(capsule)

        # ---------------------------------------------------------
        # Continue button
        # ---------------------------------------------------------
        self.continue_btn = self.create_button(t("continue_btn"))
        self.continue_btn.setMinimumHeight(55)
        self.form.addWidget(self.continue_btn)

        self.continue_btn.clicked.connect(self.save_and_continue)
        self._refresh_text()

    def resizeEvent(self, event):
        """Keep form container width at 95% of available width, capped at scaled 550px."""
        super().resizeEvent(event)
        if hasattr(self, "_form_container"):
            new_w = min(scale.sc(550), max(scale.sc(300), int(self.width() * 0.95)))
            self._form_container.setFixedWidth(new_w)

    def _refresh_text(self):
        from codes.translations import lang_manager
        is_rtl = lang_manager.get_language() == "he"
        cb_direction = Qt.LayoutDirection.RightToLeft if is_rtl else Qt.LayoutDirection.LeftToRight

        for lbl, key in self._tr_labels:
            lbl.setText(t(key))
        for cb, key in self._tr_checks:
            cb.setText(t(key))
            cb.setLayoutDirection(cb_direction)
        self.continue_btn.setText(t("continue_btn"))

    # ---------------------------------------------------------
    # SAVE
    # ---------------------------------------------------------
    def save_and_continue(self):

        questionnaire = {
            "age": self.age_spin.value(),
            "pain anamnesis": self.vas_anamnesis.value(),
            "pain average": self.vas_average.value(),
            "pain peak": self.vas_peak.value(),

            "frequency": [
                cb.text() for cb in [
                    self.freq_related, self.freq_sudden, self.freq_other,
                    self.freq_constant, self.freq_intermit
                ] if cb.isChecked()
            ],
            "frequency comment": self.freq_comment.toPlainText(),

            "radiation": self.radiation.toPlainText(),
            "pain begin": self.begin.toPlainText(),
            "pain variation": self.variation.toPlainText(),
            "pain character": [
                cb.text() for cb in [
                    self.char_press, self.char_burn, self.char_stab, self.char_hot,
                    self.char_tingle, self.char_sharp, self.char_dull,
                    self.char_pulse, self.char_neuro, self.char_other
                ] if cb.isChecked()
            ],
            "pain character comment": self.char_comment.toPlainText(),

            "alleviating factors": self.alleviate.toPlainText(),
            "aggravating factors": self.aggravate.toPlainText(),
            "associated symptoms": self.symptoms.toPlainText(),

            "life impact": [
                cb.text() for cb in [
                    self.life_sleep, self.life_appetite, self.life_rest,
                    self.life_activity, self.life_walk, self.life_study,
                    self.life_mood, self.life_conc, self.life_family, self.life_social
                ] if cb.isChecked()
            ],
            "life comment": self.life_comment.toPlainText(),

            "examination date": self.exam_date.date().toString("dd/MM/yyyy")
        }

        self.session_manager.set_questionnaire(questionnaire)
        self.main_window.navigate_to("show_model")

    def on_load(self, **kwargs):
        """Reset all fields each time this screen is shown for a new session."""
        self.reset_questionnaire()
        if hasattr(self, "_scroll_area"):
            self._scroll_area.verticalScrollBar().setValue(0)

    def reset_questionnaire(self):
        """Reset all questionnaire fields to their default values."""
        for widget in self.findChildren((QSpinBox, QSlider, QDateEdit, QTextEdit, QCheckBox)):
            if isinstance(widget, (QSpinBox, QSlider)):
                widget.setValue(widget.minimum())
            elif isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
            elif isinstance(widget, QTextEdit):
                widget.clear()
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)
