import QtQuick
import QtQuick.Layouts

// Cabeçalho de tabela ordenável, com estado visual, foco por teclado e
// tooltip explicando a ordenação. O cabeçalho participa do mesmo RowLayout do
// delegate, com largura fixa compartilhada pela página, para não desalinhar.
Item {
    id: root
    objectName: "sortHeader_" + sortKey

    property string label: ""
    property string sortKey: ""
    property string activeKey: ""
    property bool ascending: true
    property string tipTitle: ""
    property string tipText: ""
    property string tipFooter: ""
    property string sortStateText: ""
    property int horizontalAlignment: Text.AlignLeft
    // Recuo only do texto (não do fundo), para alinhar com células que têm
    // miniatura/ícone à esquerda sem perder a área clicável da coluna.
    property int labelLeftMargin: 0
    property color textColor: "#202428"
    property color mutedColor: "#5b6570"
    property color hoverColor: "#e6eaee"
    property color accentColor: "#0d47a1"

    signal activated()

    readonly property bool active: sortKey.length > 0 && activeKey === sortKey
    implicitHeight: 36
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: label + (active && sortStateText.length > 0
                             ? ", " + sortStateText : "")
    Accessible.description: tipText
    Accessible.onPressAction: activate()

    function activate() {
        if (sortKey.length > 0) {
            activated()
            forceActiveFocus()
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.active ? Qt.rgba(root.accentColor.r, root.accentColor.g,
                                     root.accentColor.b, 0.10)
                           : (headerHover.hovered ? root.hoverColor : "transparent")
        border.width: root.activeFocus ? 1 : 0
        border.color: root.accentColor
        Behavior on color { ColorAnimation { duration: 90 } }
    }

    // Colunas centralizadas: o rótulo fica no centro exato da coluna e a seta
    // cresce para a direita sem deslocar o rótulo.
    Item {
        anchors.fill: parent
        visible: root.horizontalAlignment === Text.AlignHCenter

        Text {
            id: centeredLabel
            anchors.centerIn: parent
            width: Math.min(implicitWidth, root.width - 26)
            text: root.label
            color: root.textColor
            font.pixelSize: 13
            font.bold: true
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
        }
        Text {
            anchors.left: centeredLabel.right
            anchors.leftMargin: 3
            anchors.verticalCenter: parent.verticalCenter
            text: root.active ? (root.ascending ? "▲" : "▼") : "↕"
            color: root.active ? root.accentColor : root.mutedColor
            opacity: root.active ? 1.0 : (headerHover.hovered ? 0.7 : 0.0)
            font.pixelSize: root.active ? 10 : 11
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 4 + root.labelLeftMargin
        anchors.rightMargin: 4
        spacing: 4
        visible: root.horizontalAlignment !== Text.AlignHCenter

        Text {
            Layout.maximumWidth: root.width - root.labelLeftMargin - 32
            text: root.label
            color: root.textColor
            font.pixelSize: 13
            font.bold: true
            elide: Text.ElideRight
            verticalAlignment: Text.AlignVCenter
        }
        Text {
            Layout.preferredWidth: 14
            text: root.active ? (root.ascending ? "▲" : "▼") : "↕"
            color: root.active ? root.accentColor : root.mutedColor
            opacity: root.active ? 1.0 : (headerHover.hovered ? 0.7 : 0.0)
            font.pixelSize: root.active ? 10 : 11
            verticalAlignment: Text.AlignVCenter
            horizontalAlignment: Text.AlignHCenter
        }
        Item {
            Layout.fillWidth: true
        }
    }

    HoverHandler {
        id: headerHover
        cursorShape: root.sortKey.length > 0 ? Qt.PointingHandCursor : Qt.ArrowCursor
    }
    TapHandler {
        enabled: root.sortKey.length > 0
        acceptedButtons: Qt.LeftButton
        onTapped: root.activate()
    }
    Keys.onSpacePressed: root.activate()
    Keys.onReturnPressed: root.activate()
    Keys.onEnterPressed: root.activate()

    AppToolTip {
        target: root
        title: root.tipTitle.length > 0 ? root.tipTitle : root.label
        text: root.tipText
        footer: root.tipFooter
        showOnFocus: false
        available: root.sortKey.length > 0 && (root.tipText.length > 0
                                               || root.tipFooter.length > 0)
    }
}
