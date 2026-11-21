import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Rectangle {
    id: hero

    property var theme: null
    property string title: ""
    property string description: ""
    property bool compact: false
    default property alias actions: actionsRow.data
    readonly property bool hasActions: actionsRow.children.length > 0

    implicitHeight: compact ? (hasActions ? 58 : 46) : 96
    radius: 11
    clip: true
    color: theme ? theme.heroTo : "transparent"
    border.width: 1
    border.color: theme ? theme.heroBorder : "#304152"
    gradient: Gradient {
        orientation: Gradient.Horizontal
        GradientStop {
            position: 0.0
            color: hero.theme ? hero.theme.heroFrom : "#1b2b38"
        }
        GradientStop {
            position: 1.0
            color: hero.theme ? hero.theme.heroTo : "#1b2633"
        }
    }

    // Brilho decorativo no canto, sem interferir no conteúdo.
    Rectangle {
        width: 190
        height: 190
        radius: 95
        x: hero.width - 110
        y: -112
        color: hero.theme ? hero.theme.accentFill : "#2563eb"
        opacity: 0.07
    }
    Rectangle {
        width: 4
        height: parent.height - 20
        radius: 2
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        color: hero.theme ? hero.theme.accentFill : "#2563eb"
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 22
        anchors.rightMargin: 14
        anchors.topMargin: hero.compact ? 6 : 9
        anchors.bottomMargin: hero.compact ? 6 : 9
        spacing: 12

        ColumnLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 2
            Label {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                text: hero.title
                color: hero.theme ? hero.theme.text : "#e6eef7"
                font.pixelSize: hero.compact ? 19 : 24
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                maximumLineCount: 1
                clip: true
            }
            Label {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                text: hero.description
                visible: !hero.compact && hero.description.length > 0
                color: hero.theme ? hero.theme.textSecondary : "#c2cbd3"
                font.pixelSize: 14
                font.weight: Font.Medium
                wrapMode: Text.Wrap
                maximumLineCount: 2
                elide: Text.ElideRight
                clip: true
            }
        }

        Row {
            id: actionsRow
            Layout.alignment: Qt.AlignVCenter
            spacing: 8
        }
    }
}
