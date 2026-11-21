import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Seletor de idioma com bandeira local e nome no próprio idioma.
// A bandeira é apenas um apoio visual; o texto continua sendo a identidade.
AppComboBox {
    id: control

    property var appRoot: null

    function flagSource(code) {
        return code ? Qt.resolvedUrl("../icons/flags/" + code + ".svg") : ""
    }

    readonly property var currentLanguage: {
        if (!control.model || control.currentIndex < 0)
            return null
        return control.model[control.currentIndex] || null
    }

    contentItem: Item {
        implicitHeight: 28
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 28
            spacing: 8
            Image {
                Layout.preferredWidth: 20
                Layout.preferredHeight: 14
                source: control.currentLanguage
                        ? control.flagSource(control.currentLanguage.flag) : ""
                sourceSize.width: 20
                sourceSize.height: 14
                fillMode: Image.PreserveAspectFit
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
        implicitHeight: 36
        highlighted: control.highlightedIndex === index

        contentItem: RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 8
            anchors.rightMargin: 8
            spacing: 8
            Image {
                Layout.preferredWidth: 20
                Layout.preferredHeight: 14
                source: modelData && modelData.flag
                        ? control.flagSource(modelData.flag) : ""
                sourceSize.width: 20
                sourceSize.height: 14
                fillMode: Image.PreserveAspectFit
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
