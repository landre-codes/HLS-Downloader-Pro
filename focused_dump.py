"""Dump focado: geometrias do TabBar, SwipeView e páginas."""

import os
import sys

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtWidgets import QApplication

from main import Bridge, default_output_folder
from worker import DownloadModel, QueueManager

app = QApplication(sys.argv)
app.setFont(QFont("Segoe UI", 10))

model = DownloadModel([])
manager = QueueManager(model, outdir=default_output_folder())
bridge = Bridge(manager, default_output_folder())

engine = QQmlApplicationEngine()
engine.rootContext().setContextProperty("downloadModel", model)
engine.rootContext().setContextProperty("bridge", bridge)
engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui.qml")))
root = engine.rootObjects()[0]


def walk(item, depth=0, max_depth=6):
    name = item.metaObject().className()
    vis = "" if item.isVisible() else " [INVISIVEL]"
    print(
        f"{'  ' * depth}{name} x={item.x():.0f} y={item.y():.0f} w={item.width():.0f} h={item.height():.0f}{vis}"
    )
    if depth < max_depth:
        for c in item.childItems():
            walk(c, depth + 1, max_depth)


def do_dump():
    root.show()
    QTimer.singleShot(800, dump_targets)


def dump_targets():
    for kind, want in (("TabBar", "TabBar"), ("SwipeView", "SwipeView")):
        for item in root.findChildren(QQuickItem):
            cls = item.metaObject().className()
            if want in cls and "QMLTYPE" in cls or cls == want:
                print(f"--- {kind} ---")
                walk(item, max_depth=2)
                break
    # páginas do SwipeView
    for item in root.findChildren(QQuickItem):
        if "QQuickListView" in item.metaObject().className():
            print("--- ListView (SwipeView interno?) ---")
            walk(item, max_depth=1)
    os._exit(0)


QTimer.singleShot(2500, do_dump)
app.exec()
