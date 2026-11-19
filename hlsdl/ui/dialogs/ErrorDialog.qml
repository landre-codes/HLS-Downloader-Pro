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
    property bool detailsVisible: false

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    title: strings.dlg_error || ""
    width: 540
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    standardButtons: Dialog.NoButton
    onOpened: detailsVisible = false

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null

        Label {
            Layout.fillWidth: true
            text: dialog.strings.err_dialog_summary || ""
            wrapMode: Text.Wrap
            font.pixelSize: 13
            font.weight: Font.DemiBold
            color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            AppButton {
                text: dialog.detailsVisible
                      ? (dialog.strings.err_dialog_hide || "")
                      : (dialog.strings.err_dialog_details || "")
                variant: "secondary"
                onClicked: dialog.detailsVisible = !dialog.detailsVisible
            }
            Item { Layout.fillWidth: true }
            AppButton {
                text: dialog.strings.dlg_error_copy || ""
                variant: "secondary"
                onClicked: {
                    bridge.copyLink(dialog.message)
                    dialog.close()
                }
            }
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.preferredHeight: dialog.detailsVisible ? 150 : 0
            Layout.maximumHeight: dialog.detailsVisible ? 150 : 0
            visible: dialog.detailsVisible
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            contentWidth: availableWidth

            TextArea {
                id: detailsArea
                width: parent.width
                text: dialog.message
                readOnly: true
                selectByMouse: true
                wrapMode: TextArea.Wrap
                font.pixelSize: 12
                color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
                background: Rectangle {
                    radius: 6
                    color: dialog.appRoot ? dialog.appRoot.theme.cardBg : "#ffffff"
                    border.width: 1
                    border.color: dialog.appRoot ? dialog.appRoot.theme.cardBorder : "#d7dde3"
                }
            }
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: dialog.strings.dlg_error_close || ""
            variant: "secondary"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
