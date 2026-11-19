import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ToolButton {
    id: control
    readonly property bool _darkTheme: typeof bridge !== "undefined" && bridge.dark
    property string tipTitle: ""
    property string tipText: ""
    property string tipShortcut: ""
    property bool tipEnabled: true
    Accessible.description: tipText
    AppToolTip {
        target: control
        title: control.tipTitle
        text: control.tipText
        shortcut: control.tipShortcut
        available: control.tipEnabled && control.enabled
    }
    Material.foreground: enabled
                        ? (_darkTheme ? "#f2f4f6" : "#202428")
                        : (_darkTheme ? "#8b959e" : "#6f7882")
    scale: down && enabled ? 0.94 : 1.0
    Behavior on scale { NumberAnimation { duration: 70; easing.type: Easing.OutQuad } }
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    background: Rectangle {
        radius: 4
        color: !control.enabled
               ? "transparent"
               : (control.down
                  ? (control._darkTheme ? "#323c46" : "#d8dfe6")
                  : (control.hovered
                     ? (control._darkTheme ? "#2a323a" : "#e6eaee")
                     : "transparent"))
        Behavior on color { ColorAnimation { duration: 90; easing.type: Easing.OutQuad } }
    }
}
