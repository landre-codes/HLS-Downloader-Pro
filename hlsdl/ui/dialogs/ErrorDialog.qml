import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})
    property string message: ""

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    title: strings.dlg_error || ""
    width: 540
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    standardButtons: Dialog.NoButton

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        Label {
            Layout.fillWidth: true
            text: dialog.message
            wrapMode: Text.Wrap
            font.pixelSize: 12
            color: dialog.appRoot ? dialog.appRoot.theme.errorText : "#c62828"
        }
        AppButton {
            text: dialog.strings.dlg_error_copy || ""
            onClicked: {
                bridge.copyLink(dialog.message)
                dialog.close()
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
