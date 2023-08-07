from qtpy.QtCore import QSize
from qtpy.QtGui import QIcon, QColor, QBrush
from qtpy.QtWidgets import QListWidget, QListWidgetItem
from pathlib import Path

ICON_ROOT = Path(__file__).parent / "icons"
STYLES = r"""
    QListWidget{
        min-width: 340;
        background: none;
        font-size: 8pt;
        color: #eee;
    }
    QListWidget::item {
        width: 68;
        height: 85;
        margin: 1;
        padding: 4;
    }
    QListWidget::item::hover {
        background: #8A929C;
        width: 68;
        height: 85;
        margin: 1;
        padding: 4;
    }

"""

def _get_background_brush():
    background_color = QColor()
    background_color.setNamedColor("#414851")
    background = QBrush(1)
    background.setColor(background_color)

    return background

def _get_highlight_brush():
    highlight_color = QColor()
    highlight_color.setNamedColor("#68707a")
    highlight = QBrush(1)
    highlight.setColor(highlight_color)

    return highlight


def _get_icon(name):
    path = ICON_ROOT / f'{name.lower().replace(" ", "_")}.png'
    if not path.exists():
        return ""
    return str(path)

class ButtonGrid(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setMovement(self.Static)  # The items cannot be moved by the user.
        self.setViewMode(self.IconMode)  # make items icons
        self.setResizeMode(self.Adjust)  # relayout when view is resized.
        self.setUniformItemSizes(True)  # better performance
        self.setIconSize(QSize(64, 44))
        self.setWordWrap(True)
        self.setStyleSheet(STYLES)
        self.setSpacing(2)
        self.item_mapping = {}



    def addItem(self, label : str, tool_tip : str = None):
        if isinstance(label, QListWidgetItem):
            super().addItem(label)

        item = QListWidgetItem(QIcon(_get_icon(label)), label)
        self.item_mapping[label] = item
        item.setBackground(_get_background_brush())
        
        if tool_tip is not None:
            item.setToolTip(tool_tip)
        super().addItem(item)

    def addItems(self, labels) -> None:
        for label in labels:
            if hasattr(labels[label], "tool_tip"):
                self.addItem(label, labels[label].tool_tip)
            else:
                self.addItem(label)
