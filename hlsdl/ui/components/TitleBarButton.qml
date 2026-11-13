import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Button {
    id: control

    property var theme: null
    property string tip: ""
    property bool danger: false
    property string kind: "maximize"

    readonly property color fgColor: danger && hovered && theme
                                       ? theme.onAccent
                                       : (theme ? theme.text : "#ffffff")
    readonly property color surfaceColor: hovered
                                          ? (danger && theme ? theme.dangerFill
                                                             : (theme ? theme.hover : "#30363d"))
                                          : (theme ? theme.titleBg : "#20252b")

    implicitWidth: 46
    implicitHeight: 30
    padding: 0
    focusPolicy: Qt.NoFocus
    hoverEnabled: true
    Accessible.role: Accessible.Button
    Accessible.name: tip

    ToolTip.text: tip
    ToolTip.visible: hovered
    ToolTip.delay: 450

    HoverHandler {
        cursorShape: Qt.PointingHandCursor
    }

    background: Rectangle {
        radius: 6
        color: control.hovered ? control.surfaceColor : "transparent"
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
