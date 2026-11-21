import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})
    property string pendingAction: ""
    property string pendingKey: ""
    property string pendingName: ""
    property bool pendingUpdate: false

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    title: strings.cfg_deps_title || ""
    header: null
    footer: null
    background: Rectangle { color: "transparent"; radius: 24 }
    width: 520
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape

    contentItem: ConfirmSurface {
        width: dialog.width
        height: implicitHeight
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        appRoot: dialog.appRoot
        strings: dialog.strings
        dialog: dialog
        title: dialog.title
        message: dialog.pendingAction === "all"
                 ? dialog.strings.dep_confirm_all
                 : dialog.strings.dep_confirm_task.replace(
                       "{name}", dialog.pendingName)
        detail: dialog.strings.dep_confirm_detail
        iconText: "!"
        destructive: false
        acceptText: dialog.pendingUpdate
                    ? dialog.strings.dep_update
                    : dialog.strings.dep_install
        cancelText: dialog.strings.confirm_cancel || ""
        closeText: dialog.strings.confirm_cancel || ""
        showClose: true
        onAccepted: {
            if (dialog.pendingAction === "all")
                bridge.updateDependencies()
            else if (dialog.pendingKey.length > 0)
                bridge.installDependency(dialog.pendingKey)
        }
    }
}
