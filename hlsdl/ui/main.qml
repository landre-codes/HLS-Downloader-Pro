import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQml.Models
import "i18n.js" as I18n

// =============================================================================
// HLS Downloader Pro — Interface Qt Quick (Material Design)
//
//   - Abas: Individual | Lote | Playlists | Configurações.
//   - Formato (vídeo+áudio / vídeo / áudio), qualidade (144p–4K) e arquivo
//     (mp4/mkv/webm/avi/mov ou mp3/m4a/...).
//   - O SwipeView segue o TabBar por BINDING — nunca atribuir
//     `views.currentIndex` imperativamente. Troque de aba via
//     `tabBar.currentIndex`.
// =============================================================================

ApplicationWindow {
    id: root
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint
           | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
           | Qt.WindowSystemMenuHint
    width: 1160
    height: 800
    minimumWidth: 940
    minimumHeight: 620
    visible: false
    title: "HLS Downloader Pro"

    property bool dark: bridge.dark
    property var strings: ({})
    property string errorText: ""
    property string depsLog: ""
    property int playlistSelCount: 0

    function retranslate() {
        I18n.setLang(bridge.language)
        strings = I18n.getAll()
    }
    function statusText(s) { return strings["s_" + s] || s }
    function badgeColor(s) {
        switch (s) {
        case "done":        return "#2e7d32"
        case "error":       return "#c62828"
        case "downloading": return "#00838f"
        case "analyzing":   return "#b45309"
        case "encoding":    return "#6a1b9a"
        case "cancelled":   return "#546e7a"
        case "skipped":     return "#546e7a"
        default:            return "#455a64"
        }
    }
    function isActive(s) { return s === "analyzing" || s === "downloading" || s === "encoding" }
    function isFinal(s) { return s === "done" || s === "error" || s === "cancelled" }

    function startSingle() {
        var value = singleUrl.text.trim()
        if (value.length === 0)
            return
        bridge.downloadSingle(value)
        singleUrl.clear()
    }

    // ------------------------------------------------------------- playlists
    function rebuildPlaylistModel() {
        playlistModel.clear()
        var items = bridge.playlistItems
        for (var i = 0; i < items.length; i++) {
            playlistModel.append({
                idx: items[i].index,
                title: items[i].title,
                url: items[i].url,
                duration: items[i].duration,
                thumb: items[i].thumb,
                selected: false
            })
        }
        root.playlistSelCount = 0
    }
    function refreshSelCount() {
        var n = 0
        for (var i = 0; i < playlistModel.count; i++)
            if (playlistModel.get(i).selected)
                n++
        root.playlistSelCount = n
    }
    function selectAllPlaylist(flag) {
        for (var i = 0; i < playlistModel.count; i++)
            playlistModel.setProperty(i, "selected", flag)
        refreshSelCount()
    }
    function loadPlaylist() {
        var u = playlistUrl.text.trim()
        if (u.length === 0)
            return
        playlistModel.clear()
        root.playlistSelCount = 0
        bridge.loadPlaylist(u, playlistLimit.value)
    }
    function selectedPlaylistText() {
        var out = []
        for (var i = 0; i < playlistModel.count; i++) {
            var it = playlistModel.get(i)
            if (it.selected)
                out.push(it.url)
        }
        return out.join("\n")
    }
    function addSelectedPlaylist(start) {
        var text = selectedPlaylistText()
        if (text.length === 0)
            return
        if (start)
            bridge.addLinksAndStart(text)
        else
            bridge.addLinks(text)
    }
    function formatDuration(sec) {
        sec = Math.round(sec || 0)
        if (sec <= 0)
            return ""
        var m = Math.floor(sec / 60)
        var s = sec % 60
        return m + ":" + (s < 10 ? "0" + s : s)
    }

    // Caminho do ícone SVG conforme o tema.
    function iconPath(name) {
        return "icons/" + name + (root.dark ? "_dark.svg" : "_light.svg")
    }

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

    function isVideoPath(path) {
        var p = String(path).toLowerCase()
        return p.endsWith(".mp4") || p.endsWith(".mkv") || p.endsWith(".mov")
            || p.endsWith(".avi") || p.endsWith(".webm") || p.endsWith(".m4v")
            || p.endsWith(".ts")
    }

    // Resumo compacto do perfil de download (aba Lote).
    function downloadSummary() {
        if (bridge.formatMode === "audio_only")
            return bridge.container.toUpperCase()
        var quality = bridge.quality === "best"
            ? strings.q_best
            : bridge.quality + "p"
        var codec = bridge.codec === "copy"
            ? strings.codec_copy
            : (bridge.codec === "h264" ? "H.264" : "H.265")
        return quality + " · " + bridge.container.toUpperCase() + " · " + codec
    }

    // Seletor de formato (vídeo+áudio / vídeo / áudio).
    component FormatSelector: RowLayout {
        spacing: 14
        ButtonGroup { id: fmtGroup }
        Repeater {
            model: [
                { value: "video_audio", label: root.strings.fmt_video_audio },
                { value: "video_only", label: root.strings.fmt_video_only },
                { value: "audio_only", label: root.strings.fmt_audio_only }
            ]
            delegate: RadioButton {
                text: modelData.label
                checked: bridge.formatMode === modelData.value
                Binding on checked { value: bridge.formatMode === modelData.value }
                ButtonGroup.group: fmtGroup
                onToggled: if (checked) bridge.setFormatMode(modelData.value)
            }
        }
    }

    // Seletor de qualidade (144p–4K).
    component QualityCombo: ComboBox {
        property var items: [
            { text: root.strings.q_best, value: "best" },
            { text: "2160p (4K)", value: "2160" },
            { text: "1440p (2K)", value: "1440" },
            { text: "1080p", value: "1080" },
            { text: "720p", value: "720" },
            { text: "480p", value: "480" },
            { text: "360p", value: "360" },
            { text: "240p", value: "240" },
            { text: "144p", value: "144" }
        ]
        model: items
        textRole: "text"
        valueRole: "value"
        currentIndex: {
            for (var i = 0; i < items.length; i++)
                if (items[i].value === bridge.quality)
                    return i
            return 0
        }
        onActivated: bridge.setQuality(currentValue)
        Layout.preferredWidth: 170
    }

    // Seletor de arquivo/contêiner (depende do modo de formato).
    component ContainerCombo: ComboBox {
        property var items: bridge.formatMode === "audio_only"
            ? ["mp3", "m4a", "wav", "flac", "opus"]
            : ["mp4", "mkv", "webm", "avi", "mov"]
        model: items
        currentIndex: Math.max(0, items.indexOf(bridge.container))
        onActivated: bridge.setContainer(currentText)
        Layout.preferredWidth: 110
    }

    // Compressão: original (sem reencode), H.264 ou H.265 (HEVC).
    component CodecCombo: ComboBox {
        property var items: [
            { text: root.strings.codec_copy, value: "copy" },
            { text: root.strings.codec_h264, value: "h264" },
            { text: root.strings.codec_h265, value: "h265" }
        ]
        model: items
        textRole: "text"
        valueRole: "value"
        currentIndex: {
            for (var i = 0; i < items.length; i++)
                if (items[i].value === bridge.codec)
                    return i
            return 0
        }
        onActivated: bridge.setCodec(currentValue)
        Layout.preferredWidth: 180
    }

    // Nível de compressão (quanto menor a CRF, maior a qualidade/tamanho).
    component CompressCombo: ComboBox {
        property var items: [
            { text: root.strings.compress_light, value: "light" },
            { text: root.strings.compress_medium, value: "medium" },
            { text: root.strings.compress_strong, value: "strong" }
        ]
        model: items
        textRole: "text"
        valueRole: "value"
        currentIndex: {
            for (var i = 0; i < items.length; i++)
                if (items[i].value === bridge.compressLevel)
                    return i
            return 1
        }
        onActivated: bridge.setCompressLevel(currentValue)
        Layout.preferredWidth: 130
    }

    ListModel { id: playlistModel }

    Connections {
        target: bridge
        function onLanguageChanged() { retranslate() }
    }
    Component.onCompleted: {
        retranslate()
        if (bridge.anyEssentialMissing && !bridge.depsPromptDismissed)
            depsDialog.open()
    }

    Material.theme: root.dark ? Material.Dark : Material.Light
    Material.accent: "#1e88e5"
    Material.background: root.dark ? "#14181c" : "#f5f5f5"

    property int statWaiting: 0
    property int statDownloading: 0
    property int statDone: 0
    property int statError: 0
    property int statTotal: 0
    property int compWait: 0
    property int compWork: 0
    property int compDone: 0
    property int compErr: 0
    property int compSkip: 0

    onClosing: bridge.saveGeometry(
        root.x, root.y, root.width, root.height,
        root.visibility === Window.Maximized
    )

    onVisibilityChanged: {
        if (root.visibility === Window.Maximized && root.screen)
            root.setGeometry(root.screen.availableGeometry)
    }

    // ====================================================== Atalhos
    readonly property bool typing: {
        var item = Window.activeFocusItem
        return item !== null && (item instanceof TextInput || item instanceof TextEdit)
    }
    Shortcut { sequence: "Ctrl+V"; enabled: !root.typing; onActivated: bridge.pasteFromClipboard() }
    Shortcut { sequence: "Ctrl+Return"; onActivated: { bridge.addLinks(inputArea.text); inputArea.clear() } }
    Shortcut { sequence: "Ctrl+Enter"; onActivated: { bridge.addLinks(inputArea.text); inputArea.clear() } }
    Shortcut { sequence: "F5"; onActivated: bridge.startQueue() }
    Shortcut {
        sequence: "Delete"
        enabled: !root.typing
        onActivated: if (listView.currentIndex >= 0) bridge.removeItem(listView.currentIndex)
    }

    DropArea {
        anchors.fill: parent
        onDropped: function (drop) {
            var videos = []
            if (drop.hasUrls) {
                for (var i = 0; i < drop.urls.length; i++) {
                    var url = drop.urls[i]
                    var local = url.toLocalFile()
                    var lower = String(local).toLowerCase()
                    if (local !== "" && lower.endsWith(".txt"))
                        bridge.importTxtPath(local)
                    else if (local !== "" && root.isVideoPath(local))
                        videos.push(local)
                    else if (local !== "")
                        bridge.addLinks(String(url))
                    else
                        bridge.addLinks(String(url))
                }
            } else if (drop.hasText) {
                bridge.addLinks(drop.text)
            }
            if (videos.length > 0) {
                bridge.addCompressionPaths(videos)
                tabBar.currentIndex = 3
            }
            drop.accept()
        }
    }

    Connections {
        target: bridge
        function onStatsChanged(waiting, downloading, done, errors) {
            root.statWaiting = waiting
            root.statDownloading = downloading
            root.statDone = done
            root.statError = errors
            root.statTotal = waiting + downloading + done + errors
        }
        function onNotifyText(message) {
            toastText.text = message
            toast.visible = true
            toastTimer.restart()
        }
        function onDepsOutput(line) {
            root.depsLog += line + "\n"
            if (root.depsLog.length > 20000)
                root.depsLog = root.depsLog.substring(root.depsLog.length - 12000)
        }
        function onPlaylistChanged() { root.rebuildPlaylistModel() }
        function onCompressionStatsChanged(waiting, working, done, errors, skipped) {
            root.compWait = waiting
            root.compWork = working
            root.compDone = done
            root.compErr = errors
            root.compSkip = skipped
        }
    }

    // ============================================================ BARRA DE TÍTULO
    Rectangle {
        id: titleBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 44
        color: root.dark ? "#101419" : "#e9ebee"
        z: 60

        MouseArea {
            id: dragArea
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            cursorShape: Qt.ArrowCursor
            property bool pending: false
            property bool moveStarted: false

            Timer {
                id: dragTimer
                interval: 220
                onTriggered: {
                    if (dragArea.pending && root.visibility !== Window.Maximized) {
                        dragArea.moveStarted = true
                        root.startSystemMove()
                    }
                    dragArea.pending = false
                }
            }
            onPressed: {
                dragArea.pending = true
                dragArea.moveStarted = false
                dragTimer.restart()
            }
            onDoubleClicked: {
                dragArea.pending = false
                dragTimer.stop()
                if (dragArea.moveStarted)
                    return
                if (root.visibility === Window.Maximized)
                    root.showNormal()
                else
                    root.showMaximized()
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 6
            spacing: 8

            Rectangle { width: 10; height: 30; radius: 5; color: Material.accent }
            Label {
                text: "HLS Downloader Pro"
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: root.dark ? "#e8ebee" : "#202428"
            }
            Label {
                text: strings.titlebar_sub + "  ·  v" + bridge.appVersion
                font.pixelSize: 11
                color: root.dark ? "#7f8892" : "#6a7078"
                Layout.topMargin: 6
            }
            Item { Layout.fillWidth: true }
            Rectangle { width: 1; height: 18; color: root.dark ? "#2a323a" : "#d3d7db" }

            Rectangle {
                id: minBtn
                width: 46; height: 30; radius: 6
                color: minHov.containsMouse ? (root.dark ? "#2a323a" : "#d8dce0") : "transparent"
                Label { anchors.centerIn: parent; text: "—"; font.pixelSize: 14; color: root.dark ? "#dfe3e8" : "#3c4043" }
                MouseArea { id: minHov; anchors.fill: parent; hoverEnabled: true; onClicked: root.showMinimized() }
            }
            Rectangle {
                id: maxBtn
                width: 46; height: 30; radius: 6
                color: maxHov.containsMouse ? (root.dark ? "#2a323a" : "#d8dce0") : "transparent"
                Label { anchors.centerIn: parent; text: root.visibility === Window.Maximized ? "❐" : "▢"; font.pixelSize: 14; color: root.dark ? "#dfe3e8" : "#3c4043" }
                MouseArea {
                    id: maxHov; anchors.fill: parent; hoverEnabled: true
                    onClicked: if (root.visibility === Window.Maximized) root.showNormal(); else root.showMaximized()
                }
            }
            Rectangle {
                id: closeBtn
                width: 46; height: 30; radius: 6
                color: closeHov.containsMouse ? "#c62828" : "transparent"
                Label { anchors.centerIn: parent; text: "✕"; font.pixelSize: 14; color: root.dark ? "#dfe3e8" : "#3c4043" }
                MouseArea { id: closeHov; anchors.fill: parent; hoverEnabled: true; onClicked: root.close() }
            }
        }
    }

    // ================================================== ABAS
    TabBar {
        id: tabBar
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        contentHeight: 42
        background: Rectangle { color: root.dark ? "#181d22" : "#eef0f3" }
        TabButton {
            text: strings.tab_single; font.pixelSize: 13; implicitWidth: 170
            ToolTip.text: strings.tab_single_tip; ToolTip.visible: hovered; ToolTip.delay: 500
        }
        TabButton {
            text: strings.tab_downloads; font.pixelSize: 13; implicitWidth: 130
            ToolTip.text: strings.tab_downloads_tip; ToolTip.visible: hovered; ToolTip.delay: 500
        }
        TabButton {
            text: strings.tab_playlist; font.pixelSize: 13; implicitWidth: 130
            ToolTip.text: strings.tab_playlist_tip; ToolTip.visible: hovered; ToolTip.delay: 500
        }
        TabButton {
            text: strings.tab_compress; font.pixelSize: 13; implicitWidth: 130
            ToolTip.text: strings.tab_compress_tip; ToolTip.visible: hovered; ToolTip.delay: 500
        }
        TabButton {
            text: strings.tab_settings; font.pixelSize: 13; implicitWidth: 150
            ToolTip.text: strings.tab_settings_tip; ToolTip.visible: hovered; ToolTip.delay: 500
        }
    }

    SwipeView {
        id: views
        anchors.top: tabBar.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        currentIndex: tabBar.currentIndex
        interactive: false

        // ==================================================== ABA INDIVIDUAL
        Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: singleCol.implicitHeight + 32
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1
                    ColumnLayout {
                        id: singleCol
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16
                        spacing: 12
                        Label { text: strings.single_title; font.pixelSize: 15; font.weight: Font.DemiBold }

                        TextField {
                            id: singleUrl
                            Layout.fillWidth: true
                            placeholderText: strings.single_url_placeholder
                            selectByMouse: true
                            onAccepted: root.startSingle()
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                text: strings.fmt_label; font.pixelSize: 13
                                color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter
                            }
                            FormatSelector { Layout.alignment: Qt.AlignVCenter }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                visible: bridge.formatMode !== "audio_only"
                                text: strings.quality_label; font.pixelSize: 13
                                color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter
                            }
                            QualityCombo {
                                visible: bridge.formatMode !== "audio_only"
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Item { Layout.fillWidth: true }
                            Label {
                                text: strings.container_label; font.pixelSize: 13
                                color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter
                            }
                            ContainerCombo { Layout.alignment: Qt.AlignVCenter }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Label {
                                visible: bridge.formatMode !== "audio_only"
                                text: strings.codec_label; font.pixelSize: 13
                                color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter
                            }
                            CodecCombo {
                                visible: bridge.formatMode !== "audio_only"
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Label {
                                visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
                                text: strings.compress_label; font.pixelSize: 13
                                color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter
                            }
                            CompressCombo {
                                visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12
                            Button {
                                text: strings.btn_download_now; highlighted: true
                                onClicked: root.startSingle()
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Label {
                            text: strings.single_hint
                            font.pixelSize: 11
                            color: Material.secondaryTextColor
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 12
                        Label { text: strings.single_progress; font.pixelSize: 15; font.weight: Font.DemiBold }

                        Label {
                            visible: bridge.lastItem.url === undefined || bridge.lastItem.url === ""
                            text: strings.single_idle
                            color: Material.secondaryTextColor
                            font.pixelSize: 13
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            visible: bridge.lastItem.url !== undefined && bridge.lastItem.url !== ""
                            spacing: 10

                            Label {
                                Layout.fillWidth: true
                                text: bridge.lastItem.title
                                elide: Text.ElideMiddle
                                font.weight: Font.DemiBold
                                font.pixelSize: 14
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Rectangle {
                                    width: 120; height: 24; radius: 12
                                    color: root.badgeColor(bridge.lastItem.status)
                                    Label {
                                        anchors.centerIn: parent
                                        text: root.statusText(bridge.lastItem.status)
                                        color: "white"; font.pixelSize: 11; font.bold: true
                                    }
                                }
                                Label {
                                    Layout.fillWidth: true
                                    text: bridge.lastItem.speed + "   " + bridge.lastItem.size
                                    color: Material.secondaryTextColor
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
                                visible: bridge.lastItem.status === "error" && bridge.lastItem.error.length > 0
                                text: bridge.lastItem.error
                                color: root.dark ? "#ff8a80" : "#c62828"
                                wrapMode: Text.Wrap
                                font.pixelSize: 12
                            }

                            RowLayout {
                                spacing: 10
                                Button {
                                    visible: bridge.lastItem.status === "done"
                                    text: strings.btn_open
                                    onClicked: bridge.openDownloadPath(bridge.lastItem.path)
                                }
                                Item { Layout.fillWidth: true }
                            }
                        }

                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }

        // ========================================================== ABA LOTE
        Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: batchEntryCol.implicitHeight + 32
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1

                    ColumnLayout {
                        id: batchEntryCol
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16
                        spacing: 8

                        Label { text: strings.entry_title; font.pixelSize: 15; font.weight: Font.DemiBold }

                        TextArea {
                            id: inputArea
                            Layout.fillWidth: true
                            Layout.preferredHeight: 66
                            placeholderText: strings.entry_placeholder
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Button {
                                text: strings.btn_add; highlighted: true
                                ToolTip.text: strings.btn_add_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: { bridge.addLinks(inputArea.text); inputArea.clear() }
                            }
                            Button {
                                text: strings.btn_paste
                                ToolTip.text: strings.btn_paste_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: { bridge.pasteFromClipboard(); inputArea.clear() }
                            }
                            Button {
                                text: strings.btn_import
                                ToolTip.text: strings.btn_import_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: bridge.importTxt()
                            }
                            Item { Layout.fillWidth: true }
                            Button {
                                text: strings.btn_clear; flat: true
                                ToolTip.text: strings.btn_clear_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                onClicked: inputArea.clear()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Label {
                                text: strings.batch_fmt_label; font.pixelSize: 13
                                color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter
                            }
                            FormatSelector { Layout.alignment: Qt.AlignVCenter }
                            Item { Layout.fillWidth: true }
                            Label {
                                text: root.downloadSummary()
                                font.pixelSize: 11
                                color: Material.secondaryTextColor
                                elide: Text.ElideRight
                                Layout.maximumWidth: 260
                                Layout.alignment: Qt.AlignVCenter
                            }
                            Button {
                                text: strings.batch_options
                                onClicked: batchOptionsDialog.open()
                            }
                        }

                        Label {
                            text: strings.entry_hint
                            font.pixelSize: 11
                            color: Material.secondaryTextColor
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
                    color: "#4a2c1f"
                    RowLayout {
                        id: warnRow
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 8
                        spacing: 8
                        Label {
                            text: strings.warn_attention; font.bold: true; color: "#ffcc80"
                            Layout.alignment: Qt.AlignVCenter
                        }
                        Label {
                            text: (bridge.ytdlpAvailable ? "" : strings.warn_ytdlp_missing + " ")
                                  + (bridge.ffmpegAvailable ? "" : strings.warn_ffmpeg_missing + " ")
                                  + strings.warn_tools
                            color: "#ffcc80"
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            verticalAlignment: Text.AlignVCenter
                            wrapMode: Text.Wrap
                        }
                        Button {
                            text: strings.dlg_deps_settings
                            Layout.alignment: Qt.AlignVCenter
                            onClicked: tabBar.currentIndex = 4
                        }
                    }
                }

                // --------------------------------------------------- Fila
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6

                        Label { text: strings.queue_title; font.pixelSize: 15; font.weight: Font.DemiBold }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Item { Layout.fillWidth: true; Layout.minimumWidth: 180 }
                            Label { text: strings.h_status; Layout.preferredWidth: 104; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor }
                            Label { text: strings.h_progress; Layout.preferredWidth: 150; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor; horizontalAlignment: Text.AlignHCenter }
                            Label { text: strings.h_speed_size; Layout.preferredWidth: 130; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor }
                            Item { Layout.preferredWidth: 136 }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: root.dark ? "#2a323a" : "#e0e0e0" }

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
                                color: root.dark ? "#223038" : "#e3f3f0"
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
                                        text: strings.empty_title; font.pixelSize: 15; color: Material.secondaryTextColor
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: strings.empty_hint; font.pixelSize: 12; color: Material.secondaryTextColor
                                    }
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
                        text: root.statWaiting + " " + strings.stat_waiting + " · " + root.statDownloading
                              + " " + strings.stat_downloading + " · " + root.statDone + " "
                              + strings.stat_done + " · " + root.statError + " " + strings.stat_errors
                        font.pixelSize: 12
                        color: Material.secondaryTextColor
                        elide: Text.ElideRight
                    }

                    ProgressBar {
                        Layout.preferredWidth: 180
                        value: {
                            var total = downloadModel.rowCount()
                            return total > 0 ? (root.statDone + root.statError) / total : 0
                        }
                        from: 0
                        to: 1
                    }

                    Button {
                        text: strings.btn_start; highlighted: true
                        visible: !bridge.queueActive
                        ToolTip.text: strings.btn_start_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: bridge.startQueue()
                    }
                    Button {
                        text: strings.btn_pause
                        visible: bridge.queueActive && !bridge.queuePaused
                        ToolTip.text: strings.btn_pause_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: bridge.pauseQueue()
                    }
                    Button {
                        text: strings.btn_resume
                        visible: bridge.queueActive && bridge.queuePaused
                        highlighted: true
                        ToolTip.text: strings.btn_resume_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: bridge.resumeQueue()
                    }
                    Button {
                        text: strings.btn_cancel_all
                        ToolTip.text: strings.btn_cancel_all_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: confirmCancel.open()
                    }
                    Button {
                        text: strings.btn_clear_finished
                        ToolTip.text: strings.btn_clear_finished_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                        onClicked: confirmClear.open()
                    }
                }
            }
        }

        // ===================================================== ABA PLAYLISTS
        Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: plLoadCol.implicitHeight + 32
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
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
                            TextField {
                                id: playlistUrl
                                Layout.fillWidth: true
                                placeholderText: strings.playlist_url_placeholder
                                selectByMouse: true
                                onAccepted: root.loadPlaylist()
                            }
                            Button {
                                text: bridge.playlistLoading ? strings.playlist_loading : strings.btn_load_playlist
                                enabled: !bridge.playlistLoading
                                highlighted: true
                                onClicked: root.loadPlaylist()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Label { text: strings.playlist_limit; font.pixelSize: 13; color: Material.secondaryTextColor; Layout.alignment: Qt.AlignVCenter }
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
                            color: Material.secondaryTextColor
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
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
                                text: playlistModel.count + " " + strings.playlist_items
                                      + (root.playlistSelCount > 0 ? " · " + root.playlistSelCount + " ✓" : "")
                                font.pixelSize: 13
                                color: Material.secondaryTextColor
                            }
                            Button {
                                text: strings.btn_select_all
                                enabled: playlistModel.count > 0
                                onClicked: root.selectAllPlaylist(true)
                            }
                            Button {
                                text: strings.btn_select_none
                                enabled: playlistModel.count > 0
                                onClicked: root.selectAllPlaylist(false)
                            }
                        }

                        Rectangle { Layout.fillWidth: true; height: 1; color: root.dark ? "#2a323a" : "#e0e0e0" }

                        ListView {
                            id: playlistView
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: playlistModel
                            spacing: 0
                            ScrollBar.vertical: ScrollBar {}
                            boundsBehavior: Flickable.StopAtBounds

                            Rectangle {
                                anchors.fill: parent
                                visible: playlistView.count === 0
                                color: "transparent"
                                Label {
                                    anchors.centerIn: parent
                                    text: strings.playlist_empty_ui
                                    font.pixelSize: 13
                                    color: Material.secondaryTextColor
                                }
                            }

                            delegate: Item {
                                width: playlistView.width
                                height: 52
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 6
                                    anchors.rightMargin: 6
                                    spacing: 8
                                    CheckBox {
                                        id: selBox
                                        Binding on checked { value: model.selected }
                                        onClicked: {
                                            model.selected = selBox.checked
                                            root.refreshSelCount()
                                        }
                                    }
                                    Label {
                                        text: model.idx
                                        font.pixelSize: 11
                                        color: Material.secondaryTextColor
                                        Layout.preferredWidth: 34
                                    }
                                    Rectangle {
                                        Layout.preferredWidth: 64
                                        Layout.preferredHeight: 36
                                        Layout.alignment: Qt.AlignVCenter
                                        radius: 4
                                        color: root.dark ? "#262e35" : "#eef0f3"
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
                                        Label { Layout.fillWidth: true; text: model.url; elide: Text.ElideMiddle; font.pixelSize: 10; color: Material.secondaryTextColor }
                                    }
                                    Label {
                                        text: root.formatDuration(model.duration)
                                        font.pixelSize: 11
                                        color: Material.secondaryTextColor
                                        Layout.preferredWidth: 48
                                    }
                                }
                                Rectangle {
                                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                    height: 1
                                    color: root.dark ? "#262e35" : "#ececec"
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Button {
                                text: strings.btn_add_selected
                                enabled: root.playlistSelCount > 0
                                onClicked: root.addSelectedPlaylist(false)
                            }
                            Button {
                                text: strings.btn_download_selected
                                highlighted: true
                                enabled: root.playlistSelCount > 0
                                onClicked: root.addSelectedPlaylist(true)
                            }
                            Item { Layout.fillWidth: true }
                        }
                    }
                }
            }
        }

        // ===================================================== ABA COMPRESSÃO
        Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: compOpts.implicitHeight + 32
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1
                    ColumnLayout {
                        id: compOpts
                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                        anchors.margins: 16
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Label {
                                text: strings.compress_title
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                Layout.fillWidth: true
                            }
                            Button {
                                text: strings.compress_add_files
                                onClicked: bridge.addCompressionFiles()
                            }
                            Button {
                                text: strings.compress_add_folder
                                onClicked: bridge.addCompressionFolder()
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Label { text: strings.compress_encoder; font.pixelSize: 13; color: Material.secondaryTextColor }
                            ComboBox {
                                id: compEncoder
                                model: bridge.compressionEncoders
                                textRole: "name"
                                valueRole: "key"
                                currentIndex: {
                                    for (var i = 0; i < model.length; i++)
                                        if (model[i].key === bridge.compressionEncoder)
                                            return i
                                    return 0
                                }
                                Layout.preferredWidth: 200
                                onActivated: bridge.setCompressionEncoder(currentValue)
                            }
                            Label { text: strings.compress_quality; font.pixelSize: 13; color: Material.secondaryTextColor }
                            SpinBox {
                                id: compQuality
                                from: 1; to: 51
                                value: bridge.compressionQuality
                                editable: true
                                ToolTip.text: strings.compress_quality_tip
                                ToolTip.visible: hovered; ToolTip.delay: 500
                                onValueChanged: if (value !== bridge.compressionQuality) bridge.setCompressionQuality(value)
                            }
                            Item { Layout.fillWidth: true }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Label { text: strings.compress_speed; font.pixelSize: 13; color: Material.secondaryTextColor }
                            ComboBox {
                                id: compSpeed
                                model: [
                                    { text: strings.compress_speed_fast, value: "fast" },
                                    { text: strings.compress_speed_balanced, value: "balanced" },
                                    { text: strings.compress_speed_slow, value: "slow" }
                                ]
                                textRole: "text"
                                valueRole: "value"
                                currentIndex: bridge.compressionSpeed === "fast" ? 0
                                              : (bridge.compressionSpeed === "slow" ? 2 : 1)
                                Layout.preferredWidth: 150
                                onActivated: bridge.setCompressionSpeed(currentValue)
                            }
                            Label { text: strings.compress_parallel; font.pixelSize: 13; color: Material.secondaryTextColor }
                            SpinBox {
                                id: compParallel
                                from: 1; to: 8
                                value: bridge.compressionParallel
                                editable: true
                                onValueChanged: if (value !== bridge.compressionParallel) bridge.setCompressionParallel(value)
                            }
                            Label { text: strings.compress_min_size; font.pixelSize: 13; color: Material.secondaryTextColor }
                            SpinBox {
                                id: compMinSize
                                from: 0; to: 100000
                                stepSize: 100
                                value: bridge.compressionMinSizeMB
                                editable: true
                                onValueChanged: if (value !== bridge.compressionMinSizeMB) bridge.setCompressionMinSizeMB(value)
                            }
                            Item { Layout.fillWidth: true }
                        }

                        Flow {
                            Layout.fillWidth: true
                            spacing: 12
                            CheckBox {
                                text: strings.compress_only_smaller
                                checked: bridge.compressionOnlyIfSmaller
                                onToggled: bridge.setCompressionOnlyIfSmaller(checked)
                            }
                            CheckBox {
                                text: strings.compress_replace_original
                                checked: bridge.compressionReplaceOriginal
                                onToggled: bridge.setCompressionReplaceOriginal(checked)
                            }
                            CheckBox {
                                text: strings.compress_reencode_hevc
                                checked: bridge.compressionReencodeHevc
                                onToggled: bridge.setCompressionReencodeHevc(checked)
                            }
                            CheckBox {
                                text: strings.compress_skip_hdr
                                checked: bridge.compressionSkipHdr
                                onToggled: bridge.setCompressionSkipHdr(checked)
                            }
                        }

                        Label {
                            text: strings.compress_hint
                            font.pixelSize: 11
                            color: Material.secondaryTextColor
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 12
                        spacing: 6
                        Label { text: strings.compress_queue; font.pixelSize: 15; font.weight: Font.DemiBold }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Item { Layout.fillWidth: true; Layout.minimumWidth: 160 }
                            Label { text: strings.h_status; Layout.preferredWidth: 110; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor }
                            Label { text: strings.h_progress; Layout.preferredWidth: 150; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor; horizontalAlignment: Text.AlignHCenter }
                            Label { text: strings.compress_col_result; Layout.preferredWidth: 190; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor }
                            Item { Layout.preferredWidth: 76 }
                        }
                        Rectangle { Layout.fillWidth: true; height: 1; color: root.dark ? "#2a323a" : "#e0e0e0" }

                        ListView {
                            id: compList
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            clip: true
                            model: compressionModel
                            spacing: 0
                            ScrollBar.vertical: ScrollBar {}
                            boundsBehavior: Flickable.StopAtBounds

                            Rectangle {
                                anchors.fill: parent
                                visible: compList.count === 0
                                color: "transparent"
                                Label {
                                    anchors.centerIn: parent
                                    text: strings.compress_empty
                                    font.pixelSize: 13
                                    color: Material.secondaryTextColor
                                }
                            }

                            delegate: Item {
                                width: compList.width
                                height: 58
                                property string st: model.status
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 8
                                    anchors.rightMargin: 8
                                    spacing: 10
                                    Label {
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 160
                                        text: model.name
                                        elide: Text.ElideMiddle
                                        font.pixelSize: 12
                                        font.weight: Font.DemiBold
                                    }
                                    Item {
                                        Layout.preferredWidth: 110
                                        Rectangle {
                                            width: 104; height: 24; radius: 12
                                            anchors.centerIn: parent
                                            color: root.badgeColor(root.st)
                                            Label {
                                                anchors.centerIn: parent
                                                text: root.statusText(root.st)
                                                color: "white"; font.pixelSize: 11; font.bold: true
                                            }
                                        }
                                    }
                                    Column {
                                        Layout.preferredWidth: 150
                                        spacing: 2
                                        ProgressBar {
                                            width: 150; height: 6
                                            from: 0; to: 100
                                            value: model.progress
                                            indeterminate: root.st === "analyzing"
                                        }
                                        Label {
                                            anchors.right: parent.right
                                            text: root.st === "done" ? "100%" : Math.round(model.progress) + "%"
                                            font.pixelSize: 10
                                            color: Material.secondaryTextColor
                                        }
                                    }
                                    Column {
                                        Layout.preferredWidth: 190
                                        spacing: 2
                                        Label {
                                            width: parent.width
                                            text: root.formatBytes(model.sizeBefore) + " → "
                                                  + (model.sizeAfter > 0 ? root.formatBytes(model.sizeAfter) : "—")
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                        Label {
                                            width: parent.width
                                            text: model.saving > 0
                                                  ? (model.saving + "% " + strings.compress_saving)
                                                  : (model.error.length > 0 ? model.error : model.speed)
                                            font.pixelSize: 10
                                            color: model.error.length > 0
                                                   ? (root.dark ? "#ff8a80" : "#c62828")
                                                   : Material.secondaryTextColor
                                            elide: Text.ElideRight
                                        }
                                    }
                                    Row {
                                        Layout.preferredWidth: 76
                                        spacing: 4
                                        ToolButton {
                                            width: 32; height: 28
                                            display: AbstractButton.IconOnly
                                            icon.source: root.iconPath("cancel")
                                            icon.width: 16; icon.height: 16
                                            visible: root.st === "waiting" || root.st === "analyzing" || root.st === "encoding"
                                            Accessible.name: strings.tip_cancel
                                            onClicked: bridge.cancelCompressionItem(index)
                                        }
                                        ToolButton {
                                            width: 32; height: 28
                                            display: AbstractButton.IconOnly
                                            icon.source: root.iconPath("open")
                                            icon.width: 16; icon.height: 16
                                            visible: root.st === "done" && model.output !== ""
                                            Accessible.name: strings.tip_open
                                            onClicked: bridge.openCompressionOutput(model.output)
                                        }
                                        ToolButton {
                                            width: 32; height: 28
                                            display: AbstractButton.IconOnly
                                            icon.source: root.iconPath("cancel")
                                            icon.width: 16; icon.height: 16
                                            visible: root.st === "done" || root.st === "error"
                                                     || root.st === "cancelled" || root.st === "skipped"
                                            Accessible.name: strings.ctx_remove
                                            onClicked: bridge.removeCompressionItem(index)
                                        }
                                    }
                                }
                                Rectangle {
                                    anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                                    height: 1
                                    color: root.dark ? "#262e35" : "#ececec"
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10
                    Label {
                        Layout.fillWidth: true
                        text: root.compWait + " " + strings.compress_stat_waiting + " · "
                              + root.compWork + " " + strings.compress_stat_working + " · "
                              + root.compDone + " " + strings.compress_stat_done + " · "
                              + root.compErr + " " + strings.compress_stat_errors + " · "
                              + root.compSkip + " " + strings.compress_stat_skipped
                        font.pixelSize: 12
                        color: Material.secondaryTextColor
                        elide: Text.ElideRight
                    }
                    Button {
                        text: strings.btn_start; highlighted: true
                        visible: !bridge.compressionActive
                        onClicked: bridge.startCompression()
                    }
                    Button {
                        text: strings.btn_pause
                        visible: bridge.compressionActive && !bridge.compressionPaused
                        onClicked: bridge.pauseCompression()
                    }
                    Button {
                        text: strings.btn_resume
                        visible: bridge.compressionActive && bridge.compressionPaused
                        highlighted: true
                        onClicked: bridge.resumeCompression()
                    }
                    Button {
                        text: strings.btn_cancel_all
                        onClicked: bridge.cancelCompression()
                    }
                    Button {
                        text: strings.btn_clear_finished
                        onClicked: bridge.clearCompressionFinished()
                    }
                }
            }
        }

        // ======================================================== ABA CONFIGURAÇÕES
        Item {
            ScrollView {
                id: settingsScroll
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                ColumnLayout {
                    width: settingsScroll.availableWidth
                    spacing: 12

                    // -------------------------------------------- Aparência
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: appearanceCol.implicitHeight + 32
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            id: appearanceCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            Label { text: strings.cfg_appearance; font.pixelSize: 15; font.weight: Font.DemiBold }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_dark; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                Switch {
                                    checked: root.dark
                                    ToolTip.text: strings.cfg_dark_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onToggled: bridge.setDark(checked)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_language; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                ComboBox {
                                    id: langCombo
                                    model: bridge.languages
                                    textRole: "name"
                                    valueRole: "code"
                                    currentIndex: {
                                        for (var i = 0; i < model.length; i++)
                                            if (model[i].code === bridge.language)
                                                return i
                                        return 0
                                    }
                                    Layout.preferredWidth: 200
                                    onActivated: bridge.setLanguage(currentValue)
                                }
                            }
                        }
                    }

                    // -------------------------------------------- Downloads
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: downloadsCol.implicitHeight + 32
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            id: downloadsCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            Label { text: strings.cfg_downloads; font.pixelSize: 15; font.weight: Font.DemiBold }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_concurrency; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                SpinBox {
                                    id: concurrencySpin
                                    from: 1; to: 8
                                    value: bridge.concurrency
                                    editable: true
                                    ToolTip.text: strings.cfg_concurrency_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onValueChanged: if (value !== bridge.concurrency) bridge.setConcurrency(value)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.naming_label; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                ComboBox {
                                    id: namingCombo
                                    model: [
                                        { text: strings.naming_id, value: "id" },
                                        { text: strings.naming_title, value: "title" }
                                    ]
                                    textRole: "text"
                                    valueRole: "value"
                                    currentIndex: bridge.namingMode === "title" ? 1 : 0
                                    Layout.preferredWidth: 220
                                    onActivated: bridge.setNamingMode(currentValue)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Button {
                                    text: strings.cfg_outdir
                                    ToolTip.text: strings.cfg_outdir_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onClicked: bridge.chooseOutputFolder()
                                }
                                Label {
                                    id: outputFolderLabel
                                    text: bridge.outputFolder
                                    color: Material.secondaryTextColor
                                    font.pixelSize: 12
                                    elide: Text.ElideMiddle
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }

                    // -------------------------------------------- Rede
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: networkCol.implicitHeight + 32
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            id: networkCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            Label {
                                text: strings.cfg_network; font.pixelSize: 15; font.weight: Font.DemiBold
                                ToolTip.text: strings.cfg_network_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_limit_rate; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                SpinBox {
                                    id: limitRateSpin
                                    from: 0; to: 100; stepSize: 1
                                    value: bridge.limitRateMB
                                    editable: true
                                    ToolTip.text: strings.cfg_limit_rate_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onValueChanged: if (value !== bridge.limitRateMB) bridge.setLimitRateMB(value)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_fragments; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                SpinBox {
                                    id: fragmentsSpin
                                    from: 1; to: 8
                                    value: bridge.fragments
                                    editable: true
                                    ToolTip.text: strings.cfg_fragments_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onValueChanged: if (value !== bridge.fragments) bridge.setFragments(value)
                                }
                            }
                        }
                    }

                    // -------------------------------------------- Cookies
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: cookiesCol.implicitHeight + 32
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            id: cookiesCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            Label { text: strings.cfg_cookies_title; font.pixelSize: 15; font.weight: Font.DemiBold }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_cookies_use; font.pixelSize: 13; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                Switch {
                                    checked: bridge.cookiesEnabled
                                    ToolTip.text: strings.cfg_cookies_use_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onToggled: bridge.setCookiesEnabled(checked)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_browser; font.pixelSize: 13; color: Material.secondaryTextColor; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                ComboBox {
                                    id: browserCombo
                                    model: ["Chrome", "Chromium", "Edge", "Firefox", "Opera", "Vivaldi", "Brave"]
                                    currentIndex: bridge.cookiesBrowserIndex
                                    onActivated: bridge.setCookiesBrowserIndex(currentIndex)
                                    enabled: bridge.cookiesEnabled
                                    Layout.preferredWidth: 200
                                    ToolTip.text: strings.cfg_browser_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label {
                                    text: strings.cfg_cookies_file
                                    font.pixelSize: 12
                                    color: Material.secondaryTextColor
                                    Layout.preferredWidth: 220
                                    wrapMode: Text.WordWrap
                                }
                                TextField {
                                    text: bridge.cookiesFile
                                    onEditingFinished: bridge.setCookiesFile(text)
                                    placeholderText: strings.cfg_cookies_placeholder
                                    selectByMouse: true
                                    Layout.fillWidth: true
                                    ToolTip.text: strings.cfg_cookies_file_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                }
                                Button {
                                    text: strings.btn_choose
                                    enabled: bridge.cookiesEnabled
                                    ToolTip.text: strings.btn_choose_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onClicked: bridge.chooseCookiesFile()
                                }
                            }
                            Label {
                                text: strings.cfg_cookies_hint
                                font.pixelSize: 11
                                color: Material.secondaryTextColor
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }
                        }
                    }

                    // -------------------------------------------- Dependências
                    Rectangle {
                        id: depsCard
                        Layout.fillWidth: true
                        Layout.preferredHeight: depsCol.implicitHeight + 32
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1

                        ColumnLayout {
                            id: depsCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 10

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label { text: strings.cfg_deps_title; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Item { Layout.fillWidth: true }
                                Label {
                                    visible: bridge.depsBusy
                                    text: bridge.depsBusy ? strings.dep_busy : ""
                                    color: "#ef6c00"
                                    font.pixelSize: 12
                                    Layout.rightMargin: 6
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Button {
                                    text: strings.dep_update_all
                                    enabled: !bridge.depsBusy
                                    onClicked: bridge.updateDependencies()
                                }
                                Button {
                                    text: strings.dep_recheck
                                    enabled: !bridge.depsBusy
                                    onClicked: bridge.refreshDependencies()
                                }
                            }
                            Label {
                                text: strings.cfg_deps_tip
                                font.pixelSize: 11
                                color: Material.secondaryTextColor
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label {
                                    text: strings.dep_ytdlp_channel
                                    font.pixelSize: 13
                                    color: Material.secondaryTextColor
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                ComboBox {
                                    id: ytdlpVariantCombo
                                    model: [
                                        { text: strings.variant_stable, value: "stable" },
                                        { text: strings.variant_nightly, value: "nightly" },
                                        { text: strings.variant_master, value: "master" }
                                    ]
                                    textRole: "text"
                                    valueRole: "value"
                                    currentIndex: bridge.ytdlpVariant === "nightly" ? 1
                                                  : (bridge.ytdlpVariant === "master" ? 2 : 0)
                                    Layout.preferredWidth: 180
                                    enabled: !bridge.depsBusy
                                    onActivated: bridge.setYtdlpVariant(currentValue)
                                }
                                Item { Layout.fillWidth: true }
                            }

                            Repeater {
                                model: bridge.dependencies
                                delegate: RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        width: 10; height: 10; radius: 5
                                        color: modelData.found ? "#2e7d32" : "#c62828"
                                        Layout.alignment: Qt.AlignVCenter
                                    }
                                    Label {
                                        text: modelData.name
                                        font.pixelSize: 13
                                        Layout.preferredWidth: 104
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.version ? ("v" + modelData.version) : ""
                                        font.pixelSize: 11
                                        color: Material.secondaryTextColor
                                        Layout.preferredWidth: 96
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.strategy === "bundled"
                                              ? (modelData.found ? strings.dep_bundled : strings.dep_missing)
                                              : ((modelData.required ? strings.dep_required : strings.dep_optional)
                                                 + " · " + (modelData.found ? strings.dep_found : strings.dep_missing))
                                        font.pixelSize: 11
                                        color: modelData.found ? Material.secondaryTextColor : "#c62828"
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    Button {
                                        visible: modelData.installable
                                        enabled: !bridge.depsBusy
                                        text: modelData.found ? strings.dep_update : strings.dep_install
                                        onClicked: bridge.installDependency(modelData.key)
                                    }
                                }
                            }

                            Label {
                                text: strings.dep_console
                                font.pixelSize: 11
                                font.bold: true
                                color: Material.secondaryTextColor
                                visible: root.depsLog.length > 0
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 120
                                visible: root.depsLog.length > 0
                                clip: true
                                TextArea {
                                    id: depsConsole
                                    readOnly: true
                                    text: root.depsLog
                                    font.family: "monospace"
                                    font.pixelSize: 11
                                    wrapMode: TextEdit.NoWrap
                                }
                            }
                        }
                    }

                    // -------------------------------------------- Sobre/atualizações
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: aboutCol.implicitHeight + 32
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            id: aboutCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 10
                            Label { text: strings.about_title; font.pixelSize: 15; font.weight: Font.DemiBold }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 10
                                Label {
                                    Layout.fillWidth: true
                                    text: strings.update_current + " " + bridge.appVersion
                                    font.pixelSize: 13
                                    color: Material.secondaryTextColor
                                }
                                Button {
                                    text: strings.update_check
                                    enabled: !bridge.updateBusy
                                    onClicked: bridge.checkForUpdates()
                                }
                                Button {
                                    text: strings.update_download
                                    visible: bridge.updateAvailable
                                    enabled: !bridge.updateBusy
                                    highlighted: true
                                    onClicked: bridge.downloadUpdate()
                                }
                                Button {
                                    text: strings.update_open_page
                                    visible: bridge.updateHtmlUrl !== ""
                                    onClicked: bridge.openReleasePage()
                                }
                            }
                            Label {
                                Layout.fillWidth: true
                                text: bridge.updateStatus
                                visible: bridge.updateStatus !== ""
                                wrapMode: Text.Wrap
                                font.pixelSize: 12
                            }
                            ProgressBar {
                                Layout.fillWidth: true
                                from: 0
                                to: 100
                                value: bridge.updateProgress
                                visible: bridge.updateBusy && bridge.updateProgress > 0
                            }
                            Label {
                                text: strings.update_notes
                                font.pixelSize: 11
                                font.bold: true
                                color: Material.secondaryTextColor
                                visible: bridge.updateNotes !== ""
                            }
                            ScrollView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 110
                                visible: bridge.updateNotes !== ""
                                clip: true
                                TextArea {
                                    readOnly: true
                                    text: bridge.updateNotes
                                    font.pixelSize: 11
                                    wrapMode: TextEdit.Wrap
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ===================================================== ZONAS DE REDIMENSIONAR
    Item {
        anchors.fill: parent
        z: 80
        MouseArea { anchors.left: parent.left; anchors.top: parent.top; width: 8; height: 8; cursorShape: Qt.SizeFDiagCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.TopEdge | Qt.LeftEdge) }
        MouseArea { anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; width: 60; height: 8; cursorShape: Qt.SizeVerCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.TopEdge) }
        MouseArea { anchors.right: parent.right; anchors.top: parent.top; width: 8; height: 8; cursorShape: Qt.SizeBDiagCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.TopEdge | Qt.RightEdge) }
        MouseArea { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; width: 8; height: 60; cursorShape: Qt.SizeHorCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.LeftEdge) }
        MouseArea { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; width: 8; height: 60; cursorShape: Qt.SizeHorCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.RightEdge) }
        MouseArea { anchors.left: parent.left; anchors.bottom: parent.bottom; width: 8; height: 8; cursorShape: Qt.SizeBDiagCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.BottomEdge | Qt.LeftEdge) }
        MouseArea { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; width: 60; height: 8; cursorShape: Qt.SizeVerCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.BottomEdge) }
        MouseArea { anchors.right: parent.right; anchors.bottom: parent.bottom; width: 8; height: 8; cursorShape: Qt.SizeFDiagCursor; onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.BottomEdge | Qt.RightEdge) }
    }

    // -------------------------------------------------------------------- Toast
    Rectangle {
        id: toast
        visible: false
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        width: Math.min(root.width - 40, toastText.implicitWidth + 36)
        height: 42
        radius: 21
        color: root.dark ? "#2b3138" : "#32363c"
        z: 100
        Label {
            id: toastText
            anchors.centerIn: parent
            color: "white"
            font.pixelSize: 13
            elide: Text.ElideRight
            width: parent.width - 24
            horizontalAlignment: Text.AlignHCenter
        }
        Timer { id: toastTimer; interval: 2600; onTriggered: toast.visible = false }
    }

    // ------------------------------------------------------------ Delegate
    Component {
        id: downloadDelegate
        Item {
            id: rowItem
            width: listView.width
            height: 64
            property bool editing: false
            property string st: model.status
            property bool active: root.isActive(st)
            property bool final: root.isFinal(st)
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
                        color: root.dark ? "#262e35" : "#eef0f3"
                        border.color: root.dark ? "#2a323a" : "#dddddd"
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
                            source: root.iconPath("play")
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
                            onEditingFinished: if (rowItem.editing) { bridge.editUrl(index, text); rowItem.editing = false }
                            Keys.onEscapePressed: rowItem.editing = false
                        }

                        Label {
                            Layout.fillWidth: true
                            visible: !rowItem.editing
                            text: model.url
                            elide: Text.ElideMiddle
                            font.pixelSize: 11
                            color: Material.secondaryTextColor
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
                        color: root.badgeColor(rowItem.st)
                        Label {
                            anchors.centerIn: parent
                            text: root.statusText(rowItem.st)
                            font.pixelSize: 11
                            font.bold: true
                            color: "white"
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
                        color: root.dark ? "#ff8a80" : "#c62828"
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: { root.errorText = model.error; errorDialog.open() }
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
                        color: Material.secondaryTextColor
                    }
                }

                Column {
                    Layout.preferredWidth: 130
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2
                    Label { width: parent.width; text: model.speed; font.pixelSize: 11; elide: Text.ElideRight }
                    Label { width: parent.width; text: model.size; font.pixelSize: 11; color: Material.secondaryTextColor; elide: Text.ElideRight }
                }

                Item {
                    Layout.preferredWidth: 136
                    Layout.alignment: Qt.AlignVCenter
                    Row {
                        anchors.centerIn: parent
                        spacing: 3
                        ToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: root.iconPath("edit")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.canEdit
                            Accessible.name: strings.tip_edit
                            ToolTip.text: strings.tip_edit; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: rowItem.editing = true
                        }
                        ToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: root.iconPath("copy")
                            icon.width: 16; icon.height: 16
                            Accessible.name: strings.tip_copy
                            ToolTip.text: strings.tip_copy; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.copyLink(model.url)
                        }
                        ToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: root.iconPath("retry")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.final
                            Accessible.name: strings.tip_retry
                            ToolTip.text: strings.tip_retry; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.retryItem(index)
                        }
                        ToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: root.iconPath("cancel")
                            icon.width: 16; icon.height: 16
                            visible: rowItem.active || rowItem.st === "waiting"
                            Accessible.name: strings.tip_cancel
                            ToolTip.text: strings.tip_cancel; ToolTip.visible: hovered; ToolTip.delay: 500
                            onClicked: bridge.cancelItem(index)
                        }
                        ToolButton {
                            width: 32; height: 28
                            display: AbstractButton.IconOnly
                            icon.source: root.iconPath("open")
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
                color: root.dark ? "#262e35" : "#ececec"
            }
        }
    }

    // --------------------------------------------------------- erro detalhado
    Dialog {
        id: errorDialog
        parent: root
        modal: true
        title: strings.dlg_error
        standardButtons: Dialog.NoButton
        width: 540
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        contentItem: ColumnLayout {
            Label {
                Layout.fillWidth: true
                text: root.errorText
                wrapMode: Text.Wrap
                font.pixelSize: 12
                color: root.dark ? "#ff8a80" : "#c62828"
            }
            Button {
                text: strings.dlg_error_copy
                onClicked: { bridge.copyLink(root.errorText); errorDialog.close() }
            }
        }
        footer: DialogButtonBox {
            Button {
                text: strings.dlg_error_close
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: errorDialog.close()
            }
        }
    }

    // ------------------------------------------------------- confirmações
    Dialog {
        id: confirmCancel
        parent: root
        modal: true
        title: strings.confirm_cancel_title
        standardButtons: Dialog.NoButton
        width: 420
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        contentItem: Label {
            width: confirmCancel.availableWidth
            text: strings.confirm_cancel_text
            wrapMode: Text.Wrap
        }
        footer: DialogButtonBox {
            Button {
                text: strings.confirm_ok
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                onClicked: { bridge.cancelAll(); confirmCancel.close() }
            }
            Button {
                text: strings.confirm_cancel
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: confirmCancel.close()
            }
        }
    }

    Dialog {
        id: confirmClear
        parent: root
        modal: true
        title: strings.confirm_clear_title
        standardButtons: Dialog.NoButton
        width: 420
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        contentItem: Label {
            width: confirmClear.availableWidth
            text: strings.confirm_clear_text
            wrapMode: Text.Wrap
        }
        footer: DialogButtonBox {
            Button {
                text: strings.confirm_ok
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                onClicked: { bridge.clearFinished(); confirmClear.close() }
            }
            Button {
                text: strings.confirm_cancel
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: confirmClear.close()
            }
        }
    }

    // ------------------------------------------- opções avançadas do lote
    Dialog {
        id: batchOptionsDialog
        parent: root
        modal: true
        title: strings.batch_options
        width: 520
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                visible: bridge.formatMode !== "audio_only"
                Label { text: strings.quality_label; Layout.fillWidth: true; font.pixelSize: 13 }
                QualityCombo { Layout.alignment: Qt.AlignVCenter }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                Label { text: strings.container_label; Layout.fillWidth: true; font.pixelSize: 13 }
                ContainerCombo { Layout.alignment: Qt.AlignVCenter }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                visible: bridge.formatMode !== "audio_only"
                Label { text: strings.codec_label; Layout.fillWidth: true; font.pixelSize: 13 }
                CodecCombo { Layout.alignment: Qt.AlignVCenter }
            }
            RowLayout {
                Layout.fillWidth: true
                spacing: 12
                visible: bridge.formatMode !== "audio_only" && bridge.codec !== "copy"
                Label { text: strings.compress_label; Layout.fillWidth: true; font.pixelSize: 13 }
                CompressCombo { Layout.alignment: Qt.AlignVCenter }
            }
        }
        footer: DialogButtonBox {
            Button {
                text: strings.dlg_error_close
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: batchOptionsDialog.close()
            }
        }
    }

    // ----------------------------------------------------- diálogo de dependências
    Dialog {
        id: depsDialog
        parent: root
        modal: true
        title: strings.dlg_deps_title
        width: 560
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        standardButtons: Dialog.NoButton
        contentItem: ColumnLayout {
            spacing: 10
            Label {
                Layout.fillWidth: true
                text: strings.dlg_deps_body
                wrapMode: Text.Wrap
            }
            Label {
                Layout.fillWidth: true
                text: {
                    var parts = []
                    for (var i = 0; i < bridge.dependencies.length; i++) {
                        var d = bridge.dependencies[i]
                        if (d.required && !d.found)
                            parts.push("• " + d.name)
                    }
                    return parts.join("\n")
                }
                color: root.dark ? "#ff8a80" : "#c62828"
                font.pixelSize: 12
            }
            Label {
                Layout.fillWidth: true
                text: strings.dep_console
                font.bold: true
                visible: root.depsLog.length > 0
            }
            ScrollView {
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                visible: root.depsLog.length > 0
                clip: true
                TextArea {
                    readOnly: true
                    text: root.depsLog
                    font.family: "monospace"
                    font.pixelSize: 11
                    wrapMode: TextEdit.NoWrap
                }
            }
        }
        footer: DialogButtonBox {
            Button {
                text: strings.dlg_deps_install
                DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole
                onClicked: {
                    bridge.dismissDepsPrompt()
                    bridge.installMissingDependencies()
                    depsDialog.close()
                    tabBar.currentIndex = 4
                }
            }
            Button {
                text: strings.dlg_deps_later
                DialogButtonBox.buttonRole: DialogButtonBox.RejectRole
                onClicked: {
                    bridge.dismissDepsPrompt()
                    depsDialog.close()
                }
            }
        }
    }
}
