import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

ComboBox {
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
    // Popup com superfície opaca própria: evita herdar um fundo transparente
    // do estilo e mantém o mesmo azul-acinzentado do restante da UI.
    popup.background: Rectangle {
        readonly property bool _dark: typeof bridge !== "undefined" && bridge.dark
        implicitWidth: 200
        implicitHeight: 200
        radius: 4
        color: _dark ? "#1b2633" : "#ffffff"
        border.width: 1
        border.color: _dark ? "#304152" : "#d8e1ee"
    }
    popup.height: Math.min((control.count || 0) * 40 + 16, 380)
    popup.contentItem.ScrollIndicator.vertical.visible:
        popup.contentItem.contentHeight > popup.contentItem.height
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    AppToolTip {
        target: control
        title: control.tipTitle
        text: control.tipText
        shortcut: control.tipShortcut
        available: control.tipEnabled && control.enabled
    }
}
