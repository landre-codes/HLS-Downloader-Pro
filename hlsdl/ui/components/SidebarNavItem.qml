import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Item de navegação da barra lateral. Mantém foco, teclado, tooltip e
// acessibilidade; no modo compacto exibe apenas o ícone.
Button {
    id: item

    property var theme: null
    property var appRoot: null
    property bool expanded: true
    property bool active: false
    property string iconName: ""
    property string label: ""
    property string tipTitle: ""
    property string tipText: ""
    property int badge: 0

    signal activated()

    implicitHeight: 46
    padding: 0
    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    Accessible.name: label + (badge > 0 ? " (" + badge + ")" : "")

    readonly property bool _dark: theme && theme.dark !== undefined
                                  ? theme.dark
                                  : (typeof bridge !== "undefined" && bridge.dark)
    readonly property color _text: active
                                  ? (theme ? theme.accentText
                                           : (_dark ? "#93c5fd" : "#1d4ed8"))
                                  : (theme ? theme.text
                                           : (_dark ? "#e6eef7" : "#1f2937"))
    readonly property color _hover: theme ? theme.hover
                                          : (_dark ? "#273748" : "#dfe4e8")
    readonly property color _activeBg: theme ? theme.rowHighlight
                                             : (_dark ? "#1f3a5f" : "#dceafe")
    readonly property color _divider: theme ? theme.divider
                                            : (_dark ? "#304152" : "#d8e1ee")
    readonly property color _accent: theme ? theme.accentFill : "#2563eb"

    background: Rectangle {
        anchors.fill: parent
        radius: 8
        color: item.active ? item._activeBg
                           : item.hovered ? item._hover : "transparent"
        border.width: item.activeFocus ? 1 : 0
        border.color: item.theme ? item.theme.accentText : "#1d4ed8"
        Behavior on color { ColorAnimation { duration: 110 } }

        Rectangle {
            visible: item.active
            width: 3
            height: 22
            radius: 1.5
            anchors.left: parent.left
            anchors.leftMargin: 2
            anchors.verticalCenter: parent.verticalCenter
            color: item._accent
        }
    }

    contentItem: Item {
        implicitWidth: item.width
        implicitHeight: item.height
        width: item.width
        height: item.height
        clip: true

        // Mesmo eixo do ícone nos dois modos: 14 px + 20 px = centro exato
        // da rail compacta de 48 px; na expandida, inicia o texto em 44 px.
        RowLayout {
            visible: item.expanded
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 10
            spacing: 10

            Image {
                Layout.preferredWidth: 20
                Layout.preferredHeight: 20
                source: item.appRoot ? item.appRoot.iconPath(item.iconName) : ""
                sourceSize.width: 20
                sourceSize.height: 20
                fillMode: Image.PreserveAspectFit
            }
            Label {
                Layout.fillWidth: true
                text: item.label
                color: item._text
                font.pixelSize: 12
                font.weight: item.active ? Font.DemiBold : Font.Normal
                elide: Text.ElideRight
                maximumLineCount: 1
                opacity: item.expanded ? 1 : 0
                visible: item.expanded || opacity > 0.01
                Behavior on opacity {
                    NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                }
            }
            Rectangle {
                visible: item.expanded && item.badge > 0
                Layout.preferredWidth: Math.max(20, badgeText.implicitWidth + 8)
                Layout.preferredHeight: 18
                radius: 9
                color: item._accent
                Label {
                    id: badgeText
                    anchors.centerIn: parent
                    text: item.badge > 99 ? "99+" : String(item.badge)
                    color: "#ffffff"
                    font.pixelSize: 9
                    font.bold: true
                }
            }
        }

        Image {
            visible: !item.expanded
            anchors.centerIn: parent
            width: 20
            height: 20
            source: item.appRoot ? item.appRoot.iconPath(item.iconName) : ""
            sourceSize.width: 20
            sourceSize.height: 20
            fillMode: Image.PreserveAspectFit
        }

        Rectangle {
            visible: !item.expanded && item.badge > 0
            width: 8
            height: 8
            radius: 4
            color: item._accent
            anchors.top: parent.top
            anchors.right: parent.right
            anchors.topMargin: 8
            anchors.rightMargin: 8
        }
    }

    AppToolTip {
        target: item
        title: item.tipTitle.length > 0 ? item.tipTitle : item.label
        text: item.tipText
        available: item.enabled
    }

    onClicked: item.activated()
}
