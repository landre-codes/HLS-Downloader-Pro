import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

// Importação de playlist sem sair da aba Downloads. O cabeçalho usa o mesmo
// gradiente das páginas e os itens selecionados entram na fila já existente.
Dialog {
    id: dialog

    property var appRoot: null
    property var strings: ({})

    parent: appRoot ? appRoot.contentItem : null
    modal: true
    width: appRoot ? Math.min(820, appRoot.width - 40) : 780
    height: appRoot ? Math.min(640, appRoot.height - 40) : 560
    x: appRoot ? (appRoot.width - width) / 2 : 0
    y: appRoot ? (appRoot.height - height) / 2 : 0
    padding: 0
    standardButtons: Dialog.NoButton
    closePolicy: Popup.CloseOnEscape

    // Valida antes de qualquer chamada ao backend: Enter/clique sem URL não
    // podem iniciar uma listagem vazia nem produzir exceção.
    function submitPlaylist() {
        var value = playlistUrl.text.trim()
        if (value.length === 0) {
            playlistUrl.forceActiveFocus()
            return false
        }
        dialog.appRoot.loadPlaylist(value, playlistLimit.value)
        return true
    }

    onOpened: {
        if (dialogSurface.maximized)
            dialogSurface.restoreGeometry()
        playlistUrl.forceActiveFocus()
    }
    onClosed: if (dialogSurface.maximized)
                  dialogSurface.restoreGeometry()

    contentItem: AppDialogSurface {
        id: dialogSurface
        objectName: "playlistDialogSurface"
        theme: dialog.appRoot ? dialog.appRoot.theme : null
        dialog: dialog
        appRoot: dialog.appRoot
        strings: dialog.strings
        title: dialog.strings.playlist_title || ""
        subtitle: dialog.strings.playlist_import_hint || ""
        iconSource: dialog.appRoot ? dialog.appRoot.iconPath("download") : ""
        showCloseButton: true
        closeText: dialog.strings.dlg_error_close || ""
        resizable: true
        minDialogWidth: 520
        minDialogHeight: 420
        width: dialog.width
        height: dialog.height
        implicitWidth: dialog.width
        implicitHeight: dialog.height

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            AppHintField {
                id: playlistUrl
                objectName: "playlistUrlField"
                Layout.fillWidth: true
                hint: dialog.strings.playlist_url_placeholder || ""
                strings: dialog.strings
                selectByMouse: true
                tipEnabled: false
                onAccepted: dialog.submitPlaylist()
            }
            AppButton {
                text: bridge.playlistLoading
                      ? dialog.strings.confirm_cancel
                      : dialog.strings.btn_load_playlist
                icon.source: bridge.playlistLoading
                             ? dialog.appRoot.iconPath("stop", enabled)
                             : dialog.appRoot.tonalIcon("retry", enabled)
                icon.width: 16
                icon.height: 16
                display: AbstractButton.TextBesideIcon
                enabled: bridge.playlistLoading
                         || playlistUrl.text.trim().length > 0
                variant: bridge.playlistLoading ? "danger" : "tonal"
                onClicked: bridge.playlistLoading
                           ? bridge.cancelPlaylist()
                           : dialog.submitPlaylist()
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8
            Label {
                text: dialog.strings.playlist_limit || ""
                font.pixelSize: 14
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
                objectName: "playlistClearList"
                text: dialog.strings.playlist_clear_list || ""
                variant: "secondary"
                dangerHover: true
                size: "compact"
                icon.source: dialog.appRoot.iconPath("trash")
                icon.width: 14
                icon.height: 14
                display: AbstractButton.TextBesideIcon
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
                         ? " \u00b7 " + dialog.appRoot.playlistSelCount + " " : "")
                font.pixelSize: 12
                color: dialog.appRoot ? dialog.appRoot.theme.textSecondary : "#4f5862"
            }
            AppButton {
                objectName: "playlistSelectAll"
                text: dialog.strings.btn_select_all || ""
                size: "compact"
                variant: "secondary"
                icon.source: dialog.appRoot.iconPath("add")
                icon.width: 14
                icon.height: 14
                display: AbstractButton.TextBesideIcon
                enabled: dialog.appRoot.playlistModelRef.count > 0
                onClicked: dialog.appRoot.selectAllPlaylist(true)
            }
            AppButton {
                objectName: "playlistSelectNone"
                text: dialog.strings.btn_select_none || ""
                size: "compact"
                variant: "secondary"
                icon.source: dialog.appRoot.iconPath("cancel")
                icon.width: 14
                icon.height: 14
                display: AbstractButton.TextBesideIcon
                enabled: dialog.appRoot.playlistModelRef.count > 0
                onClicked: dialog.appRoot.selectAllPlaylist(false)
            }
        }

        AppHintField {
            id: playlistFilter
            Layout.fillWidth: true
            hint: dialog.strings.filter_placeholder || ""
            strings: dialog.strings
            leadingIcon: dialog.appRoot.iconPath("search")
            selectByMouse: true
            tipEnabled: false
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
            Layout.minimumHeight: 140
            radius: 8
            color: dialog.appRoot ? dialog.appRoot.theme.tableBg : "#f5f8fd"
            border.width: 1
            border.color: dialog.appRoot ? dialog.appRoot.theme.cardBorder : "#d8e1ee"
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
                    width: playlistView.width - 16
                    property bool matches: dialog.appRoot.playlistMatches(model)
                    height: matches ? 50 : 0
                    visible: matches

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 6
                        anchors.rightMargin: 10
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
                                font.pixelSize: 13
                            }
                            Label {
                                Layout.fillWidth: true
                                text: model.url
                                elide: Text.ElideMiddle
                                font.pixelSize: 11
                                color: dialog.appRoot.theme.textSecondary
                            }
                        }
                        Label {
                            text: dialog.appRoot.formatDuration(model.duration)
                            font.pixelSize: 12
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
                objectName: "playlistCloseButton"
                text: dialog.strings.dlg_error_close || ""
                variant: "secondary"
                dangerHover: true
                icon.source: dialog.appRoot.iconPath("cancel")
                icon.width: 15
                icon.height: 15
                display: AbstractButton.TextBesideIcon
                onClicked: dialog.close()
            }
            AppButton {
                text: dialog.strings.btn_add_selected || ""
                variant: "tonal"
                icon.source: dialog.appRoot.tonalIcon("add", enabled)
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
                icon.source: dialog.appRoot.iconPath("play", enabled)
                icon.width: 16
                icon.height: 16
                display: AbstractButton.TextBesideIcon
                variant: "primary"
                enabled: dialog.appRoot.playlistSelCount > 0
                onClicked: {
                    dialog.appRoot.addSelectedPlaylist(true)
                    dialog.close()
                }
            }
        }
    }
}
