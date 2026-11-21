import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../motion.js" as Motion

Button {
    id: control

    property var theme: null
    property string tip: ""
    property bool danger: false
    property string kind: "maximize"

    readonly property color fgColor: danger && (hovered || down) && theme
                                       ? theme.onAccent
                                       : (theme ? theme.text : "#ffffff")
    readonly property color surfaceColor: down
                                          ? (danger && theme
                                             ? Qt.darker(theme.dangerFill, 1.28)
                                             : (theme ? Qt.darker(theme.hover, 1.25) : "#252b31"))
                                          : (hovered
                                             ? (danger && theme ? theme.dangerFill
                                                                : (theme ? theme.hover : "#30363d"))
                                             : "transparent")

    implicitWidth: 46
    implicitHeight: 30
    padding: 0
    // Controles de janela não devem reter foco após clique do mouse; Tab
    // continua funcionando e o anel de foco só aparece via teclado.
    focusPolicy: Qt.TabFocus
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.name: tip
    scale: down ? 0.90 : 1.0
    Behavior on scale { NumberAnimation { duration: Motion.press; easing.type: Easing.OutQuad } }

    AppToolTip {
        target: control
        title: control.tip
        available: control.tip.length > 0
        delay: 500
        // Bolha compacta: os três controles ficam a 46 px um do outro; um
        // tooltip largo cobria a área dos botões vizinhos.
        minWidth: 96
        maxWidth: 150
    }

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    background: Rectangle {
        radius: 6
        color: control.surfaceColor
        border.width: control.visualFocus ? 1 : 0
        border.color: theme ? theme.accentText : "#93c5fd"
        Behavior on color { ColorAnimation { duration: Motion.fast; easing.type: Easing.OutQuad } }
    }

    contentItem: Item {
        anchors.centerIn: parent
        width: 14
        height: 14

        // Minimizar: uma linha horizontal curta.
        Rectangle {
            visible: control.kind === "minimize"
            anchors.centerIn: parent
            width: 11
            height: 1.5
            radius: 0.75
            color: control.fgColor
        }

        // Maximizar: um quadrado vazado.
        Rectangle {
            visible: control.kind === "maximize"
            anchors.centerIn: parent
            width: 10
            height: 10
            color: "transparent"
            border.width: 1.25
            border.color: control.fgColor
        }

        // Restaurar: dois quadrados sobrepostos.
        Item {
            visible: control.kind === "restore"
            anchors.centerIn: parent
            width: 13
            height: 13

            Rectangle {
                x: 3
                y: 0
                width: 9
                height: 9
                color: "transparent"
                border.width: 1.25
                border.color: control.fgColor
            }
            Rectangle {
                x: 0
                y: 3
                width: 9
                height: 9
                color: control.surfaceColor
                border.width: 1.25
                border.color: control.fgColor
            }
        }

        // Fechar: X desenhado em dois traços.
        Item {
            visible: control.kind === "close"
            anchors.centerIn: parent
            width: 12
            height: 12

            Rectangle {
                anchors.centerIn: parent
                width: 12
                height: 1.4
                radius: 0.7
                rotation: 45
                color: control.fgColor
            }
            Rectangle {
                anchors.centerIn: parent
                width: 12
                height: 1.4
                radius: 0.7
                rotation: -45
                color: control.fgColor
            }
        }
    }
}
