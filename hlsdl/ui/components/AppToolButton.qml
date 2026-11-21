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
    property bool tipShowOnFocus: true
    // Fechar/remover/excluir: fundo avermelhado somente no hover/pressão.
    property bool danger: false
    // Clique do mouse não deve roubar o foco da página; Tab continua acessível.
    focusPolicy: Qt.TabFocus
    Accessible.description: tipText
    AppToolTip {
        target: control
        title: control.tipTitle
        text: control.tipText
        shortcut: control.tipShortcut
        available: control.tipEnabled && control.enabled
        showOnFocus: control.tipShowOnFocus
    }
    Material.foreground: enabled
                        ? (control.danger && (control.hovered || control.down)
                           ? (_darkTheme ? "#f87171" : "#b42332")
                           : (_darkTheme ? "#e6eef7" : "#1f2937"))
                        : (_darkTheme ? "#8b959e" : "#6f7882")
    scale: down && enabled ? 0.94 : 1.0
    Behavior on scale { NumberAnimation { duration: 70; easing.type: Easing.OutQuad } }
    hoverEnabled: true
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    background: Rectangle {
        radius: 4
        color: !control.enabled
               ? "transparent"
               : control.danger
                 ? (control.down
                    ? (control._darkTheme ? "#5a3030" : "#f6d5d5")
                    : (control.hovered
                       ? (control._darkTheme ? "#4a2b2b" : "#fde8e8")
                       : "transparent"))
                 : (control.down
                    ? (control._darkTheme ? "#304255" : "#d8dfe6")
                    : (control.hovered
                       ? (control._darkTheme ? "#273748" : "#e6eaee")
                       : "transparent"))
        Behavior on color { ColorAnimation { duration: 90; easing.type: Easing.OutQuad } }
    }
}
