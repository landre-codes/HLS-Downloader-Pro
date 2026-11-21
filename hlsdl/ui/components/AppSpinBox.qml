import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

SpinBox {
    id: control
    property string tipTitle: ""
    property string tipText: ""
    property string tipShortcut: ""
    property bool tipEnabled: true
    Accessible.description: tipText
    hoverEnabled: true
    background: Rectangle {
        readonly property bool _dark: typeof bridge !== "undefined" && bridge.dark
        implicitHeight: 56
        radius: 4
        color: _dark ? "#14191e" : "#e9eef2"
        border.width: 1
        border.color: control.activeFocus
                      ? (_dark ? "#93c5fd" : "#1d4ed8")
                      : (_dark ? "#3d4a55" : "#c6d0d8")
    }
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    AppToolTip {
        target: control
        title: control.tipTitle
        text: control.tipText
        shortcut: control.tipShortcut
        available: control.tipEnabled && control.enabled
    }
}
