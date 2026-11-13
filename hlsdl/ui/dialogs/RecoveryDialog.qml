import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot
    property var strings
    property var bridge

    modal: true
    title: strings.recovery_title
    width: 640
    x: (appRoot.width - width) / 2
    y: (appRoot.height - height) / 2
    standardButtons: Dialog.NoButton

    contentItem: Rectangle {
        color: appRoot.theme.windowBg
        implicitWidth: 600
        implicitHeight: body.implicitHeight
        ColumnLayout {
            id: body
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: 8

            Label {
                Layout.fillWidth: true
                text: strings.recovery_hint
                wrapMode: Text.Wrap
                color: appRoot.theme.textSecondary
                font.pixelSize: 12
            }

            Repeater {
                model: bridge.recoveryMessages
                delegate: Label {
                    Layout.fillWidth: true
                    text: "• " + modelData
                    wrapMode: Text.Wrap
                    font.pixelSize: 11
                }
            }
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: strings.recovery_dismiss
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: {
                dialog.close()
                bridge.clearRecoveryMessages()
            }
        }
    }
}
