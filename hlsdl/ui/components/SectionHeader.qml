import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Título de card com um ícone temático, usado nas configurações.
RowLayout {
    id: header

    property var theme: null
    property string iconSource: ""
    property string title: ""
    property string tipTitle: ""
    property string tipText: ""

    spacing: 9
    implicitHeight: 28

    AppToolTip {
        target: header
        title: header.tipTitle.length > 0 ? header.tipTitle : header.title
        text: header.tipText
        available: header.tipText.length > 0
    }

    Rectangle {
        visible: header.iconSource.toString().length > 0
        Layout.preferredWidth: 28
        Layout.preferredHeight: 28
        Layout.alignment: Qt.AlignVCenter
        radius: 7
        // Placa azul-escura com contorno cobalto: os ícones claros mantêm
        // contraste tanto no tema claro quanto no escuro.
        color: header.theme && header.theme.dark ? "#0d1a2b" : "#102a43"
        border.width: 1
        border.color: "#3b82f6"

        Image {
            anchors.centerIn: parent
            source: header.iconSource
            sourceSize.width: 16
            sourceSize.height: 16
        }
    }

    Label {
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        text: header.title
        font.pixelSize: 15
        font.weight: Font.DemiBold
        elide: Text.ElideRight
        color: header.theme ? header.theme.text : "#1f2937"
    }
}
