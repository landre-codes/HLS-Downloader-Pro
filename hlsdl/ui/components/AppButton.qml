import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Button {
    Material.accent: highlighted
                     ? "#1565c0"
                     : (typeof bridge !== "undefined" && bridge.dark ? "#90caf9" : "#0d47a1")
    HoverHandler { cursorShape: Qt.PointingHandCursor }
}
