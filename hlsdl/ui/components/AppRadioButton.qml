import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

RadioButton {
    id: control
    property string tipTitle: ""
    property string tipText: ""
    property string tipShortcut: ""
    property bool tipEnabled: true
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    AppToolTip {
        target: control
        title: control.tipTitle
        text: control.tipText
        shortcut: control.tipShortcut
        available: control.tipEnabled && control.enabled
    }
}
