import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../motion.js" as Motion

Button {
    id: control
    readonly property bool _darkTheme: typeof bridge !== "undefined" && bridge.dark
    // Variantes semânticas: primary, secondary, tertiary, danger, icon.
    // "auto" preserva a compatibilidade com o antigo `highlighted`.
    property string variant: "auto"
    property string size: "normal"
    // Tooltip rico: título opcional + descrição + atalho. Sem `tipText`, o
    // texto visível do botão vira o título (sem tooltip redundante).
    property string tipTitle: ""
    property string tipText: ""
    property string tipShortcut: ""
    property bool tipEnabled: true
    readonly property string _variant: variant === "auto"
                                          ? (highlighted ? "primary" : "tertiary")
                                          : variant
    readonly property bool _primary: _variant === "primary"
    readonly property bool _danger: _variant === "danger"
    readonly property bool _secondary: _variant === "secondary"
    readonly property color _textColor: !enabled
                                       ? (_darkTheme ? "#8b959e" : "#6f7882")
                                       : ((_primary || _danger) ? "#ffffff"
                                                               : (_darkTheme ? "#f2f4f6" : "#202428"))
    Material.accent: _primary || _danger
                     ? "#1565c0"
                     : (_darkTheme ? "#90caf9" : "#0d47a1")
    Material.foreground: _textColor
    Accessible.description: tipText
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    implicitHeight: size === "compact" ? 36 : 44
    leftPadding: size === "compact" ? 10 : 14
    rightPadding: size === "compact" ? 10 : 14
    font.pixelSize: size === "compact" ? 12 : 14
    font.weight: Font.Medium
    scale: down && enabled ? 0.98 : 1.0
    Behavior on scale { NumberAnimation { duration: Motion.press; easing.type: Easing.OutQuad } }

    background: Rectangle {
        radius: 4
        border.width: control._secondary ? 1 : 0
        border.color: control._darkTheme ? "#33404a" : "#d7dde3"
        color: control._primary
               ? (!control.enabled
                  ? (control._darkTheme ? "#3a444d" : "#dfe3e6")
                  : (control.down ? "#0b3f8f"
                                  : (control.hovered ? "#1e88e5" : "#1565c0")))
               : control._danger
                 ? (!control.enabled
                    ? (control._darkTheme ? "#4a2b2b" : "#eadada")
                    : (control.down ? "#8e0000"
                                    : (control.hovered ? "#d32f2f" : "#b71c1c")))
                 : control._secondary
                   ? (control.down
                      ? (control._darkTheme ? "#323c46" : "#d8dfe6")
                      : (control.hovered
                         ? (control._darkTheme ? "#2a323a" : "#e6eaee")
                         : (control._darkTheme ? "#1d2329" : "#ffffff")))
                   : (control.enabled && (control.down || control.hovered)
                      ? (control.down
                         ? (control._darkTheme ? "#323c46" : "#d8dfe6")
                         : (control._darkTheme ? "#2a323a" : "#e6eaee"))
                      : "transparent")
        Behavior on color { ColorAnimation { duration: Motion.fast; easing.type: Easing.OutQuad } }
    }

    // Conteúdo explícito: o Material pinta o texto de botões highlighted como
    // branco mesmo quando desabilitados, o que desaparece no tema claro.
    AppToolTip {
        target: control
        title: control.tipTitle
        text: control.tipText
        shortcut: control.tipShortcut
        available: control.tipEnabled && control.enabled
    }

    contentItem: Item {
        implicitWidth: contentRow.implicitWidth
        implicitHeight: contentRow.implicitHeight
        Row {
            id: contentRow
            anchors.centerIn: parent
            spacing: (control.text.length > 0 && control.icon.source.toString().length > 0) ? 6 : 0
            Image {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.icon.source.toString().length > 0
                source: control.icon.source
                sourceSize.width: control.icon.width > 0 ? control.icon.width : 16
                sourceSize.height: control.icon.height > 0 ? control.icon.height : 16
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: control.display !== AbstractButton.IconOnly
                         && control.text.length > 0
                text: control.text
                color: control._textColor
                font: control.font
                elide: Text.ElideRight
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
