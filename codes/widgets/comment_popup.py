from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, QWidget
)
from PyQt6.QtCore import Qt, QSize, QEvent, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from codes.translations import t, lang_manager
from codes.config import get_base_icons_path
import os


def _tint(path: str, color: str) -> QPixmap:
    px = QPixmap(path)
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


def _icon(filename: str) -> QIcon:
    path = os.path.join(get_base_icons_path(), filename)
    if filename.endswith(".svg"):
        return QIcon(path)
    return QIcon(_tint(path, "#E2EAF4"))


class CommentPopup(QDialog):
    """Popup window for adding, editing and deleting comments."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("comment_title"))
        self.setModal(True)
        self.resize(420, 500)

        self._is_rtl = lang_manager.get_language() == "he"
        _is_rtl = self._is_rtl
        _direction = Qt.LayoutDirection.RightToLeft if _is_rtl else Qt.LayoutDirection.LeftToRight
        self.setLayoutDirection(_direction)
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(15, 23, 42, 0.97);
            }
        """)

        # --- Storage for comments ---
        self.comments = []  # list of strings

        _BTN = """
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
            }
        """

        # --- Layouts ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # --- Title ---
        title = QLabel(t("comment_label"))
        title.setStyleSheet(
            "font-size: 15px; font-weight: bold;"
            " color: #E2EAF4; background: transparent;"
        )
        main_layout.addWidget(title)

        # --- Text input ---
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setLayoutDirection(_direction)
        if _is_rtl:
            from PyQt6.QtGui import QTextOption, QTextBlockFormat
            # Document-level default: RTL direction
            opt = QTextOption()
            opt.setTextDirection(Qt.LayoutDirection.RightToLeft)
            self.text_edit.document().setDefaultTextOption(opt)
            # Initial paragraph block: RTL flow + right alignment
            # setAlignment() alone only changes visual alignment, not text flow direction.
            # setLayoutDirection on the block format is what makes the cursor start from
            # the right and Hebrew text flow RTL.
            cursor = self.text_edit.textCursor()
            fmt = QTextBlockFormat()
            fmt.setAlignment(Qt.AlignmentFlag.AlignRight)
            fmt.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            cursor.setBlockFormat(fmt)
            self.text_edit.setTextCursor(cursor)
            # Qt6 hardcodes AlignLeft for placeholder — bypass with an overlay label.
            # setAlignment() on QLabel is ignored when a stylesheet is applied;
            # use HTML inline style instead which is always honored.
            self._ph_label = QLabel(self.text_edit.viewport())
            self._ph_label.setTextFormat(Qt.TextFormat.RichText)
            self._ph_label.setText(
                f'<div style="text-align:right; direction:rtl;">'
                f'{t("comment_placeholder")}</div>'
            )
            self._ph_label.setWordWrap(True)
            self._ph_label.setStyleSheet(
                "color: rgba(226,234,244,0.45); font-size: 14px;"
                " background: transparent; padding: 6px;"
            )
            self._ph_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._ph_label.raise_()
            self.text_edit.textChanged.connect(self._update_placeholder_visibility)
            self.text_edit.viewport().installEventFilter(self)
        else:
            self.text_edit.setPlaceholderText(t("comment_placeholder"))
            self._ph_label = None
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 0.08);
                color: #E2EAF4;
                font-size: 18px;
                border: 1px solid rgba(148, 163, 184, 0.30);
                border-radius: 8px;
                padding: 6px;
            }
        """)
        main_layout.addWidget(self.text_edit)

        # --- Buttons row ---
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)

        self.save_btn = QPushButton(" " + t("comment_save_btn"))
        self.save_btn.setIcon(_icon("save.svg"))
        self.save_btn.setIconSize(QSize(16, 16))
        self.save_btn.setFixedHeight(34)
        self.save_btn.setStyleSheet(_BTN)

        self.close_btn = QPushButton(" " + t("comment_close_btn"))
        self.close_btn.setIcon(_icon("close_grey.png"))
        self.close_btn.setIconSize(QSize(16, 16))
        self.close_btn.setFixedHeight(34)
        self.close_btn.setStyleSheet(_BTN)

        buttons_row.addWidget(self.save_btn)
        buttons_row.addWidget(self.close_btn)
        buttons_row.addStretch(1)
        main_layout.addLayout(buttons_row)

        # --- Comments list ---
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(148, 163, 184, 0.20);
                border-radius: 8px;
                color: #E2EAF4;
                font-size: 13px;
            }
            QListWidget::item {
                border-bottom: 1px solid rgba(148, 163, 184, 0.10);
            }
        """)
        main_layout.addWidget(self.list_widget, stretch=1)

        # --- Connections ---
        self.save_btn.clicked.connect(self.add_comment)
        self.close_btn.clicked.connect(self.close)



    # ------------------------------------------------------------------ #
    def _update_placeholder_visibility(self):
        if self._ph_label is not None:
            self._ph_label.setVisible(not self.text_edit.toPlainText())

    def showEvent(self, event):
        super().showEvent(event)
        if self._ph_label is not None:
            QTimer.singleShot(0, self._sync_ph_geometry)

    def _sync_ph_geometry(self):
        if self._ph_label is not None:
            self._ph_label.setGeometry(self.text_edit.viewport().rect())
            self._ph_label.raise_()

    def eventFilter(self, obj, event):
        if self._is_rtl and self._ph_label is not None and obj is self.text_edit.viewport():
            if event.type() == QEvent.Type.Resize:
                self._ph_label.setGeometry(obj.rect())
                self._ph_label.raise_()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------ #
    def add_comment(self):
        """Add a new comment to the list."""
        text = self.text_edit.toPlainText().strip()
        if not text:
            return

        self.comments.append(text)
        self.text_edit.clear()
        self.refresh_list()

    def edit_comment(self, index):
        """Edit an existing comment."""
        old = self.comments[index]
        self.text_edit.setText(old)
        del self.comments[index]
        self.refresh_list()

    def delete_comment(self, index):
        """Delete a comment."""
        del self.comments[index]
        self.refresh_list()
        self.save_comments()

    def refresh_list(self):
        """Refresh comment list display."""
        self.list_widget.clear()
        for i, text in enumerate(self.comments):
            item_widget = QWidget()
            row = QHBoxLayout(item_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)

            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #E2EAF4; background: transparent; font-size: 16px;")

            _MINI = """
                QPushButton {
                    background: rgba(255,255,255,0.08);
                    color: #E2EAF4; border-radius: 6px;
                    border: 1px solid rgba(148,163,184,0.25);
                    font-size: 14px;
                }
                QPushButton:hover {
                    background: rgba(0,206,209,0.25);
                    border: 1px solid rgba(0,206,209,0.70);
                }
            """

            edit_btn = QPushButton("✏")
            edit_btn.setFixedSize(30, 30)
            edit_btn.setStyleSheet(_MINI)
            edit_btn.clicked.connect(lambda _, x=i: self.edit_comment(x))

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(30, 30)
            del_btn.setStyleSheet(_MINI)
            del_btn.clicked.connect(lambda _, x=i: self.delete_comment(x))

            row.addWidget(lbl, stretch=1)
            row.addWidget(edit_btn)
            row.addWidget(del_btn)

            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, item_widget)

    # ------------------------------------------------------------------ #
    # Persistence (temporary – can later be linked to patient/session)
    # ------------------------------------------------------------------ #
    def save_comments(self):
        """Save comments in memory for this session."""
        pass

    def load_comments(self):
        """Load comments from memory (placeholder)."""
        self.refresh_list()

    def clear_all(self):
        """Clear all comments stored inside the popup."""
        self.comments = []
        self.refresh_list()
        self.text_edit.clear()
