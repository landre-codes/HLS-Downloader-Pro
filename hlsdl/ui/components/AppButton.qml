import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../motion.js" as Motion

Button {
    id: control
    readonly property bool _darkTheme: typeof bridge !== "undefined" && bridge.dark
    // Variantes semânticas: primary (cobalto), tonal (azul-acinzentado),
    // secondary (contorno), tertiary (transparente), success, warning e danger.
    // As preenchidas usam texto/ícone brancos; o verde fica reservado a sucesso.
    // "auto" preserva a compatibilidade com o antigo `highlighted`.
    property string variant: "auto"
    property string size: "normal"
    property int radius: 8
    // Tooltip rico: título opcional + descrição + atalho. Sem `tipText`, o
    // texto visível do botão vira o título (sem tooltip redundante).
    property string tipTitle: ""
    property string tipText: ""
    property string tipShortcut: ""
    property bool tipEnabled: true
    // Botões destrutivos que não são vermelhos em repouso (fechar, remover,
    // limpar) ganham apenas o hover avermelhado.
    property bool dangerHover: false
    readonly property string _variant: variant === "auto"
                                          ? (highlighted ? "primary" : "tertiary")
                                          : variant
    readonly property bool _primary: _variant === "primary"
    readonly property bool _danger: _variant === "danger"
    readonly property bool _success: _variant === "success"
    readonly property bool _warning: _variant === "warning"
    readonly property bool _tonal: _variant === "tonal"
    readonly property bool _secondary: _variant === "secondary"
    readonly property bool _filled: _primary || _danger || _success || _warning
    // Cobalto como acento de execução; estados semânticos ficam separados.
    readonly property color _filledBase: _primary ? "#2563eb"
                                       : _danger ? "#b42332"
                                       : _success ? "#15803d"
                                       : _warning ? "#b45309" : "transparent"
    readonly property color _filledHover: _primary ? "#1d4ed8"
                                        : _danger ? "#9f1d2b"
                                        : _success ? "#166534"
                                        : _warning ? "#92400e" : "transparent"
    readonly property color _filledDown: _primary ? "#1e40af"
                                       : _danger ? "#871927"
                                       : _success ? "#14532d"
                                       : _warning ? "#78350f" : "transparent"
    readonly property color _filledDisabled: _primary
                                             ? (_darkTheme ? "#2b3645" : "#dfe7f3")
                                             : _danger
                                               ? (_darkTheme ? "#47262b" : "#f0dbde")
                                               : _success
                                                 ? (_darkTheme ? "#243d2c" : "#d8e8dc")
                                                 : _warning
                                                   ? (_darkTheme ? "#4a3826" : "#f3e3d2")
                                                   : "transparent"
    // Superfície tonal para ações auxiliares (importar, colar, analisar).
    readonly property color _tonalBg: _darkTheme ? "#243447" : "#e4edfb"
    readonly property color _tonalHover: _darkTheme ? "#2b3f55" : "#d8e6fa"
    readonly property color _tonalDown: _darkTheme ? "#324960" : "#ccdcf7"
    readonly property color _tonalDisabled: _darkTheme ? "#202c3a" : "#eef3fa"
    readonly property bool _dangerHover: dangerHover && enabled
                                         && (hovered || down)
                                         && !_filled
    readonly property color _dangerHoverColor: _darkTheme ? "#4a2b2b" : "#fde8e8"
    readonly property color _dangerDownColor: _darkTheme ? "#5a3030" : "#f6d5d5"
    readonly property color _textColor: !enabled
                                       ? (_darkTheme ? "#8b959e" : "#5f6b78")
                                       : (_filled ? "#ffffff"
                                          : (_dangerHover
                                             ? (_darkTheme ? "#f87171" : "#b42332")
                                             : (_tonal
                                                ? (_darkTheme ? "#bfdbfe" : "#1d4ed8")
                                                : (_darkTheme ? "#e6eef7" : "#1f2937"))))
    Material.accent: _filled ? _filledBase
                             : (_darkTheme ? "#93c5fd" : "#1d4ed8")
    Material.foreground: _textColor
    Accessible.description: tipText
    hoverEnabled: true
    HoverHandler { cursorShape: Qt.PointingHandCursor }
    implicitHeight: size === "compact" ? 36 : 44
    leftPadding: size === "compact" ? 10 : 14
    rightPadding: size === "compact" ? 10 : 14
    font.pixelSize: size === "compact" ? 12 : 14
    font.weight: Font.Medium
    scale: down && enabled ? 0.98 : 1.0
    Behavior on scale { NumberAnimation { duration: Motion.press; easing.type: Easing.OutQuad } }

    background: Rectangle {
        anchors.fill: parent
        radius: control.radius
        border.width: control._secondary || control._tonal ? 1 : 0
        border.color: control._tonal
                      ? (control._darkTheme ? "#36506c" : "#c9dbf5")
                      : (control._darkTheme ? "#3a4c60" : "#cbd6e4")
        color: control._filled
               ? (!control.enabled
                  ? control._filledDisabled
                  : (control.down ? control._filledDown
                                  : (control.hovered ? control._filledHover
                                                     : control._filledBase)))
               : control._tonal
                   ? (!control.enabled
                      ? control._tonalDisabled
                      : (control.down ? control._tonalDown
                                      : (control.hovered ? control._tonalHover
                                                         : control._tonalBg)))
                   : control._secondary
                     ? (control._dangerHover
                        ? (control.down ? control._dangerDownColor
                                        : control._dangerHoverColor)
                        : (control.down
                           ? (control._darkTheme ? "#304255" : "#d4dfee")
                           : (control.hovered
                              ? (control._darkTheme ? "#273748" : "#e2e9f3")
                              : (control._darkTheme ? "#1b2633" : "#ffffff"))))
                     : (control.enabled && (control.down || control.hovered)
                        ? (control._dangerHover
                           ? (control.down ? control._dangerDownColor
                                           : control._dangerHoverColor)
                           : (control.down
                              ? (control._darkTheme ? "#304255" : "#d4dfee")
                              : (control._darkTheme ? "#273748" : "#e2e9f3")))
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
            spacing: (control.text.length > 0 && control.icon.source.toString().length > 0) ? 8 : 0
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
