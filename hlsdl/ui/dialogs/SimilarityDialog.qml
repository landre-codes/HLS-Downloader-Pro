import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot
    property var strings
    property var bridge

    modal: true
    title: strings.similar_title
    width: Math.min(appRoot.width - 60, 780)
    x: (appRoot.width - width) / 2
    y: (appRoot.height - height) / 2
    standardButtons: Dialog.NoButton

    function formatBytes(value) {
        var n = Number(value) || 0
        if (n <= 0)
            return "—"
        var units = ["B", "KB", "MB", "GB", "TB"]
        var i = 0
        while (n >= 1024 && i < units.length - 1) {
            n /= 1024
            i++
        }
        return (i === 0 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i]
    }

    contentItem: Rectangle {
        color: appRoot.theme.windowBg
        implicitWidth: 720
        implicitHeight: body.implicitHeight
        ColumnLayout {
            id: body
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            spacing: 8

            Label {
                Layout.fillWidth: true
                text: strings.similar_subtitle
                wrapMode: Text.Wrap
                font.pixelSize: 12
                color: appRoot.theme.textSecondary
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Label { text: strings.similar_threshold; font.pixelSize: 12; color: appRoot.theme.textSecondary }
                SpinBox {
                    from: 50; to: 100; stepSize: 5
                    value: bridge.similarityThreshold
                    editable: true
                    onValueChanged: if (value !== bridge.similarityThreshold)
                                        bridge.setSimilarityThreshold(value)
                    ToolTip.text: strings.similar_threshold_tip
                    ToolTip.visible: hovered
                    ToolTip.delay: 500
                }
                AppButton {
                    text: strings.similar_scan_queue
                    enabled: !bridge.similarityBusy
                    onClicked: bridge.scanSimilarQueue()
                }
                AppButton {
                    text: strings.similar_scan_folder
                    enabled: !bridge.similarityBusy
                    onClicked: bridge.scanSimilarFolder()
                }
                AppButton {
                    text: strings.similar_cancel
                    enabled: bridge.similarityBusy
                    onClicked: bridge.cancelSimilarityScan()
                }
                Item { Layout.fillWidth: true }
                AppButton {
                    text: strings.similar_clear
                    enabled: bridge.similarityGroups.length > 0
                    onClicked: bridge.clearSimilarityResults()
                }
            }

            ProgressBar {
                Layout.fillWidth: true
                from: 0; to: 1
                value: bridge.similarityTotal > 0
                       ? bridge.similarityProgress / bridge.similarityTotal : 0
                visible: bridge.similarityBusy
            }

            Label {
                Layout.fillWidth: true
                text: bridge.similarityStatus
                visible: bridge.similarityStatus.length > 0
                wrapMode: Text.Wrap
                font.pixelSize: 11
                color: appRoot.theme.textSecondary
            }

            Label {
                Layout.fillWidth: true
                text: strings.similar_hint
                wrapMode: Text.Wrap
                font.pixelSize: 11
                color: appRoot.theme.textMuted
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 360
                clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded
                ListView {
                    id: similarList
                    model: bridge.similarityGroups
                    spacing: 8
                    delegate: Rectangle {
                        width: similarList.width
                        height: similarGroup.implicitHeight + 18
                        radius: 8
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
                        border.width: 1

                        ColumnLayout {
                            id: similarGroup
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.top: parent.top
                            anchors.margins: 9
                            spacing: 3

                            Label {
                                Layout.fillWidth: true
                                text: "#" + (index + 1) + "  ·  " + modelData.score + "%  ·  "
                                      + strings.similar_method + ": " + modelData.method
                                font.pixelSize: 12
                                font.bold: true
                                color: appRoot.theme.accentText
                            }

                            Repeater {
                                model: modelData.members
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 6
                                    Label {
                                        Layout.fillWidth: true
                                        text: modelData.path
                                        elide: Text.ElideMiddle
                                        font.pixelSize: 11
                                    }
                                    Label {
                                        text: dialog.formatBytes(modelData.size)
                                        font.pixelSize: 10
                                        color: appRoot.theme.textSecondary
                                    }
                                    AppToolButton {
                                        width: 26; height: 24
                                        text: "…"
                                        Accessible.name: strings.similar_open
                                        ToolTip.text: strings.similar_open
                                        ToolTip.visible: hovered
                                        ToolTip.delay: 500
                                        onClicked: bridge.openDownloadPath(modelData.path)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Label {
                Layout.fillWidth: true
                visible: bridge.similarityGroups.length === 0 && !bridge.similarityBusy
                text: strings.similar_empty
                color: appRoot.theme.textSecondary
                font.pixelSize: 12
                horizontalAlignment: Text.AlignHCenter
            }
        }
    }

    footer: DialogButtonBox {
        AppButton {
            text: strings.similar_close
            DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
            onClicked: dialog.close()
        }
    }
}
