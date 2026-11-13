import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

        Item {
    id: page
    property var appRoot
    property var strings: ({})
    property alias singleUrl: singleUrl

    ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: singleCol.implicitHeight + 32
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1
                    ColumnLayout {
                        id: singleCol
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16
                        spacing: 12
                        Label { text: strings.single_title; font.pixelSize: 15; font.weight: Font.DemiBold }

                        AppHintField {
                            id: singleUrl
                            Layout.fillWidth: true
                            hint: strings.single_url_placeholder
                            selectByMouse: true
                            onAccepted: appRoot.startSingle()
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                text: strings.fmt_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary; Layout.alignment: Qt.AlignVCenter
                            }
                            AppFormatSelector {
                                strings: page.strings
                                Layout.alignment: Qt.AlignVCenter }
                            Item { Layout.fillWidth: true }
                            Label {
                                text: strings.container_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary; Layout.alignment: Qt.AlignVCenter
                            }
                            AppContainerCombo {
                                Layout.alignment: Qt.AlignVCenter }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: bridge.formatMode !== "audio_only"
                            Label {
                                text: strings.quality_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary; Layout.alignment: Qt.AlignVCenter
                            }
                            AppQualityCombo {
                                strings: page.strings
                                Layout.alignment: Qt.AlignVCenter }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            visible: bridge.formatMode !== "audio_only"
                            Label {
                                visible: bridge.formatMode !== "audio_only"
                                text: strings.codec_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary; Layout.alignment: Qt.AlignVCenter
                            }
                            AppCodecCombo {
                                strings: page.strings
                                visible: bridge.formatMode !== "audio_only"
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
                                text: strings.compress_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary; Layout.alignment: Qt.AlignVCenter
                            }
                            AppCompressCombo {
                                strings: page.strings
                                visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            AppButton {
                                text: strings.btn_download_now; highlighted: true
                                icon.source: appRoot.iconPath("play")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                ToolTip.text: strings.single_hint
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: appRoot.startSingle()
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Label {
                            text: strings.single_hint
                            font.pixelSize: 11
                            color: appRoot.theme.textSecondary
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12
                        Label { text: strings.single_progress; font.pixelSize: 15; font.weight: Font.DemiBold }

                        Label {
                            visible: bridge.lastItem.url === undefined || bridge.lastItem.url === ""
                            text: strings.single_idle
                            color: appRoot.theme.textSecondary
                            font.pixelSize: 13
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: bridge.lastItem.url !== undefined && bridge.lastItem.url !== ""
                            spacing: 10

                            Label {
                                Layout.fillWidth: true
                                text: bridge.lastItem.title || ""
                                elide: Text.ElideMiddle
                                font.weight: Font.DemiBold
                                font.pixelSize: 14
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Rectangle {
                                    width: 120; height: 24; radius: 12
                                    color: appRoot.badgeColor(bridge.lastItem.status)
                                    Label {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        text: appRoot.statusText(bridge.lastItem.status || "")
                                        color: appRoot.theme.onAccent
                                        font.pixelSize: 11
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                        elide: Text.ElideRight
                                    }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: (bridge.lastItem.speed || "") + "   " + (bridge.lastItem.size || "")
                                    color: appRoot.theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }

                            ProgressBar {
                                Layout.fillWidth: true
                                from: 0; to: 100
                                value: bridge.lastItem.progress !== undefined ? bridge.lastItem.progress : 0
                                indeterminate: bridge.lastItem.status === "analyzing"
                            }

                            Label {
                                Layout.fillWidth: true
                                visible: bridge.lastItem.status === "error" && (bridge.lastItem.error || "").length > 0
                                text: bridge.lastItem.error || ""
                                color: appRoot.theme.errorText
                                wrapMode: Text.Wrap
                                font.pixelSize: 12
                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: appRoot.showError(bridge.lastItem.error)
                                }
                            }

                            RowLayout {
                                spacing: 10
                                AppButton {
                                    visible: bridge.lastItem.status === "done"
                                    text: strings.btn_open
                                    onClicked: bridge.openDownloadPath(bridge.lastItem.path)
                                }
                                AppButton {
                                    visible: bridge.lastItem.status === "waiting"
                                             || appRoot.isActive(bridge.lastItem.status)
                                    text: strings.tip_cancel
                                    onClicked: bridge.cancelSingle()
                                }
                                AppButton {
                                    visible: bridge.lastItem.status === "error"
                                             || bridge.lastItem.status === "cancelled"
                                    text: strings.ctx_retry
                                    onClicked: bridge.retrySingle()
                                }
                                Item { Layout.fillWidth: true }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
