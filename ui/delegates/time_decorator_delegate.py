from PyQt5.QtCore import QLocale, QObject
from PyQt5.QtWidgets import QStyledItemDelegate


class TimeDecoratorDelegate(QStyledItemDelegate):
    def __init__(self, /, parent: QObject | None) -> None:
        super().__init__(parent)

    def displayText(self, value: str, _: QLocale) -> str:
        if value == "-inf":
            return "Distant Future"
        elif value == "inf":
            return "Distant Past"

        return value
