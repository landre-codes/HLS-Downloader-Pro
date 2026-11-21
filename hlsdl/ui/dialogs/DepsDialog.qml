import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
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
    header: null
    footer: null
    background: Rectangle { color: "transparent"; radius: 24 }
    width: 560
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0
    standardButtons: Dialog.NoButton

    contentItem: ConfirmSurface {
        width: dialog.width
        height: implicitHeight
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        appRoot: dialog.appRoot
        strings: dialog.strings
        dialog: dialog
        title: dialog.title
        message: dialog.strings.dlg_deps_body
        detail: {
            var parts = []
            for (var i = 0; i < bridge.dependencies.length; i++) {
                var d = bridge.dependencies[i]
                if (d.required && !d.found)
                    parts.push("\u2022 " + d.name)
            }
            return parts.join("\n")
        }
        iconText: "!"
        destructive: false
        acceptText: dialog.strings.dlg_deps_install || ""
        cancelText: dialog.strings.dlg_deps_later || ""
        showClose: false
        terminalTitle: dialog.strings.dep_console
        terminalOutput: dialog.logText
        onAccepted: {
            bridge.dismissDepsPrompt()
            bridge.installMissingDependencies()
            if (dialog.appRoot)
                dialog.appRoot.goToSettingsTab()
        }
        onCancelled: bridge.dismissDepsPrompt()
    }
}
