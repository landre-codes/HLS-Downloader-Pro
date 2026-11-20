import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    width: appRoot ? Math.min(780, appRoot.width - 48) : 720
    height: appRoot ? Math.min(620, appRoot.height - 48) : 560
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape

    onOpened: playlistUrl.forceActiveFocus()

    contentItem: AppDialogSurface {
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        width: dialog.width
        height: dialog.height
        implicitWidth: dialog.width
        implicitHeight: dialog.height

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                Layout.fillWidth: true
                text: dialog.strings.playlist_title || ""
                font.pixelSize: 17
                font.weight: Font.DemiBold
                color: dialog.appRoot ? dialog.appRoot.theme.text : "#202428"
            }
            AppToolButton {
                display: AbstractButton.IconOnly
                icon.source: dialog.appRoot ? dialog.appRoot.iconPath("cancel") : ""
                icon.width: 16
                icon.height: 16
                Accessible.name: dialog.strings.dlg_error_close || ""
                tipTitle: dialog.strings.dlg_error_close || ""
                onClicked: dialog.close()
            }
        }

        Label {
            Layout.fillWidth: true
            text: dialog.strings.playlist_import_hint || ""
            wrapMode: Text.Wrap
            font.pixelSize: 12
            color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            AppHintField {
                id: playlistUrl
                Layout.fillWidth: true
                hint: dialog.strings.playlist_url_placeholder || ""
                selectByMouse: true
                onAccepted: dialog.appRoot.loadPlaylist(
                                playlistUrl.text, playlistLimit.value)
            }
            AppButton {
                text: bridge.playlistLoading
                      ? dialog.strings.confirm_cancel
                      : dialog.strings.btn_load_playlist
                icon.source: dialog.appRoot.iconPath(
                    bridge.playlistLoading ? "stop" : "retry")
                icon.width: 16
                icon.height: 16
                display: AbstractButton.TextBesideIcon
                enabled: bridge.playlistLoading
                         || playlistUrl.text.trim().length > 0
                highlighted: true
                onClicked: bridge.playlistLoading
                           ? bridge.cancelPlaylist()
                           : dialog.appRoot.loadPlaylist(
                                 playlistUrl.text, playlistLimit.value)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                text: dialog.strings.playlist_limit || ""
                font.pixelSize: 13
                color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
            }
            AppSpinBox {
                id: playlistLimit
                from: 0
                to: 5000
                stepSize: 50
                value: 200
                editable: true
                tipText: dialog.strings.playlist_no_limit || ""
            }
            Item { Layout.fillWidth: true }
            AppButton {
                text: dialog.strings.playlist_clear_list || ""
                variant: "tertiary"
                size: "compact"
                enabled: dialog.appRoot.playlistModelRef.count > 0
                onClicked: {
                    dialog.appRoot.clearPlaylist()
                    playlistFilter.clear()
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                Layout.fillWidth: true
                text: (dialog.appRoot.playlistFilterText.length > 0
                       ? dialog.appRoot.playlistVisibleCount + "/" : "")
                      + dialog.appRoot.playlistModelRef.count + " "
                      + (dialog.strings.playlist_items || "")
                      + (dialog.appRoot.playlistSelCount > 0
                         ? " · " + dialog.appRoot.playlistSelCount + " " : "")
                font.pixelSize: 12
                color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
            }
            AppButton {
                text: dialog.strings.btn_select_all || ""
                size: "compact"
                variant: "tertiary"
                enabled: dialog.appRoot.playlistModelRef.count > 0
                onClicked: dialog.appRoot.selectAllPlaylist(true)
            }
            AppButton {
                text: dialog.strings.btn_select_none || ""
                size: "compact"
                variant: "tertiary"
                enabled: dialog.appRoot.playlistModelRef.count > 0
                onClicked: dialog.appRoot.selectAllPlaylist(false)
            }
        }

        AppHintField {
            id: playlistFilter
            Layout.fillWidth: true
            hint: dialog.strings.filter_placeholder || ""
            leadingIcon: dialog.appRoot.iconPath("search")
            selectByMouse: true
            onTextChanged: {
                if (text.length === 0) {
                    playlistFilterDebounce.stop()
                    dialog.appRoot.playlistFilterText = ""
                    dialog.appRoot.refreshPlaylistVisibleCount()
                } else {
                    playlistFilterDebounce.restart()
                }
            }
        }
        Timer {
            id: playlistFilterDebounce
            interval: 220
            onTriggered: {
                dialog.appRoot.playlistFilterText = playlistFilter.text.toLowerCase()
                dialog.appRoot.refreshPlaylistVisibleCount()
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.minimumHeight: 180
            radius: 6
            color: dialog.appRoot ? dialog.appRoot.theme.cardBg : "#ffffff"
            border.width: 1
            border.color: dialog.appRoot ? dialog.appRoot.theme.cardBorder : "#d7dde3"
            clip: true

            ListView {
                id: playlistView
                anchors.fill: parent
                anchors.margins: 4
                clip: true
                model: dialog.appRoot.playlistModelRef
                spacing: 0
                ScrollBar.vertical: ScrollBar {}
                boundsBehavior: Flickable.StopAtBounds

                Label {
                    anchors.centerIn: parent
                    visible: playlistView.count === 0
                             || (dialog.appRoot.playlistFilterText.length > 0
                                 && dialog.appRoot.playlistVisibleCount === 0)
                    text: dialog.appRoot.playlistFilterText.length > 0
                          ? dialog.strings.filter_no_results
                          : dialog.strings.playlist_empty_ui
                    font.pixelSize: 13
                    color: dialog.appRoot.theme.textSecondary
                }

                delegate: Item {
                    width: playlistView.width
                    property bool matches: dialog.appRoot.playlistMatches(model)
                    height: matches ? 50 : 0
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
                                dialog.appRoot.refreshSelCount()
                            }
                        }
                        Label {
                            text: model.idx
                            font.pixelSize: 11
                            color: dialog.appRoot.theme.textSecondary
                            Layout.preferredWidth: 34
                        }
                        Rectangle {
                            Layout.preferredWidth: 60
                            Layout.preferredHeight: 34
                            radius: 4
                            color: dialog.appRoot.theme.thumbnailBg
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
                            Label {
                                Layout.fillWidth: true
                                text: model.title
                                elide: Text.ElideMiddle
                                font.pixelSize: 12
                            }
                            Label {
                                Layout.fillWidth: true
                                text: model.url
                                elide: Text.ElideMiddle
                                font.pixelSize: 10
                                color: dialog.appRoot.theme.textSecondary
                            }
                        }
                        Label {
                            text: dialog.appRoot.formatDuration(model.duration)
                            font.pixelSize: 11
                            color: dialog.appRoot.theme.textSecondary
                            Layout.preferredWidth: 46
                        }
                    }
                    Rectangle {
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        height: 1
                        color: dialog.appRoot.theme.divider
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Item { Layout.fillWidth: true }
            AppButton {
                text: dialog.strings.dlg_error_close || ""
                variant: "tertiary"
                onClicked: dialog.close()
            }
            AppButton {
                text: dialog.strings.btn_add_selected || ""
                variant: "secondary"
                icon.source: dialog.appRoot.iconPath("add")
                icon.width: 16
                icon.height: 16
                display: AbstractButton.TextBesideIcon
                enabled: dialog.appRoot.playlistSelCount > 0
                onClicked: {
                    dialog.appRoot.addSelectedPlaylist(false)
                    dialog.close()
                }
            }
            AppButton {
                text: dialog.strings.btn_download_selected || ""
                icon.source: dialog.appRoot.iconPath("play")
                icon.width: 16
                icon.height: 16
                display: AbstractButton.TextBesideIcon
                highlighted: true
                enabled: dialog.appRoot.playlistSelCount > 0
                onClicked: {
                    dialog.appRoot.addSelectedPlaylist(true)
                    dialog.close()
                }
            }
        }
    }
}
