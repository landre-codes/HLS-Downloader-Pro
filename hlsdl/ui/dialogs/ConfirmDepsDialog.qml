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
    width: 520
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    standardButtons: Dialog.NoButton

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: dialog.pendingAction === "all"
                  ? dialog.strings.dep_confirm_all
                  : dialog.strings.dep_confirm_task.replace(
                        "{name}", dialog.pendingName)
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.pixelSize: 11
            color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
            text: dialog.strings.dep_confirm_detail
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: dialog.pendingUpdate
                  ? dialog.strings.dep_update
                  : dialog.strings.dep_install
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                if (dialog.pendingAction === "all")
                    bridge.updateDependencies()
                else if (dialog.pendingKey.length > 0)
                    bridge.installDependency(dialog.pendingKey)
                dialog.close()
            }
        }
        AppButton {
            text: dialog.strings.confirm_cancel || ""
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
