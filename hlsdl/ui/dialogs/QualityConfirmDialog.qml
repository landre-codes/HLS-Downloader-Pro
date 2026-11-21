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
    property var backend: null
    property var prompt: backend ? backend.compressionQualityPrompt : ({})
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
        if (!hasPrompt() || responded)
            return
        responded = true
        backend.respondCompressionQuality(allow)
    }

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    header: null
    footer: null
    background: Rectangle { color: "transparent"; radius: 24 }
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
            backend.respondCompressionQuality(false)
        }
    }

    contentItem: ConfirmSurface {
        width: dialog.width
        height: implicitHeight
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        appRoot: dialog.appRoot
        strings: dialog.strings
        dialog: dialog
        title: dialog.strings.compress_quality_confirm_title
        message: dialog.strings.compress_quality_confirm_message
        iconText: "!"
        warning: true
        acceptText: dialog.strings.compress_quality_keep
        cancelText: dialog.strings.compress_quality_discard
        acceptObjectName: "qualityConfirmAccept"
        cancelObjectName: "qualityConfirmReject"
        cancelVariant: "warning"
        closeText: dialog.strings.compress_quality_discard
        showClose: true
        onAccepted: dialog.decide(true)
        onCancelled: dialog.decide(false)

        RowLayout {
            Layout.fillWidth: true
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
                color: dialog.appRoot ? dialog.appRoot.theme.text : "#1f2937"
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: metrics.implicitHeight + 24
            radius: 10
            color: dialog.appRoot ? dialog.appRoot.theme.tableBg : "#f5f8fd"
            border.width: 1
            border.color: dialog.appRoot
                          ? dialog.appRoot.theme.cardBorder : "#d8e1ee"

            GridLayout {
                id: metrics
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.margins: 12
                columns: 3
                columnSpacing: 12
                rowSpacing: 6

                Label { text: "" }
                Label {
                    text: dialog.strings.compress_quality_source
                    font.pixelSize: 11
                    font.bold: true
                    color: dialog.appRoot
                           ? dialog.appRoot.theme.textMuted : "#626b75"
                }
                Label {
                    text: dialog.strings.compress_quality_output
                    font.pixelSize: 11
                    font.bold: true
                    color: dialog.appRoot
                           ? dialog.appRoot.theme.textMuted : "#626b75"
                }

                Label {
                    text: dialog.strings.compress_quality_bitrate
                    font.pixelSize: 11
                    color: dialog.appRoot
                           ? dialog.appRoot.theme.textMuted : "#626b75"
                }
                Label {
                    text: dialog.appRoot
                          ? dialog.appRoot.formatBitrate(dialog.prompt.bitrate_before)
                          : "—"
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot ? dialog.appRoot.theme.text : "#1f2937"
                }
                Label {
                    text: dialog.appRoot
                          ? dialog.appRoot.formatBitrate(dialog.prompt.bitrate_after)
                          : "—"
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot
                           ? dialog.appRoot.theme.warningText : "#ffd180"
                }

                Label {
                    text: dialog.strings.compress_quality_resolution
                    font.pixelSize: 11
                    color: dialog.appRoot
                           ? dialog.appRoot.theme.textMuted : "#626b75"
                }
                Label {
                    text: dialog.resolution(dialog.prompt.width_before,
                                            dialog.prompt.height_before)
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot ? dialog.appRoot.theme.text : "#1f2937"
                }
                Label {
                    text: dialog.resolution(dialog.prompt.width_after,
                                            dialog.prompt.height_after)
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot ? dialog.appRoot.theme.text : "#1f2937"
                }

                Label {
                    text: dialog.strings.compress_quality_size
                    font.pixelSize: 11
                    color: dialog.appRoot
                           ? dialog.appRoot.theme.textMuted : "#626b75"
                }
                Label {
                    text: dialog.appRoot
                          ? dialog.appRoot.formatBytes(dialog.prompt.size_before)
                          : "—"
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot ? dialog.appRoot.theme.text : "#1f2937"
                }
                Label {
                    text: dialog.appRoot
                          ? dialog.appRoot.formatBytes(dialog.prompt.size_after)
                          : "—"
                    font.pixelSize: 12
                    font.bold: true
                    color: dialog.appRoot ? dialog.appRoot.theme.text : "#1f2937"
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
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
                color: dialog.appRoot
                       ? dialog.appRoot.theme.successText : "#81c784"
            }
        }

        Label {
            Layout.fillWidth: true
            text: dialog.strings.compress_quality_confirm_hint
            font.pixelSize: 11
            wrapMode: Text.Wrap
            color: dialog.appRoot
                   ? dialog.appRoot.theme.textSecondary : "#4f5862"
        }
        Label {
            Layout.fillWidth: true
            text: dialog.strings.compress_quality_close_hint
            font.pixelSize: 11
            wrapMode: Text.Wrap
            color: dialog.appRoot
                   ? dialog.appRoot.theme.textMuted : "#626b75"
        }
    }
}
