import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})
    property string message: ""
    property string okText: ""

    signal confirmed()

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    standardButtons: Dialog.NoButton
    width: 420
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        Label {
            Layout.fillWidth: true
            text: dialog.message
            wrapMode: Text.Wrap
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: dialog.okText.length > 0
                  ? dialog.okText
                  : (dialog.strings.confirm_ok || "")
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                dialog.close()
                dialog.confirmed()
            }
        }
        AppButton {
            text: dialog.strings.confirm_cancel || ""
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
