import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})
    property string logText: ""

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    title: strings.dlg_deps_title || ""
    width: 560
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    standardButtons: Dialog.NoButton

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        Label {
            Layout.fillWidth: true
            text: dialog.strings.dlg_deps_body
            wrapMode: Text.Wrap
        }
        Label {
            Layout.fillWidth: true
            text: {
                var parts = []
                for (var i = 0; i < bridge.dependencies.length; i++) {
                    var d = bridge.dependencies[i]
                    if (d.required && !d.found)
                        parts.push("• " + d.name)
                }
                return parts.join("\n")
            }
            color: dialog.appRoot ? dialog.appRoot.theme.errorText : "#c62828"
            font.pixelSize: 12
        }
        AppTerminalPanel {
            theme: dialog.appRoot ? dialog.appRoot.theme : null
            strings: dialog.strings
            visible: dialog.logText.length > 0
            title: dialog.strings.dep_console
            output: dialog.logText
            panelHeight: 110
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: dialog.strings.dlg_deps_install || ""
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: {
                bridge.dismissDepsPrompt()
                bridge.installMissingDependencies()
                dialog.close()
                if (dialog.appRoot)
                    dialog.appRoot.goToSettingsTab()
            }
        }
        AppButton {
            text: dialog.strings.dlg_deps_later || ""
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: {
                bridge.dismissDepsPrompt()
                dialog.close()
            }
        }
    }
}
