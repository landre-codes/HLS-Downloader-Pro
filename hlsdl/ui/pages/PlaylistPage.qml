import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

        Item {
    id: page
    property var appRoot
    property var strings: ({})

    ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: plLoadCol.implicitHeight + 32
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1
                    ColumnLayout {
                        id: plLoadCol
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16
                        spacing: 10

                        Label { text: strings.playlist_title; font.pixelSize: 15; font.weight: Font.DemiBold }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            AppHintField {
                                id: playlistUrl
                                Layout.fillWidth: true
                                hint: strings.playlist_url_placeholder
                                selectByMouse: true
                                onAccepted: appRoot.loadPlaylist()
                            }
                            AppButton {
                                text: bridge.playlistLoading
                                      ? strings.confirm_cancel
                                      : strings.btn_load_playlist
                                icon.source: appRoot.iconPath(
                                    bridge.playlistLoading ? "stop" : "retry"
                                )
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                enabled: bridge.playlistLoading
                                         || playlistUrl.text.trim().length > 0
                                highlighted: true
                                onClicked: bridge.playlistLoading
                                           ? bridge.cancelPlaylist()
                                           : appRoot.loadPlaylist()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Label { text: strings.playlist_limit; font.pixelSize: 13; color: appRoot.theme.textSecondary; Layout.alignment: Qt.AlignVCenter }
                            SpinBox {
                                id: playlistLimit
                                from: 0; to: 5000; stepSize: 50
                                value: 200
                                editable: true
                                ToolTip.text: strings.playlist_no_limit; ToolTip.visible: hovered; ToolTip.delay: 500
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Label {
                            text: strings.playlist_hint
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
                        anchors.margins: 12
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Label {
                                Layout.fillWidth: true
                                text: (appRoot.playlistFilterText.length > 0
                                       ? appRoot.playlistVisibleCount + "/" : "")
                                      + appRoot.playlistModelRef.count + " " + strings.playlist_items
                                      + (appRoot.playlistSelCount > 0 ? " · " + appRoot.playlistSelCount + " ✓" : "")
                                font.pixelSize: 13
                                color: appRoot.theme.textSecondary
                            }
                            AppButton {
                                text: strings.btn_select_all
                                enabled: appRoot.playlistModelRef.count > 0
                                onClicked: appRoot.selectAllPlaylist(true)
                            }
                            AppButton {
                                text: strings.btn_select_none
                                enabled: appRoot.playlistModelRef.count > 0
                                onClicked: appRoot.selectAllPlaylist(false)
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            AppHintField {
                                id: playlistFilter
                                Layout.fillWidth: true
                                hint: strings.filter_placeholder
                                leadingIcon: appRoot.iconPath("search")
                                selectByMouse: true
                                onTextChanged: {
                                    if (text.length === 0) {
                                        playlistFilterDebounce.stop()
                                        appRoot.playlistFilterText = ""
                                        appRoot.refreshPlaylistVisibleCount()
                                    } else {
                                        playlistFilterDebounce.restart()
                                    }
                                }
                            }
                            Timer {
                                id: playlistFilterDebounce
                                interval: 220
                                onTriggered: {
                                    appRoot.playlistFilterText = playlistFilter.text.toLowerCase()
                                    appRoot.refreshPlaylistVisibleCount()
                                }
                            }
                            AppToolButton {
                                display: AbstractButton.IconOnly
                                icon.source: appRoot.iconPath("cancel")
                                icon.width: 14; icon.height: 14
                                opacity: playlistFilter.text.length > 0 ? 1 : 0
                                enabled: playlistFilter.text.length > 0
                                Accessible.name: strings.btn_clear
                                ToolTip.text: strings.btn_clear
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: playlistFilter.clear()
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.theme.cardBorder }

                        ListView {
                            id: playlistView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: appRoot.playlistModelRef
                            spacing: 0
                            ScrollBar.vertical: ScrollBar {}
                            boundsBehavior: Flickable.StopAtBounds

                            Rectangle {
                                anchors.fill: parent
                                visible: playlistView.count === 0
                                         || (appRoot.playlistFilterText.length > 0
                                             && appRoot.playlistVisibleCount === 0)
                                color: "transparent"
                                Label {
                                    anchors.centerIn: parent
                                    text: appRoot.playlistFilterText.length > 0
                                          ? strings.filter_no_results
                                          : strings.playlist_empty_ui
                                    font.pixelSize: 13
                                    color: appRoot.theme.textSecondary
                                }
                            }

                            delegate: Item {
                                width: playlistView.width
                                property bool matches: appRoot.playlistMatches(model)
                                height: matches ? 52 : 0
                                visible: matches
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 6
                                    anchors.rightMargin: 6
                                    spacing: 8
                                    AppCheckBox {
                                        id: selBox
                                        Binding on checked { value: model.selected }
                                        onClicked: {
                                            model.selected = selBox.checked
                                            appRoot.refreshSelCount()
                                        }
                                    }
                                    Label {
                                        text: model.idx
                                        font.pixelSize: 11
                                        color: appRoot.theme.textSecondary
                                        Layout.preferredWidth: 34
                                    }
                                    Rectangle {
                                        Layout.preferredWidth: 64
                                        Layout.preferredHeight: 36
                                        Layout.alignment: Qt.AlignVCenter
                                        radius: 4
                                        color: appRoot.theme.thumbnailBg
                                        Image {
                                            anchors.fill: parent
                                            visible: model.thumb !== ""
                                            source: model.thumb
                                            asynchronous: true
                                            fillMode: Image.PreserveAspectCrop
                                            clip: true
                                        }
                                    }
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 0
                                        Label { Layout.fillWidth: true; text: model.title; elide: Text.ElideMiddle; font.pixelSize: 12 }
                                        Label { Layout.fillWidth: true; text: model.url; elide: Text.ElideMiddle; font.pixelSize: 10; color: appRoot.theme.textSecondary }
                                    }
                                    Label {
                                        text: appRoot.formatDuration(model.duration)
                                        font.pixelSize: 11
                                        color: appRoot.theme.textSecondary
                                        Layout.preferredWidth: 48
                                    }
                                }
                                Rectangle {
                                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                    height: 1
                                    color: appRoot.theme.divider
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            AppButton {
                                text: strings.btn_add_selected
                                icon.source: appRoot.iconPath("add")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                enabled: appRoot.playlistSelCount > 0
                                onClicked: appRoot.addSelectedPlaylist(false)
                            }
                            AppButton {
                                text: strings.btn_download_selected
                                icon.source: appRoot.iconPath("play")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                highlighted: true
                                enabled: appRoot.playlistSelCount > 0
                                onClicked: appRoot.addSelectedPlaylist(true)
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }
