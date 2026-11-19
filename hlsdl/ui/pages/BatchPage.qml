import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

        Item {
    id: page
    objectName: "batchPage"
    property var appRoot
    property var strings: ({})
    property alias inputArea: inputArea
    property alias listView: listView
    property alias queueFilter: queueFilter
    property alias filterField: queueFilter
    readonly property bool showHero: width >= 1050 && height >= 650
    readonly property string batchSortKey: bridge.batchModel
                                               ? bridge.batchModel.sortKey : ""
    readonly property bool batchSortAscending: bridge.batchModel
                                                ? bridge.batchModel.sortAscending : true
    readonly property int batchTotalCount: appRoot ? appRoot.statTotal : 0

    function syncProxyStatusLabels() {
        if (!bridge.batchModel)
            return
        bridge.batchModel.statusLabels = {
            "waiting": appRoot.statusText("waiting"),
            "analyzing": appRoot.statusText("analyzing"),
            "downloading": appRoot.statusText("downloading"),
            "encoding": appRoot.statusText("encoding"),
            "verifying": appRoot.statusText("verifying"),
            "paused": appRoot.statusText("paused"),
            "done": appRoot.statusText("done"),
            "error": appRoot.statusText("error"),
            "cancelled": appRoot.statusText("cancelled"),
            "skipped": appRoot.statusText("skipped")
        }
    }

    function batchSourceIndex(displayIndex) {
        return bridge.batchModel ? bridge.batchModel.sourceIndexAt(displayIndex) : -1
    }

    function rowTitleAt(displayIndex) {
        return bridge.batchModel ? bridge.batchModel.titleAt(displayIndex) : ""
    }

    function rowProgressAt(displayIndex) {
        return bridge.batchModel ? bridge.batchModel.progressAt(displayIndex) : -1
    }

    function rowSourceAt(displayIndex) {
        return batchSourceIndex(displayIndex)
    }

    function rowCellXsAt(displayIndex) {
        var item = listView.itemAtIndex(displayIndex)
        if (!item)
            return []
        var layout = null
        for (var c = 0; c < item.children.length; c++) {
            if (item.children[c].objectName === "batchRowLayout") {
                layout = item.children[c]
                break
            }
        }
        if (!layout)
            return []
        var xs = []
        for (var i = 0; i < layout.children.length; i++)
            xs.push(layout.children[i].x)
        return xs
    }

    function rowCellRectsAt(displayIndex) {
        var item = listView.itemAtIndex(displayIndex)
        if (!item)
            return []
        var layout = null
        for (var c = 0; c < item.children.length; c++) {
            if (item.children[c].objectName === "batchRowLayout") {
                layout = item.children[c]
                break
            }
        }
        if (!layout)
            return []
        var rects = []
        for (var i = 0; i < layout.children.length; i++) {
            var cell = layout.children[i]
            rects.push({ x: cell.x, width: cell.width })
        }
        return rects
    }

    onStringsChanged: syncProxyStatusLabels()

    Connections {
        target: appRoot
        function onQueueFilterTextChanged() {
            if (bridge.batchModel)
                bridge.batchModel.filterText = appRoot.queueFilterText
        }
    }

    Component.onCompleted: {
        syncProxyStatusLabels()
        if (bridge.batchModel)
            bridge.batchModel.filterText = appRoot.queueFilterText
    }

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
                        anchors.margins: page.showHero ? 16 : 12
                        spacing: page.showHero ? 8 : 6

                        PageHero {
                            Layout.fillWidth: true
                            compact: !page.showHero
                            theme: appRoot.theme
                            title: strings.entry_title
                            description: strings.hero_batch_desc
                        }

                        AppHintArea {
                            id: inputArea
                            Layout.fillWidth: true
                            Layout.preferredHeight: page.showHero ? 66 : 60
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
                                tipTitle: strings.btn_add
                                tipText: strings.btn_add_tip
                                tipShortcut: "Ctrl+Enter"
                                onClicked: {
                                    if (bridge.addLinks(inputArea.text) > 0)
                                        inputArea.clear()
                                }
                            }
                            AppButton {
                                text: strings.btn_paste
                                variant: "secondary"
                                icon.source: appRoot.iconPath("copy")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                tipTitle: strings.btn_paste
                                tipText: strings.btn_paste_tip
                                tipShortcut: "Ctrl+V"
                                onClicked: {
                                    if (bridge.pasteFromClipboard() > 0)
                                        inputArea.clear()
                                }
                            }
                            AppButton {
                                text: strings.btn_import
                                variant: "secondary"
                                icon.source: appRoot.iconPath("file")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                tipTitle: strings.btn_import
                                tipText: strings.btn_import_tip
                                onClicked: bridge.importTxt()
                            }
                            AppButton {
                                text: strings.btn_clear; variant: "tertiary"; flat: true
                                icon.source: appRoot.iconPath("trash")
                                icon.width: 16; icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                tipTitle: strings.btn_clear
                                tipText: strings.btn_clear_tip
                                onClicked: inputArea.clear()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Label {
                                text: strings.batch_fmt_label; font.pixelSize: 13
                                color: appRoot.theme.textSecondary
                                Layout.alignment: Qt.AlignVCenter
                            }
                            AppFormatSelector {
                                strings: page.strings
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                text: appRoot.downloadSummary()
                                font.pixelSize: 11
                                color: appRoot.theme.textSecondary
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                            }
                            AppButton {
                                text: strings.batch_options
                                variant: "secondary"
                                Layout.alignment: Qt.AlignVCenter
                                onClicked: appRoot.openBatchOptions()
                            }
                        }

                        Label {
                            text: strings.entry_hint
                            visible: page.showHero
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
                                objectName: "batchFilter"
                                Layout.preferredWidth: 310
                                Layout.preferredHeight: 38
                                hint: strings.queue_filter_placeholder
                                leadingIcon: appRoot.iconPath("search")
                                selectByMouse: true
                                tipTitle: strings.queue_filter_title
                                tipText: strings.queue_filter_tip
                                tipShortcut: "Ctrl+F"
                                onTextChanged: {
                                    if (text.length === 0) {
                                        filterDebounce.stop()
                                        appRoot.queueFilterText = ""
                                    } else {
                                        filterDebounce.restart()
                                    }
                                }
                                Keys.onEscapePressed: clear()
                            }
                            Timer {
                                id: filterDebounce
                                interval: 180
                                onTriggered: appRoot.queueFilterText = queueFilter.text
                            }
                            AppToolButton {
                                display: AbstractButton.IconOnly
                                icon.source: appRoot.iconPath("cancel")
                                icon.width: 14
                                icon.height: 14
                                opacity: queueFilter.text.length > 0 ? 1 : 0
                                enabled: queueFilter.text.length > 0
                                Accessible.name: strings.filter_clear
                                tipTitle: strings.filter_clear
                                tipText: strings.filter_clear_tip
                                tipShortcut: "Esc"
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

                                TableSortHeader {
                                    objectName: "batchHeaderName"
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.minimumWidth: 180
                                    labelLeftMargin: 80
                                    label: strings.h_title
                                    sortKey: "name"
                                    activeKey: page.batchSortKey
                                    ascending: page.batchSortAscending
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.h_title
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_name_tip
                                    sortStateText: page.batchSortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: bridge.batchModel.sortBy("name")
                                }
                                TableSortHeader {
                                    objectName: "batchHeaderStatus"
                                    Layout.preferredWidth: 104
                                    Layout.minimumWidth: 104
                                    Layout.maximumWidth: 104
                                    Layout.fillHeight: true
                                    label: strings.h_status
                                    sortKey: "status"
                                    activeKey: page.batchSortKey
                                    ascending: page.batchSortAscending
                                    horizontalAlignment: Text.AlignHCenter
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.h_status
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_status_tip
                                    sortStateText: page.batchSortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: bridge.batchModel.sortBy("status")
                                }
                                TableSortHeader {
                                    objectName: "batchHeaderProgress"
                                    Layout.preferredWidth: 150
                                    Layout.minimumWidth: 150
                                    Layout.maximumWidth: 150
                                    Layout.fillHeight: true
                                    label: strings.h_progress
                                    sortKey: "progress"
                                    activeKey: page.batchSortKey
                                    ascending: page.batchSortAscending
                                    horizontalAlignment: Text.AlignHCenter
                                    textColor: appRoot.theme.tableHeaderText
                                    mutedColor: appRoot.theme.textMuted
                                    hoverColor: appRoot.theme.hover
                                    accentColor: appRoot.theme.accentText
                                    tipTitle: strings.h_progress
                                    tipText: strings.sort_tip
                                    tipFooter: strings.sort_progress_tip
                                    sortStateText: page.batchSortAscending
                                                   ? strings.sort_ascending
                                                   : strings.sort_descending
                                    onActivated: bridge.batchModel.sortBy("progress")
                                }
                                Item {
                                    objectName: "batchHeaderSpeed"
                                    Layout.preferredWidth: 130
                                    Layout.minimumWidth: 130
                                    Layout.maximumWidth: 130
                                    Layout.fillHeight: true
                                    Text {
                                        anchors.left: parent.left
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: strings.h_speed_size
                                        color: appRoot.theme.tableHeaderText
                                        font.pixelSize: 13
                                        font.bold: true
                                        elide: Text.ElideRight
                                    }
                                }
                                Item {
                                    objectName: "batchHeaderActions"
                                    Layout.preferredWidth: 136
                                    Layout.minimumWidth: 136
                                    Layout.maximumWidth: 136
                                    Layout.fillHeight: true
                                    Text {
                                        anchors.centerIn: parent
                                        text: strings.h_actions
                                        color: appRoot.theme.tableHeaderText
                                        font.pixelSize: 13
                                        font.bold: true
                                        horizontalAlignment: Text.AlignHCenter
                                        verticalAlignment: Text.AlignVCenter
                                    }
                                }
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: appRoot.theme.cardBorder }

                        ListView {
                            id: listView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: bridge.batchModel
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
                                visible: page.batchTotalCount === 0
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
                                        visible: listView.height >= 90
                                        text: strings.empty_hint; font.pixelSize: 12; color: appRoot.theme.textSecondary
                                    }
                                }
                            }
                            Column {
                                anchors.centerIn: parent
                                spacing: 4
                                visible: page.batchTotalCount > 0
                                         && page.batchFilterTokens.length > 0
                                         && listView.count === 0
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: strings.filter_no_results
                                    font.pixelSize: 13
                                    color: appRoot.theme.textSecondary
                                }
                                Label {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    text: strings.filter_no_results_hint
                                    font.pixelSize: 11
                                    color: appRoot.theme.textMuted
                                }
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
                        wrapMode: Text.Wrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }

                    ProgressBar {
                        Layout.preferredWidth: 180
                        visible: appRoot.width >= 1050
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
                        enabled: appRoot.statWaiting > 0
                        tipTitle: strings.btn_start
                        tipText: strings.btn_start_tip
                        tipShortcut: "F5"
                        onClicked: bridge.startQueue()
                    }
                    AppButton {
                        text: strings.btn_pause
                        icon.source: appRoot.iconPath("pause")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.queueActive && !bridge.queuePaused
                        tipTitle: strings.btn_pause
                        tipText: strings.btn_pause_tip
                        onClicked: bridge.pauseQueue()
                    }
                    AppButton {
                        text: strings.btn_resume
                        icon.source: appRoot.iconPath("play")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        visible: bridge.queueActive && bridge.queuePaused
                        highlighted: true
                        tipTitle: strings.btn_resume
                        tipText: strings.btn_resume_tip
                        onClicked: bridge.resumeQueue()
                    }
                    AppButton {
                        text: strings.btn_cancel_all
                        variant: "secondary"
                        icon.source: appRoot.iconPath("stop")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        enabled: appRoot.statWaiting + appRoot.statDownloading > 0
                        tipTitle: strings.btn_cancel_all
                        tipText: strings.btn_cancel_all_tip
                        onClicked: appRoot.openConfirmCancel()
                    }
                    AppButton {
                        text: strings.btn_clear_finished
                        variant: "secondary"
                        icon.source: appRoot.iconPath("trash")
                        icon.width: 16; icon.height: 16
                        display: AbstractButton.TextBesideIcon
                        enabled: appRoot.statDone + appRoot.statError + appRoot.statCancelled > 0
                        tipTitle: strings.btn_clear_finished
                        tipText: strings.btn_clear_finished_tip
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
            property int sourceIndex: model.sourceIndex
            height: 64
            visible: true
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
                MenuItem { text: strings.ctx_retry; visible: rowItem.final; onTriggered: bridge.retryItem(rowItem.sourceIndex) }
                MenuItem { text: strings.ctx_cancel; visible: rowItem.active || rowItem.st === "waiting"; onTriggered: bridge.cancelItem(rowItem.sourceIndex) }
                MenuItem { text: strings.ctx_remove; onTriggered: bridge.removeItem(rowItem.sourceIndex) }
            }

            RowLayout {
                objectName: "batchRowLayout"
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
                                if (bridge.editUrl(rowItem.sourceIndex, text)) {
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
                        id: statusBadge
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
                        AppToolTip {
                            target: statusBadge
                            title: appRoot.statusText(rowItem.st)
                            text: model.error
                            available: model.error.length > 0
                            delay: 400
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
                            tipTitle: strings.tip_edit
                            tipText: strings.tip_edit_tip
                            onClicked: rowItem.editing = true
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("copy")
                            icon.width: 16; icon.height: 16
                            Accessible.name: strings.tip_copy
                            tipTitle: strings.tip_copy
                            tipText: model.url
                            onClicked: bridge.copyLink(model.url)
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("retry")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.final
                            Accessible.name: strings.tip_retry
                            tipTitle: strings.tip_retry
                            tipText: strings.tip_retry_tip
                            onClicked: bridge.retryItem(rowItem.sourceIndex)
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("cancel")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.active || rowItem.st === "waiting"
                            Accessible.name: strings.tip_cancel
                            tipTitle: strings.tip_cancel
                            tipText: strings.tip_cancel_tip
                            onClicked: bridge.cancelItem(rowItem.sourceIndex)
                        }
                        AppToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.st === "done"
                            Accessible.name: strings.tip_open
                            tipTitle: strings.tip_open
                            tipText: model.path
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
