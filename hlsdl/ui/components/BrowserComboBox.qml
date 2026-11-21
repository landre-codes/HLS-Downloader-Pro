import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Contêiner local para os logotipos dos navegadores usados na importação de
// cookies. Não baixa nada em runtime: usa apenas assets versionados.
AppComboBox {
    id: control

    property var appRoot: null

    function browserIcon(code) {
        return code ? Qt.resolvedUrl("../icons/browsers/" + code + ".svg") : ""
    }

    readonly property var currentBrowser: {
        if (!control.model || control.currentIndex < 0)
            return null
        return control.model[control.currentIndex] || null
    }

    contentItem: Item {
        implicitHeight: 32
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 28
            spacing: 8
            Rectangle {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                Layout.alignment: Qt.AlignVCenter
                radius: 8
                color: "#ffffff"
                border.width: 1
                border.color: control.appRoot
                              ? control.appRoot.theme.cardBorder : "#d8e1ee"
                Image {
                    anchors.centerIn: parent
                    width: 24
                    height: 24
                    source: control.currentBrowser
                            ? control.browserIcon(control.currentBrowser.icon) : ""
                    sourceSize.width: 48
                    sourceSize.height: 48
                    fillMode: Image.PreserveAspectFit
                    mipmap: true
                    smooth: true
                }
            }
            Label {
                Layout.fillWidth: true
                text: control.displayText
                elide: Text.ElideRight
                font: control.font
                color: control.enabled
                       ? (control.appRoot ? control.appRoot.theme.text : "#1f2937")
                       : (control.appRoot ? control.appRoot.theme.textMuted : "#626b75")
                verticalAlignment: Text.AlignVCenter
            }
        }
    }

    delegate: ItemDelegate {
        width: control.width
        implicitHeight: 40
        highlighted: control.highlightedIndex === index

        contentItem: RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 8
            Rectangle {
                Layout.preferredWidth: 32
                Layout.preferredHeight: 32
                Layout.alignment: Qt.AlignVCenter
                radius: 8
                color: "#ffffff"
                border.width: 1
                border.color: control.appRoot
                              ? control.appRoot.theme.cardBorder : "#d8e1ee"
                Image {
                    anchors.centerIn: parent
                    width: 24
                    height: 24
                    source: modelData && modelData.icon
                            ? control.browserIcon(modelData.icon) : ""
                    sourceSize.width: 48
                    sourceSize.height: 48
                    fillMode: Image.PreserveAspectFit
                    mipmap: true
                    smooth: true
                }
            }
            Label {
                Layout.fillWidth: true
                text: modelData && modelData.name !== undefined
                      ? String(modelData.name) : String(modelData)
                elide: Text.ElideRight
                font.pixelSize: 13
                color: control.appRoot ? control.appRoot.theme.text : "#1f2937"
            }
        }
    }
}
