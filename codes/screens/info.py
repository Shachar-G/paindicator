# codes/screens/info.py

import html as _html

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QScrollArea, QWidget, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt
from .base_screen import BaseScreen
from codes.translations import lang_manager
from codes import theme
from codes import scale

# ---------------------------------------------------------------------------
# Scrollbar style — matches the questionnaire screen
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Bilingual content
# ---------------------------------------------------------------------------

_CONTENT = {
    "en": [
        ("title",   "About PAINDICATOR"),
        ("body",    "PAINDICATOR is a digital system for pain mapping on a three-dimensional model of the human body."),
        ("body",    "The system was developed as part of a final project in Biomedical Engineering at Tel Aviv University, in collaboration with Loewenstein Rehabilitation Medical Center, part of Clalit Health Services."),
        ("body",    "The purpose of the system is to streamline and improve the process of pain documentation in pain clinics, by replacing manual marking on paper with interactive, clear, and structured marking on a three-dimensional model."),
        ("body",    "The system was developed by Amit Bezalel and Shachar Guttman, Biomedical Engineering students at Tel Aviv University, under the supervision of Prof. Mickey Scheinowitz, in collaboration with Loewenstein Rehabilitation Medical Center."),

        ("section", "Instructions for Use"),
        ("item",    "Enter the clinician's name and the patient ID."),
        ("item",    "Complete the pain questionnaire."),
        ("item",    "Select the patient model."),
        ("item",    "On the model screen, pain areas can be marked directly on the three-dimensional body model."),
        ("item",    "Use the View button to rotate, move, and inspect the model."),
        ("item",    "Use the Mark button to mark pain areas."),
        ("item",    "After clicking Mark, the pain intensity level can be selected:"),
        ("sub",     "Yellow - mild pain"),
        ("sub",     "Orange - moderate pain"),
        ("sub",     "Red - severe pain"),
        ("item",    "Use the Erase button to delete specific markings."),
        ("item",    "Use the Undo button to cancel the last action."),
        ("item",    "Use the Reset View button to return the model to the initial viewing angle."),
        ("item",    "Use the Clear button to delete all markings from the model."),
        ("item",    "Comments can be added using the Notes button."),
        ("item",    "At the end of the process, click Save to save the session data, questionnaire, comments, and model images."),

        ("section", "Analyse - Anatomical Analysis"),
        ("body",    "The Analyse function is designed to assist with anatomical interpretation of the marked pain areas."),
        ("body",    "The system calculates the degree of overlap between the marked pain areas and the dermatomal regions in the model, and presents the most relevant dermatomes according to the distribution of the markings and pain intensity."),
        ("body",    "It is important to emphasize that the output presented by the system is a supportive tool only. It does not constitute a final medical diagnosis and does not replace clinical judgment, physical examination, imaging, or a full medical evaluation."),

        ("section", "Data Saving"),
        ("body",    "After saving the session, the system stores the patient details, questionnaire answers, pain markings, comments, and images of the model from anterior and posterior views."),
        ("body",    "The information is saved for documentation, later review, and comparison between sessions."),
    ],
    "he": [
        ("title",   "אודות PAINDICATOR"),
        ("body",    "מערכת PAINDICATOR היא מערכת דיגיטלית למיפוי כאב על גבי מודל תלת-ממדי של גוף האדם."),
        ("body",    "המערכת פותחה במסגרת פרויקט גמר בהנדסה ביורפואית באוניברסיטת תל אביב, בשיתוף המרכז הרפואי לשיקום בית לוינשטיין מקבוצת כללית."),
        ("body",    "מטרת המערכת היא לייעל ולשפר את תהליך תיעוד הכאב במרפאות כאב, באמצעות מעבר מסימון ידני על גבי דף לסימון אינטראקטיבי, ברור ומובנה על מודל תלת-ממדי."),
        ("body",    "המערכת פותחה על ידי עמית בצלאל ושחר גוטמן, סטודנטים להנדסה ביורפואית באוניברסיטת תל אביב, בהנחיית פרופ' מיקי שיינוביץ, ובשיתוף המרכז הרפואי לשיקום בית לוינשטיין."),

        ("section", "הוראות שימוש"),
        ("item",    "יש להזין את שם הרופא/ה ואת מזהה המטופל/ת."),
        ("item",    "יש למלא את שאלון הכאב."),
        ("item",    "יש לבחור את מודל המטופל/ת."),
        ("item",    "במסך המודל ניתן לסמן את אזורי הכאב ישירות על גבי הגוף התלת-ממדי."),
        ("item",    "יש להשתמש בכפתור תצוגה כדי לסובב, להזיז ולבחון את המודל."),
        ("item",    "יש להשתמש בכפתור סמן כדי לסמן אזורי כאב."),
        ("item",    "לאחר לחיצה על סמן, ניתן לבחור את רמת הכאב:"),
        ("sub",     "   צהוב - כאב קל   "),
        ("sub",     "   כתום - כאב בינוני   "),
        ("sub",     "   אדום - כאב חמור "),
        ("item",    "יש להשתמש בכפתור מחק כדי למחוק סימונים נקודתיים."),
        ("item",    "יש להשתמש בכפתור חזור כדי לבטל את הפעולה האחרונה."),
        ("item",    "יש להשתמש בכפתור אפס תצוגה כדי להחזיר את המודל לזווית התצוגה הראשונית."),
        ("item",    "יש להשתמש בכפתור מחק הכל כדי למחוק את כל הסימונים במודל."),
        ("item",    "ניתן להוסיף הערות באמצעות כפתור הערות."),
        ("item",    "בסיום התהליך, יש ללחוץ על שמור כדי לשמור את נתוני המפגש, השאלון, ההערות ותמונות המודל."),

        ("section", "נתח - ניתוח אנטומי"),
        ("body",    "פונקציית נתח נועדה לסייע בפרשנות אנטומית של אזורי הכאב שסומנו."),
        ("body",    "המערכת מחשבת את מידת החפיפה בין אזורי הכאב שסומנו לבין אזורי דרמטומים במודל, ומציגה את הדרמטומים הרלוונטיים ביותר בהתאם לפיזור הסימונים ולעוצמת הכאב."),
        ("body",    "חשוב להדגיש כי הפלט המוצג על ידי המערכת הוא כלי עזר בלבד. הוא אינו מהווה אבחנה רפואית סופית ואינו מחליף שיקול דעת קליני, בדיקה גופנית, דימות או הערכה רפואית מלאה."),

        ("section", "שמירת נתונים"),
        ("body",    "לאחר שמירת המפגש, המערכת שומרת את פרטי המטופל/ת, תשובות השאלון, סימוני הכאב, ההערות ותמונות של המודל מזווית קדמית ואחורית."),
        ("body",    "המידע נשמר לצורך תיעוד, צפייה חוזרת והשוואה בין מפגשים."),
    ],
}


class InfoScreen(BaseScreen):
    """Info / About screen, displayed when the user taps the (i) button."""

    def __init__(self, main_window, patient_data, **kwargs):
        super().__init__(main_window, patient_data, **kwargs)
        self._labels: list[tuple[str, QLabel]] = []
        self._init_ui()

    # ------------------------------------------------------------------
    # Build UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(0, scale.sc(20), 0, scale.sc(20))
        main.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; } " + _SCROLLBAR_STYLE)
        main.addWidget(scroll)

        # Centering wrapper — mirrors questionnaire layout
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        wrapper_layout = QHBoxLayout(wrapper)
        wrapper_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(wrapper)

        self._container = QWidget()
        self._container.setFixedWidth(scale.sc(600))
        self._container.setStyleSheet("background: transparent;")
        self._container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        wrapper_layout.addWidget(self._container)

        self._inner_layout = QVBoxLayout(self._container)
        self._inner_layout.setContentsMargins(0, 10, 0, 40)
        self._inner_layout.setSpacing(0)
        self._inner_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._build_labels()

    def _build_labels(self):
        lang = lang_manager.get_language()
        is_rtl = (lang == "he")
        font_family = "Nunito" if self.nunito_font else "Arial"

        def make_lbl(raw_text, stylesheet, rich=False):
            lbl = QLabel()
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            lbl.setStyleSheet(stylesheet)
            if rich:
                lbl.setText(f'<p align="right" style="margin:0;">{_html.escape(raw_text)}</p>')
            else:
                lbl.setText(raw_text)
                lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            return lbl

        for kind, text in _CONTENT[lang]:

            if kind == "title":
                ss = f"""
                    color: {theme.PRIMARY_DARK};
                    font-family: '{font_family}';
                    font-size: {scale.sc(26)}px;
                    font-weight: bold;
                    padding-bottom: 6px;
                    border-bottom: 2px solid {theme.PRIMARY};
                """
                lbl = make_lbl(text, ss, rich=is_rtl)
                self._inner_layout.addSpacing(scale.sc(10))
                self._inner_layout.addWidget(lbl)
                self._inner_layout.addSpacing(scale.sc(14))

            elif kind == "section":
                ss = f"""
                    color: {theme.PRIMARY_DARK};
                    font-family: '{font_family}';
                    font-size: {scale.sc(18)}px;
                    font-weight: bold;
                    padding-bottom: 2px;
                    border-bottom: 1px solid rgba(0,150,160,0.3);
                """
                lbl = make_lbl(text, ss, rich=is_rtl)
                self._inner_layout.addSpacing(scale.sc(22))
                self._inner_layout.addWidget(lbl)
                self._inner_layout.addSpacing(scale.sc(10))

            elif kind == "body":
                ss = f"""
                    color: {theme.TEXT_PRIMARY};
                    font-family: '{font_family}';
                    font-size: {scale.sc(14)}px;
                """
                lbl = make_lbl(text, ss, rich=is_rtl)
                self._inner_layout.addWidget(lbl)
                self._inner_layout.addSpacing(scale.sc(8))

            elif kind == "item":
                bullet = "\u2022"
                display = f"{bullet}  {text}" if is_rtl else f"  {bullet}  {text}"
                ss = f"""
                    color: {theme.TEXT_PRIMARY};
                    font-family: '{font_family}';
                    font-size: {scale.sc(14)}px;
                """
                lbl = make_lbl(display, ss, rich=is_rtl)
                self._inner_layout.addWidget(lbl)
                self._inner_layout.addSpacing(scale.sc(4))

            elif kind == "sub":
                circle = "\u25e6"
                indent = "\u2003\u2003"
                display = f"{circle}  {text}" if is_rtl else f"{indent}{circle}  {text}"
                ss = f"""
                    color: {theme.TEXT_SECOND};
                    font-family: '{font_family}';
                    font-size: {scale.sc(13)}px;
                """
                lbl = make_lbl(display, ss, rich=is_rtl)
                self._inner_layout.addWidget(lbl)
                self._inner_layout.addSpacing(scale.sc(2))

            else:
                continue

            self._labels.append((kind, lbl))

        self._inner_layout.addStretch()

    def _clear_labels(self):
        """Remove all widgets and spacers from the inner layout."""
        while self._inner_layout.count():
            item = self._inner_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            del item
        self._labels.clear()

    # ------------------------------------------------------------------
    # Language refresh
    # ------------------------------------------------------------------

    def _refresh_text(self):
        self._clear_labels()
        self._build_labels()
