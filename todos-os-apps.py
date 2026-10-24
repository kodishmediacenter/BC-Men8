#!/usr/bin/env python3
"""Todos os Apps: lista todos os aplicativos instalados em tela cheia.

Setas = navegar | Enter = abrir | Esc = fechar | digitar = buscar pelo nome
Requer PySide6 (ou PyQt6 como alternativa).
"""
import configparser
import locale
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

try:
    from PySide6.QtCore import Qt, QSize
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import (QApplication, QListWidget, QListWidgetItem,
                                   QListView, QVBoxLayout, QLabel, QWidget)
except ImportError:
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import (QApplication, QListWidget, QListWidgetItem,
                                 QListView, QVBoxLayout, QLabel, QWidget)

APP_DIRS = [
    Path.home() / ".local/share/applications",
    Path.home() / ".local/share/flatpak/exports/share/applications",
    Path("/var/lib/flatpak/exports/share/applications"),
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
]

SELF_NAME = "Todos os Apps"


def localized(section, key, langs):
    for lang in langs:
        value = section.get(f"{key}[{lang}]")
        if value:
            return value
    return section.get(key, "")


def load_apps():
    lang_code = (locale.getlocale()[0] or "en_US")
    langs = [lang_code, lang_code.split("_")[0]]
    apps = {}
    for directory in APP_DIRS:  # diretórios do usuário vêm primeiro e têm prioridade
        if not directory.is_dir():
            continue
        for path in directory.glob("*.desktop"):
            if path.name in apps:
                continue
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.optionxform = str
            try:
                cp.read(path, encoding="utf-8")
                entry = cp["Desktop Entry"]
            except (configparser.Error, KeyError, UnicodeDecodeError):
                continue
            if entry.get("Type") != "Application":
                continue
            if entry.get("NoDisplay", "false").lower() == "true":
                continue
            if entry.get("Hidden", "false").lower() == "true":
                continue
            if entry.get("Terminal", "false").lower() == "true":
                continue
            name = localized(entry, "Name", langs)
            exec_line = entry.get("Exec", "")
            if not name or not exec_line or name == SELF_NAME:
                continue
            apps[path.name] = {
                "name": name,
                "exec": exec_line,
                "icon": entry.get("Icon", "application-x-executable"),
                "path": entry.get("Path") or None,
            }
    return sorted(apps.values(), key=lambda a: a["name"].lower())


def launch(app):
    cmd = re.sub(r"%%", "\0", app["exec"])
    cmd = re.sub(r"%[a-zA-Z]", "", cmd).replace("\0", "%")
    try:
        args = shlex.split(cmd)
        subprocess.Popen(args, cwd=app["path"], start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, ValueError) as err:
        print(f"Erro ao abrir {app['name']}: {err}", file=sys.stderr)
        return False


class Launcher(QWidget):
    def __init__(self, apps):
        super().__init__()
        self.setWindowTitle(SELF_NAME)
        self.setStyleSheet("""
            QWidget { background: #14161a; color: #eceff4; }
            QLabel { font-size: 34px; font-weight: bold; padding: 12px 24px; }
            QListWidget { border: none; font-size: 22px; outline: 0; padding: 12px 24px; }
            QListWidget::item { padding: 14px; border-radius: 14px; }
            QListWidget::item:selected { background: #3daee9; color: white; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(SELF_NAME))

        self.list = QListWidget()
        self.list.setViewMode(QListView.ViewMode.IconMode)
        self.list.setResizeMode(QListView.ResizeMode.Adjust)
        self.list.setMovement(QListView.Movement.Static)
        self.list.setIconSize(QSize(96, 96))
        self.list.setGridSize(QSize(190, 170))
        self.list.setWordWrap(True)
        self.list.setUniformItemSizes(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.list)

        for app in apps:
            icon = QIcon.fromTheme(app["icon"])
            if icon.isNull() and os.path.isfile(app["icon"]):
                icon = QIcon(app["icon"])
            if icon.isNull():
                icon = QIcon.fromTheme("application-x-executable")
            item = QListWidgetItem(icon, app["name"])
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            item.setData(Qt.ItemDataRole.UserRole, app)
            self.list.addItem(item)

        self.list.itemActivated.connect(self.open_item)
        self.list.itemClicked.connect(self.open_item)
        if self.list.count():
            self.list.setCurrentRow(0)
        self.list.setFocus()

    def open_item(self, item):
        if launch(item.data(Qt.ItemDataRole.UserRole)):
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    window = Launcher(load_apps())
    window.showFullScreen()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
