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
    title: strings.compress_suggestions || ""
    width: 540
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    standardButtons: Dialog.NoButton

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        Label {
            Layout.fillWidth: true
            text: dialog.strings.compress_best_saving + "   ≈ -"
                  + dialog.appRoot.estimateSaving("av1") + "%"
            wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            text: dialog.strings.compress_best_balance + "   ≈ -"
                  + dialog.appRoot.estimateSaving("hevc") + "%"
            wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            text: dialog.strings.compress_best_compat + "   ≈ -"
                  + dialog.appRoot.estimateSaving("h264") + "%"
            wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            text: dialog.strings.compress_estimate_tip
            wrapMode: Text.Wrap
            font.pixelSize: 11
            color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
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
