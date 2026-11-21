import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

// Mini-formulário de opções do lote. Diferente da Playlist, é um modal
// compacto de tamanho fixo: os controles não se beneficiam de maximizar ou
// redimensionar a janela.
Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    width: 560
    height: 380
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    objectName: "batchOptionsDialog"

    contentItem: AppDialogSurface {
        id: batchOptionsSurface
        objectName: "batchOptionsSurface"
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        dialog: dialog
        appRoot: dialog.appRoot
        strings: dialog.strings
        title: dialog.strings.batch_options || ""
        subtitle: dialog.strings.batch_options_hint || ""
        iconSource: dialog.appRoot ? dialog.appRoot.iconPath("file") : ""
        showCloseButton: true
        closeText: dialog.strings.dlg_error_close || ""
        resizable: false
        draggable: false
        width: dialog.width
        height: dialog.height

        RowLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: 620
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            visible: bridge.formatMode !== "audio_only"
            Label { text: dialog.strings.quality_label; Layout.fillWidth: true; font.pixelSize: 14 }
            AppQualityCombo {
                strings: dialog.strings
                Layout.alignment: Qt.AlignVCenter
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: 620
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            Label { text: dialog.strings.container_label; Layout.fillWidth: true; font.pixelSize: 14 }
            AppContainerCombo { Layout.alignment: Qt.AlignVCenter }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: 620
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            visible: bridge.formatMode !== "audio_only"
            Label { text: dialog.strings.codec_label; Layout.fillWidth: true; font.pixelSize: 14 }
            AppCodecCombo {
                strings: dialog.strings
                Layout.alignment: Qt.AlignVCenter
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.maximumWidth: 620
            Layout.alignment: Qt.AlignHCenter
            spacing: 12
            visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
            Label { text: dialog.strings.compress_label; Layout.fillWidth: true; font.pixelSize: 14 }
            AppCompressCombo {
                strings: dialog.strings
                Layout.alignment: Qt.AlignVCenter
            }
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 4
            spacing: 8
            Item { Layout.fillWidth: true }
            AppButton {
                text: dialog.strings.dlg_error_close || ""
                variant: "secondary"
                dangerHover: true
                icon.source: dialog.appRoot.iconPath("cancel")
                icon.width: 15
                icon.height: 15
                display: AbstractButton.TextBesideIcon
                onClicked: dialog.close()
            }
        }
    }
}
