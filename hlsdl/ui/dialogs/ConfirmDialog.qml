import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})
    property string message: ""
    property string okText: ""
    property bool destructive: false

    signal confirmed()

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    standardButtons: Dialog.NoButton
    header: null
    footer: null
    background: Rectangle { color: "transparent"; radius: 24 }
    width: 484
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0
    closePolicy: Popup.CloseOnEscape

    contentItem: ConfirmSurface {
        width: dialog.width
        height: implicitHeight
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        appRoot: dialog.appRoot
        strings: dialog.strings
        dialog: dialog
        title: dialog.title
        message: dialog.message
        destructive: dialog.destructive
        iconText: dialog.destructive ? "!" : "?"
        acceptText: dialog.okText.length > 0
                    ? dialog.okText
                    : (dialog.strings.confirm_ok || "")
        cancelText: dialog.strings.confirm_cancel || ""
        closeText: dialog.strings.dlg_error_close || ""
        showClose: true
        onAccepted: dialog.confirmed()
    }
}
