import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    title: strings.batch_options || ""
    width: 520
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    standardButtons: Dialog.NoButton

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            visible: bridge.formatMode !== "audio_only"
            Label { text: dialog.strings.quality_label; Layout.fillWidth: true; font.pixelSize: 13 }
            AppQualityCombo {
                strings: dialog.strings
                Layout.alignment: Qt.AlignVCenter
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            Label { text: dialog.strings.container_label; Layout.fillWidth: true; font.pixelSize: 13 }
            AppContainerCombo { Layout.alignment: Qt.AlignVCenter }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            visible: bridge.formatMode !== "audio_only"
            Label { text: dialog.strings.codec_label; Layout.fillWidth: true; font.pixelSize: 13 }
            AppCodecCombo {
                strings: dialog.strings
                Layout.alignment: Qt.AlignVCenter
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 12
            visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
            Label { text: dialog.strings.compress_label; Layout.fillWidth: true; font.pixelSize: 13 }
            AppCompressCombo {
                strings: dialog.strings
                Layout.alignment: Qt.AlignVCenter
            }
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: dialog.strings.dlg_error_close || ""
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
