import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

// Confirmação antes de instalar uma saída com queda extrema de bitrate.
// Fechar a janela (Esc) equivale a recusar: o arquivo original é mantido.
Dialog {
    id: dialog
    objectName: "qualityConfirmDialog"

    property var appRoot: null
    property var strings: ({})
    property var bridge: null
    property var prompt: bridge ? bridge.compressionQualityPrompt : ({})
    property bool responded: false

    function hasPrompt() {
        return prompt !== undefined && prompt !== null
                && prompt.id !== undefined
    }

    function resolution(width, height) {
        return width > 0 && height > 0 ? width + " × " + height : "—"
    }

    function ssimColor() {
        var value = Number(prompt.ssim) || 0
        if (value <= 0)
            return appRoot ? appRoot.theme.textMuted : "#9aa5af"
        if (value < 0.95)
            return appRoot ? appRoot.theme.warningText : "#ffd180"
        return appRoot ? appRoot.theme.successText : "#81c784"
    }

    function decide(allow) {
        if (!hasPrompt())
            return
        responded = true
        bridge.respondCompressionQuality(allow)
    }

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape
    width: Math.min(appRoot ? appRoot.width - 60 : 640, 640)
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0

    onPromptChanged: {
        if (hasPrompt()) {
            responded = false
            open()
        } else {
            close()
        }
    }

    onClosed: {
        if (hasPrompt() && !responded) {
            responded = true
            bridge.respondCompressionQuality(false)
        }
    }

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        implicitWidth: 600

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(64, warningRow.implicitHeight + 24)
            radius: 10
            color: dialog.appRoot ? dialog.appRoot.theme.warningBg : "#4a2c1f"

            RowLayout {
                id: warningRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: 12
                spacing: 12

                Rectangle {
                    Layout.alignment: Qt.AlignTop
                    width: 34
                    height: 34
                    radius: 17
                    color: "#d98b2b"
                    Label {
                        anchors.centerIn: parent
                        text: "!"
                        font.pixelSize: 20
                        font.bold: true
                        color: "#1b1b1b"
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 3
                    Label {
                        Layout.fillWidth: true
                        text: dialog.strings.compress_quality_confirm_title
                        font.pixelSize: 16
                        font.bold: true
                        color: dialog.appRoot ? dialog.appRoot.theme.warningText : "#ffd180"
                    }
                    Label {
                        Layout.fillWidth: true
                        text: dialog.strings.compress_quality_confirm_message
                        font.pixelSize: 12
                        wrapMode: Text.Wrap
                        color: dialog.appRoot ? dialog.appRoot.theme.warningText : "#ffd180"
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.topMargin: 2
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            spacing: 8

            Image {
                width: 16
                height: 16
                source: dialog.appRoot && dialog.appRoot.iconPath
                        ? dialog.appRoot.iconPath("file") : ""
                fillMode: Image.PreserveAspectFit
            }
            Label {
                Layout.fillWidth: true
                text: dialog.prompt.name || ""
                font.pixelSize: 13
                font.bold: true
                elide: Text.ElideMiddle
                color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            spacing: 10

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: sourceMetrics.implicitHeight + 20
                radius: 8
                color: dialog.appRoot ? dialog.appRoot.theme.cardBg : "#ffffff"
                border.width: 1
                border.color: dialog.appRoot ? dialog.appRoot.theme.cardBorder : "#d7dde3"

                ColumnLayout {
                    id: sourceMetrics
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 6

                    Label {
                        text: dialog.strings.compress_quality_source
                        font.pixelSize: 11
                        font.bold: true
                        color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            Layout.preferredWidth: 82
                            text: dialog.strings.compress_quality_bitrate
                            font.pixelSize: 11
                            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                        }
                        Label {
                            Layout.fillWidth: true
                            text: dialog.appRoot ? dialog.appRoot.formatBitrate(dialog.prompt.bitrate_before) : "—"
                            font.pixelSize: 12
                            font.bold: true
                            color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            Layout.preferredWidth: 82
                            text: dialog.strings.compress_quality_resolution
                            font.pixelSize: 11
                            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                        }
                        Label {
                            Layout.fillWidth: true
                            text: dialog.resolution(dialog.prompt.width_before,
                                                    dialog.prompt.height_before)
                            font.pixelSize: 12
                            font.bold: true
                            color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            Layout.preferredWidth: 82
                            text: dialog.strings.compress_quality_size
                            font.pixelSize: 11
                            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                        }
                        Label {
                            Layout.fillWidth: true
                            text: dialog.appRoot ? dialog.appRoot.formatBytes(dialog.prompt.size_before) : "—"
                            font.pixelSize: 12
                            font.bold: true
                            color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
                        }
                    }
                }
            }

            Label {
                text: "→"
                font.pixelSize: 20
                color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: outputMetrics.implicitHeight + 20
                radius: 8
                color: dialog.appRoot ? dialog.appRoot.theme.cardBg : "#ffffff"
                border.width: 1
                border.color: dialog.appRoot ? dialog.appRoot.theme.cardBorder : "#d7dde3"

                ColumnLayout {
                    id: outputMetrics
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 10
                    spacing: 6

                    Label {
                        text: dialog.strings.compress_quality_output
                        font.pixelSize: 11
                        font.bold: true
                        color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            Layout.preferredWidth: 82
                            text: dialog.strings.compress_quality_bitrate
                            font.pixelSize: 11
                            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                        }
                        Label {
                            Layout.fillWidth: true
                            text: dialog.appRoot ? dialog.appRoot.formatBitrate(dialog.prompt.bitrate_after) : "—"
                            font.pixelSize: 12
                            font.bold: true
                            color: dialog.appRoot ? dialog.appRoot.theme.warningText : "#ffd180"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            Layout.preferredWidth: 82
                            text: dialog.strings.compress_quality_resolution
                            font.pixelSize: 11
                            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                        }
                        Label {
                            Layout.fillWidth: true
                            text: dialog.resolution(dialog.prompt.width_after,
                                                    dialog.prompt.height_after)
                            font.pixelSize: 12
                            font.bold: true
                            color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 6
                        Label {
                            Layout.preferredWidth: 82
                            text: dialog.strings.compress_quality_size
                            font.pixelSize: 11
                            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
                        }
                        Label {
                            Layout.fillWidth: true
                            text: dialog.appRoot ? dialog.appRoot.formatBytes(dialog.prompt.size_after) : "—"
                            font.pixelSize: 12
                            font.bold: true
                            color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.preferredHeight: 42
            radius: 8
            color: dialog.appRoot ? dialog.appRoot.theme.tableHeaderBg : "#eef1f4"

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 12

                Label {
                    text: dialog.strings.compress_quality_ssim + ": "
                          + (Number(dialog.prompt.ssim) > 0
                             ? Number(dialog.prompt.ssim).toFixed(3) : "—")
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.ssimColor()
                }
                Item { Layout.fillWidth: true }
                Label {
                    text: dialog.strings.compress_quality_saving + ": "
                          + (Number(dialog.prompt.saving) > 0
                             ? Number(dialog.prompt.saving).toFixed(1) + "%" : "—")
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot ? dialog.appRoot.theme.successText : "#81c784"
                }
            }
        }

        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            text: dialog.strings.compress_quality_confirm_hint
            font.pixelSize: 11
            wrapMode: Text.Wrap
            color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
        }
        Label {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            Layout.rightMargin: 12
            Layout.bottomMargin: 12
            text: dialog.strings.compress_quality_close_hint
            font.pixelSize: 11
            wrapMode: Text.Wrap
            color: dialog.appRoot ? dialog.appRoot.theme.textMuted : "#626b75"
        }
    }

    footer: DialogButtonBox {
        AppButton {
            objectName: "qualityConfirmReject"
            text: dialog.strings.compress_quality_discard
            highlighted: true
            font.bold: true
            Material.accent: dialog.appRoot
                              ? dialog.appRoot.theme.accentText : "#90caf9"
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.decide(false)
        }
        AppButton {
            objectName: "qualityConfirmAccept"
            text: dialog.strings.compress_quality_keep
            DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
            onClicked: dialog.decide(true)
        }
    }
}
