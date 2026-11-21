import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Superfície de confirmação centrada, inspirada nos modais do anexo:
// ícone circular suave, título/mensagem centralizados, dois botões largos
// e fechar no canto. Não usa cabeçalho em degradê nem arraste.
Item {
    id: surface

    property var theme: null
    property var appRoot: null
    property var strings: ({})
    property var dialog: null
    property string title: ""
    property string message: ""
    property string detail: ""
    property string iconText: "?"
    property bool destructive: false
    property bool warning: false
    property string acceptText: ""
    property string cancelText: ""
    property string acceptObjectName: ""
    property string cancelObjectName: ""
    property string cancelVariant: "secondary"
    property string closeText: ""
    property bool showCancel: true
    property bool showClose: true
    property string terminalTitle: ""
    property string terminalOutput: ""

    signal accepted()
    signal cancelled()
    default property alias extraContent: extraColumn.data

    readonly property bool _dark: theme && theme.dark !== undefined
                                  ? theme.dark
                                  : (typeof bridge !== "undefined" && bridge.dark)
    readonly property color cardColor: theme ? theme.cardBg
                                             : (_dark ? "#1b2633" : "#ffffff")
    readonly property color _cardBg: cardColor
    readonly property color _border: theme ? theme.cardBorder
                                           : (_dark ? "#304152" : "#d8e1ee")
    readonly property color _text: theme ? theme.text
                                         : (_dark ? "#e6eef7" : "#1f2937")
    readonly property color _muted: theme ? theme.textSecondary
                                          : (_dark ? "#c2cbd3" : "#4f5862")
    readonly property color _accent: theme ? theme.accentFill : "#2563eb"
    readonly property color _danger: theme ? theme.dangerFill : "#b42332"
    readonly property color _warning: theme ? theme.warningText : "#b45309"
    readonly property color _iconColor: destructive ? _danger
                                       : warning ? _warning : _accent
    readonly property color _iconBg: destructive
                                     ? (_dark ? "#4a2b2b" : "#fde8e8")
                                     : warning
                                       ? (_dark ? "#4a3826" : "#fdf0e3")
                                       : (_dark ? "#1e3350" : "#e3f2fd")

    function _close() {
        if (dialog)
            dialog.close()
    }

    implicitWidth: 484
    implicitHeight: card.height + 24
    width: implicitWidth

    // Halo suave em camadas, sem depender de efeitos gráficos externos.
    Rectangle {
        anchors.fill: card
        anchors.margins: -8
        radius: 32
        color: "#000000"
        opacity: 0.05
    }
    Rectangle {
        anchors.fill: card
        anchors.margins: -4
        radius: 28
        color: "#000000"
        opacity: 0.06
    }

    Rectangle {
        id: card
        x: 12
        y: 12
        width: surface.width - 24
        height: contentColumn.implicitHeight + 72
        radius: 24
        color: surface._cardBg
        border.width: 1
        border.color: surface._border

        ColumnLayout {
            id: contentColumn
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: 36
            spacing: 12

            Rectangle {
                Layout.alignment: Qt.AlignHCenter
                Layout.preferredWidth: 72
                Layout.preferredHeight: 72
                radius: 36
                color: surface._iconBg
                Label {
                    anchors.centerIn: parent
                    text: surface.iconText
                    color: surface._iconColor
                    font.pixelSize: 32
                    font.bold: true
                }
            }

            Label {
                Layout.fillWidth: true
                Layout.topMargin: 4
                text: surface.title
                color: surface._text
                font.pixelSize: 22
                font.bold: true
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: surface.message
                color: surface._muted
                font.pixelSize: 14
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
            }

            Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: surface.detail
                color: surface._muted
                font.pixelSize: 12
                wrapMode: Text.Wrap
            }

            ColumnLayout {
                id: extraColumn
                Layout.fillWidth: true
                spacing: 8
            }

            AppTerminalPanel {
                Layout.fillWidth: true
                visible: surface.terminalOutput.length > 0
                theme: surface.theme
                strings: surface.strings
                title: surface.terminalTitle
                output: surface.terminalOutput
                panelHeight: 110
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 10
                visible: surface.destructive

                AppButton {
                    objectName: surface.destructive ? surface.acceptObjectName : ""
                    Layout.fillWidth: true
                    Layout.preferredWidth: 0
                    Layout.preferredHeight: 48
                    radius: 10
                    text: surface.acceptText.length > 0
                          ? surface.acceptText
                          : (surface.strings.confirm_ok || "")
                    variant: "danger"
                    font.weight: Font.DemiBold
                    onClicked: {
                        surface.accepted()
                        surface._close()
                    }
                }
                AppButton {
                    objectName: surface.destructive ? surface.cancelObjectName : ""
                    Layout.fillWidth: true
                    Layout.preferredWidth: 0
                    Layout.preferredHeight: 48
                    radius: 10
                    visible: surface.showCancel
                    text: surface.cancelText.length > 0
                          ? surface.cancelText
                          : (surface.strings.confirm_cancel || "")
                    variant: "secondary"
                    font.weight: Font.DemiBold
                    onClicked: {
                        surface.cancelled()
                        surface._close()
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 10
                visible: !surface.destructive

                AppButton {
                    objectName: surface.destructive ? "" : surface.cancelObjectName
                    Layout.fillWidth: true
                    Layout.preferredWidth: 0
                    Layout.preferredHeight: 48
                    radius: 10
                    visible: surface.showCancel
                    text: surface.cancelText.length > 0
                          ? surface.cancelText
                          : (surface.strings.confirm_cancel || "")
                    variant: surface.cancelVariant
                    font.weight: Font.DemiBold
                    onClicked: {
                        surface.cancelled()
                        surface._close()
                    }
                }
                AppButton {
                    objectName: surface.destructive ? "" : surface.acceptObjectName
                    Layout.fillWidth: true
                    Layout.preferredWidth: 0
                    Layout.preferredHeight: 48
                    radius: 10
                    text: surface.acceptText.length > 0
                          ? surface.acceptText
                          : (surface.strings.confirm_ok || "")
                    variant: "primary"
                    font.weight: Font.DemiBold
                    onClicked: {
                        surface.accepted()
                        surface._close()
                    }
                }
            }
        }

        AppToolButton {
            visible: surface.showClose
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 12
            anchors.rightMargin: 12
            width: 32
            height: 32
            display: AbstractButton.TextOnly
            text: "\u00d7"
            font.pixelSize: 20
            tipTitle: surface.closeText.length > 0
                      ? surface.closeText
                      : (surface.strings.dlg_error_close || "Close")
            Accessible.name: tipTitle
            onClicked: {
                surface.cancelled()
                surface._close()
            }
        }
    }
}
