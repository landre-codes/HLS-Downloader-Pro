import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

        Item {
    id: page
    property var appRoot
    property var strings: ({})
    property alias inputArea: inputArea
    property alias listView: listView
    property alias queueFilter: queueFilter

    ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: batchEntryCol.implicitHeight + 32
                    radius: 12
                    color: appRoot.theme.cardBg
                    border.color: appRoot.theme.cardBorder
                    border.width: 1

                    ColumnLayout {
                        id: batchEntryCol
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16
                        spacing: 8

                        Label { text: strings.entry_title; font.pixelSize: 15; font.weight: Font.DemiBold }

                        AppHintArea {
                            id: inputArea
                            Layout.fillWidth: true
                            Layout.preferredHeight: 66
                            hint: strings.entry_placeholder
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 8
                            AppButton {
                                text: strings.btn_add; highlighted: true
                                icon.source: appRoot.iconPath("add")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                ToolTip.text: strings.btn_add_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: {
                                    if (bridge.addLinks(inputArea.text) > 0)
                                        inputArea.clear()
                                }
                            }
                            AppButton {
                                text: strings.btn_paste
                                icon.source: appRoot.iconPath("copy")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                ToolTip.text: strings.btn_paste_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: {
                                    if (bridge.pasteFromClipboard() > 0)
                                        inputArea.clear()
                                }
                            }
                            AppButton {
                                text: strings.btn_import
                                icon.source: appRoot.iconPath("file")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                ToolTip.text: strings.btn_import_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: bridge.importTxt()
                            }
                            AppButton {
                                text: strings.btn_clear; flat: true
                                icon.source: appRoot.iconPath("trash")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                ToolTip.text: strings.btn_clear_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: inputArea.clear()
                            }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 10
                            Label {
                                text: strings.batch_fmt_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary
                            }
                            AppFormatSelector {
                            strings: page.strings }
                            Label {
                                text: appRoot.downloadSummary()
                                font.pixelSize: 11
                                color: appRoot.theme.textSecondary
                                elide: Text.ElideRight
                                width: 260
                            }
                            AppButton {
                                text: strings.batch_options
                                onClicked: appRoot.openBatchOptions()
                            }
                        }

                        Label {
                            text: strings.entry_hint
                            font.pixelSize: 11
                            color: appRoot.theme.textSecondary
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }

                // Aviso de dependências (texto centralizado verticalmente).
                Rectangle {
                    Layout.fillWidth: true
                    visible: bridge.anyEssentialMissing
                    Layout.preferredHeight: warnRow.implicitHeight + 16
                    radius: 8
                    color: appRoot.theme.warningBg
                    RowLayout {
                        id: warnRow
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 8
                        spacing: 8
                        Label {
                            text: strings.warn_attention; font.bold: true; color: appRoot.theme.warningText
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Label {
                            text: (bridge.ytdlpAvailable ? "" : strings.warn_ytdlp_missing + " ")
                                  + (bridge.ffmpegAvailable ? "" : strings.warn_ffmpeg_missing + " ")
                                  + strings.warn_tools
                            color: appRoot.theme.warningText
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.Wrap
                        }
                        AppButton {
                            text: strings.dlg_deps_settings
                            Layout.alignment: Qt.AlignVCenter
                            onClicked: appRoot.goToSettingsTab()
                        }
                    }
                }

                // --------------------------------------------------- Fila
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
                            Layout.bottomMargin: 8
                            spacing: 8
                            Label { text: strings.queue_title; font.pixelSize: 15; font.weight: Font.DemiBold }
                            Item { Layout.fillWidth: true }
                            AppHintField {
                                id: queueFilter
                                Layout.preferredWidth: 280
                                hint: strings.filter_placeholder
                                leadingIcon: appRoot.iconPath("search")
                                selectByMouse: true
                                ToolTip.text: strings.filter_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onTextChanged: {
                                    if (text.length === 0) {
                                        filterDebounce.stop()
                                        appRoot.queueFilterText = ""
                                    } else {
                                        filterDebounce.restart()
                                    }
                                }
                            }
                            Timer {
                                id: filterDebounce
                                interval: 220
                                onTriggered: appRoot.queueFilterText = queueFilter.text.toLowerCase()
                            }
                            AppToolButton {
                                display: AbstractButton.IconOnly
                                icon.source: appRoot.iconPath("cancel")
                                icon.width: 14
                                icon.height: 14
                                opacity: queueFilter.text.length > 0 ? 1 : 0
                                enabled: queueFilter.text.length > 0
                                Accessible.name: strings.btn_clear
                                ToolTip.text: strings.btn_clear
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: queueFilter.clear()
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 36
                            radius: 6
                            color: appRoot.theme.tableHeaderBg

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                spacing: 10
                                Item { Layout.fillWidth: true; Layout.minimumWidth: 180 }
                                Label { text: strings.h_status; Layout.preferredWidth: 104; font.pixelSize: 13; font.bold: true; color: appRoot.theme.tableHeaderText }
                                Label { text: strings.h_progress; Layout.preferredWidth: 150; font.pixelSize: 13; font.bold: true; color: appRoot.theme.tableHeaderText; horizontalAlignment: Text.AlignHCenter }
                                Label { text: strings.h_speed_size; Layout.preferredWidth: 130; font.pixelSize: 13; font.bold: true; color: appRoot.theme.tableHeaderText }
                                Item { Layout.preferredWidth: 136 }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.theme.cardBorder }

                        ListView {
                            id: listView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: downloadModel
                            delegate: downloadDelegate
                            spacing: 0
                            ScrollBar.vertical: ScrollBar {}
                            boundsBehavior: Flickable.StopAtBounds
                            highlightMoveDuration: 0
                            highlight: Rectangle {
                                color: appRoot.theme.rowHighlight
                                visible: listView.currentIndex >= 0
                            }

                            Rectangle {
                                anchors.fill: parent
                                visible: listView.count === 0
                                color: "transparent"
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: strings.empty_title; font.pixelSize: 15; color: appRoot.theme.textSecondary
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: strings.empty_hint; font.pixelSize: 12; color: appRoot.theme.textSecondary
                                    }
                                }
                            }
                            Label {
                                anchors.centerIn: parent
                                visible: listView.count > 0
                                         && appRoot.queueFilterText.length > 0
                                         && listView.contentHeight <= 0
                                text: strings.filter_no_results
                                font.pixelSize: 13
                                color: appRoot.theme.textSecondary
                            }
                        }
                    }
                }

                // --------------------------------------------------- Barra de ações
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Label {
                        id: statsLabel
                        Layout.fillWidth: true
                        text: appRoot.statWaiting + " " + strings.stat_waiting + " · " + appRoot.statDownloading
                              + " " + strings.stat_downloading + " · " + appRoot.statDone + " "
                              + strings.stat_done + " · " + appRoot.statError + " " + strings.stat_errors
                              + " · " + appRoot.statCancelled + " " + strings.stat_cancelled
                        font.pixelSize: 12
                        color: appRoot.theme.textSecondary
                        elide: Text.ElideRight
                    }

                    ProgressBar {
                        Layout.preferredWidth: 180
                        value: {
                            var total = appRoot.statTotal
                            return total > 0
                                ? (appRoot.statDone + appRoot.statError + appRoot.statCancelled) / total
                                : 0
                        }
                        from: 0
                        to: 1
                    }

                    AppButton {
                        text: strings.btn_start; highlighted: true
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: !bridge.queueActive
                        ToolTip.text: strings.btn_start_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: bridge.startQueue()
                    }
                    AppButton {
                        text: strings.btn_pause
                        icon.source: appRoot.iconPath("pause")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.queueActive && !bridge.queuePaused
                        ToolTip.text: strings.btn_pause_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: bridge.pauseQueue()
                    }
                    AppButton {
                        text: strings.btn_resume
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.queueActive && bridge.queuePaused
                        highlighted: true
                        ToolTip.text: strings.btn_resume_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: bridge.resumeQueue()
                    }
                    AppButton {
                        text: strings.btn_cancel_all
                        icon.source: appRoot.iconPath("stop")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        ToolTip.text: strings.btn_cancel_all_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: appRoot.openConfirmCancel()
                    }
                    AppButton {
                        text: strings.btn_clear_finished
                        icon.source: appRoot.iconPath("trash")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        ToolTip.text: strings.btn_clear_finished_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: appRoot.openConfirmClear()
                    }
                }
            }
        
    Component {
        id: downloadDelegate
        Item {
            id: rowItem
            width: listView.width
            property bool editing: false
            property bool cancelEdit: false
            property string st: model.status
            property string filterText: appRoot.queueFilterText
            property bool matches: filterText.length === 0
                || String(model.title).toLowerCase().indexOf(filterText) !== -1
                || String(model.url).toLowerCase().indexOf(filterText) !== -1
            height: matches ? 64 : 0
            visible: matches
            property bool active: appRoot.isActive(st)
            property bool final: appRoot.isFinal(st)
            property bool canEdit: st === "waiting" || st === "error" || st === "cancelled"

            MouseArea {
                anchors.fill: parent
                acceptedButtons: Qt.RightButton
                onClicked: {
                    listView.currentIndex = index
                    rowMenu.popup()
                }
            }

            Menu {
                id: rowMenu
                MenuItem { text: strings.ctx_copy; onTriggered: bridge.copyLink(model.url) }
                MenuItem { text: strings.ctx_edit; visible: rowItem.canEdit; onTriggered: rowItem.editing = true }
                MenuItem { text: strings.ctx_open; visible: rowItem.st === "done"; onTriggered: bridge.openDownloadPath(model.path) }
                MenuItem { text: strings.ctx_retry; visible: rowItem.final; onTriggered: bridge.retryItem(index) }
                MenuItem { text: strings.ctx_cancel; visible: rowItem.active || rowItem.st === "waiting"; onTriggered: bridge.cancelItem(index) }
                MenuItem { text: strings.ctx_remove; onTriggered: bridge.removeItem(index) }
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                RowLayout {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 180
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 8

                    Rectangle {
                        Layout.preferredWidth: 72
                        Layout.preferredHeight: 40
                        Layout.alignment: Qt.AlignVCenter
                        radius: 4
                        color: appRoot.theme.thumbnailBg
                        border.color: appRoot.theme.thumbnailBorder
                        border.width: 1
                        Image {
                            anchors.fill: parent
                            visible: model.thumb !== ""
                            source: model.thumb
                            asynchronous: true
                            fillMode: Image.PreserveAspectCrop
                            clip: true
                        }
                        Image {
                            anchors.centerIn: parent
                            visible: model.thumb === ""
                            source: appRoot.iconPath("play")
                            sourceSize.width: 18
                            sourceSize.height: 18
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.alignment: Qt.AlignVCenter
                        spacing: 2

                        Label {
                            Layout.fillWidth: true
                            text: model.title
                            elide: Text.ElideMiddle
                            font.weight: Font.DemiBold
                            font.pixelSize: 13
                        }

                        TextField {
                            id: editField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 28
                            visible: rowItem.editing
                            leftPadding: 6
                            rightPadding: 6
                            topPadding: 2
                            bottomPadding: 2
                            font.pixelSize: 11
                            selectByMouse: true
                            onVisibleChanged: if (visible) { text = model.url; forceActiveFocus() }
                            onEditingFinished: {
                                if (rowItem.cancelEdit) {
                                    rowItem.cancelEdit = false
                                    return
                                }
                                if (!rowItem.editing)
                                    return
                                if (bridge.editUrl(index, text)) {
                                    rowItem.editing = false
                                } else {
                                    // Mantém o campo aberto para o usuário
                                    // corrigir URL duplicada/inválida.
                                    Qt.callLater(function() { editField.forceActiveFocus() })
                                }
                            }
                            Keys.onEscapePressed: {
                                rowItem.cancelEdit = true
                                rowItem.editing = false
                            }
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: !rowItem.editing
                            text: model.url
                            elide: Text.ElideMiddle
                            font.pixelSize: 11
                            color: appRoot.theme.textSecondary
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onDoubleClicked: rowItem.editing = true
                                onPressed: listView.currentIndex = index
                            }
                        }
                    }
                }

                Column {
                    Layout.preferredWidth: 104
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 3
                    Rectangle {
                        width: 104; height: 24; radius: 12
                        color: appRoot.badgeColor(rowItem.st)
                        Label {
                            anchors.fill: parent
                            anchors.margins: 4
                            text: appRoot.statusText(rowItem.st)
                            font.pixelSize: 11
                            font.bold: true
                            color: appRoot.theme.onAccent
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }
                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            ToolTip.text: model.error
                            ToolTip.visible: containsMouse && model.error.length > 0
                        }
                    }
                    Label {
                        width: parent.width
                        visible: rowItem.st === "error" && model.error.length > 0
                        text: model.error
                        elide: Text.ElideRight
                        font.pixelSize: 11
                        color: appRoot.theme.errorText
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: appRoot.showError(model.error)
                        }
                    }
                }

                Column {
                    Layout.preferredWidth: 150
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2
                    ProgressBar {
                        width: 150; height: 6
                        from: 0; to: 100
                        value: model.progress
                        indeterminate: rowItem.st === "analyzing"
                    }
                    Label {
                        anchors.right: parent.right
                        text: rowItem.st === "done" ? "100%" : Math.round(model.progress) + "%"
                        font.pixelSize: 11
                        color: appRoot.theme.textSecondary
                    }
                }

                Column {
                    Layout.preferredWidth: 130
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2
                    Label { width: parent.width; text: model.speed; font.pixelSize: 11; elide: Text.ElideRight }
                    Label { width: parent.width; text: model.size; font.pixelSize: 11; color: appRoot.theme.textSecondary; elide: Text.ElideRight }
                }

                Item {
                    Layout.preferredWidth: 136
                    Layout.alignment: Qt.AlignVCenter
                    Row {
                        anchors.centerIn: parent
                        spacing: 3
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("edit")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.canEdit
                            Accessible.name: strings.tip_edit
                            ToolTip.text: strings.tip_edit; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: rowItem.editing = true
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("copy")
                            icon.width: 16; icon.height: 16
                            Accessible.name: strings.tip_copy
                            ToolTip.text: strings.tip_copy; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.copyLink(model.url)
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("retry")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.final
                            Accessible.name: strings.tip_retry
                            ToolTip.text: strings.tip_retry; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.retryItem(index)
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("cancel")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.active || rowItem.st === "waiting"
                            Accessible.name: strings.tip_cancel
                            ToolTip.text: strings.tip_cancel; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.cancelItem(index)
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.st === "done"
                            Accessible.name: strings.tip_open
                            ToolTip.text: strings.tip_open; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.openDownloadPath(model.path)
                        }
                    }
                }
            }

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: appRoot.theme.divider
            }
        }
    }
}
