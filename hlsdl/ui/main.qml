import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQml.Models
import "i18n.js" as I18n
import "motion.js" as Motion
import "dialogs"
import "pages"
import "components"

// =============================================================================
// HLS Downloader Pro — Interface Qt Quick (Material Design)
//
//   - Abas: Individual | Downloads | Compressão | Configurações.
//     Playlist é carregada pelo diálogo da aba Downloads e entra na mesma fila.
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

    // Tokens semânticos de tema. Todo texto/plano de fundo deve usar estes
    // valores (evita combinações claro-sobre-claro/escuro-sobre-escuro).
    component ThemeTokens: QtObject {
        property bool dark: false
        readonly property color windowBg: dark ? "#14181c" : "#f5f5f5"
        readonly property color cardBg: dark ? "#1d2329" : "#ffffff"
        readonly property color cardBorder: dark ? "#33404a" : "#d7dde3"
        readonly property color titleBg: dark ? "#101419" : "#e9ebee"
        readonly property color tabBg: dark ? "#181d22" : "#eef0f3"
        readonly property color text: dark ? "#f2f4f6" : "#202428"
        readonly property color textSecondary: dark ? "#c2cbd3" : "#4f5862"
        readonly property color textMuted: dark ? "#9aa5af" : "#626b75"
        readonly property color divider: dark ? "#33404a" : "#d7dde3"
        readonly property color hover: dark ? "#2a323a" : "#dfe4e8"
        readonly property color rowHighlight: dark ? "#223038" : "#dceef7"
        readonly property color tableHeaderBg: dark ? "#232b33" : "#eef1f4"
        readonly property color tableHeaderText: dark ? "#e3e8ec" : "#2f3a42"
        readonly property color thumbnailBg: dark ? "#262e35" : "#eef0f3"
        readonly property color thumbnailBorder: dark ? "#33404a" : "#d7dde3"
        readonly property color accentText: dark ? "#90caf9" : "#0d47a1"
        readonly property color accentFill: "#1565c0"
        readonly property color onAccent: "#ffffff"
        readonly property color dangerFill: "#b71c1c"
        readonly property color successText: dark ? "#81c784" : "#1b5e20"
        readonly property color busyText: dark ? "#ffb74d" : "#9a4a00"
        readonly property color errorText: dark ? "#ff8a80" : "#b71c1c"
        readonly property color warningBg: "#4a2c1f"
        readonly property color warningText: dark ? "#ffd180" : "#ffd180"
        readonly property color terminalBg: "#0d1117"
        readonly property color terminalBorder: "#30363d"
        readonly property color terminalText: "#d6dde5"
        readonly property color terminalMuted: "#9aa5af"
        readonly property color terminalPrompt: "#27c93f"
        readonly property color terminalSelection: "#264f78"
        readonly property color toastBg: dark ? "#2b3138" : "#32363c"
        readonly property color heroFrom: dark ? "#1b2c3a" : "#eaf4ff"
        readonly property color heroTo: dark ? "#1d2329" : "#ffffff"
        readonly property color heroBorder: dark ? "#2d4557" : "#cfe0f2"
        readonly property color badgeDone: "#2e7d32"
        readonly property color badgeError: "#b71c1c"
        readonly property color badgeDownloading: "#00695c"
        readonly property color badgeAnalyzing: "#8a4b08"
        readonly property color badgeEncoding: "#4a148c"
        readonly property color badgeMuted: "#455a64"
    }
    property QtObject theme: ThemeTokens { dark: root.dark }


    property var strings: ({})
    readonly property var bridgeApi: bridge
    property alias singleUrl: singlePage.singleUrl
    property alias inputArea: batchPage.inputArea
    property alias listView: batchPage.listView
    property alias queueFilter: batchPage.queueFilter
    property alias playlistModelRef: playlistModel
    property alias settingsScroll: settingsPage.settingsScroll
    property string errorText: ""
    property string depsLog: ""
    property string queueFilterText: ""
    property int playlistSelCount: 0
    property string playlistFilterText: ""
    property int playlistVisibleCount: 0
    property bool depsPromptShown: false
    property string pendingDepKey: ""
    property string pendingDepName: ""
    property string pendingDepAction: ""
    property bool pendingDepUpdate: false
    property int normalX: 0
    property int normalY: 0
    property int normalW: 0
    property int normalH: 0
    property bool allowClose: false
    property bool wasMinimized: false
    property bool minimizeAnimating: false

    function minimizeAnimated() {
        if (root.visibility === Window.Minimized || root.minimizeAnimating)
            return
        if (root.contentItem === null) {
            root.showMinimized()
            return
        }
        root.minimizeAnimating = true
        minimizeAnimation.start()
    }

    function rememberNormalGeometry() {
        if (root.visibility !== Window.Maximized) {
            root.normalX = root.x
            root.normalY = root.y
            root.normalW = root.width
            root.normalH = root.height
        }
    }
    onXChanged: rememberNormalGeometry()
    onYChanged: rememberNormalGeometry()
    onWidthChanged: rememberNormalGeometry()
    onHeightChanged: rememberNormalGeometry()
    function toggleMaximize() {
        if (root.visibility === Window.Maximized) {
            root.showNormal()
        } else {
            rememberNormalGeometry()
            root.showMaximized()
        }
    }
    function saveWindowGeometry() {
        bridge.saveGeometry(
            root.visibility === Window.Maximized && root.normalW > 0 ? root.normalX : root.x,
            root.visibility === Window.Maximized && root.normalH > 0 ? root.normalY : root.y,
            root.visibility === Window.Maximized && root.normalW > 0 ? root.normalW : root.width,
            root.visibility === Window.Maximized && root.normalH > 0 ? root.normalH : root.height,
            root.visibility === Window.Maximized
        )
    }

    function askInstallDependency(key, name, update) {
        root.pendingDepAction = "one"
        root.pendingDepKey = key
        root.pendingDepName = name
        root.pendingDepUpdate = update
        confirmDeps.open()
    }
    function askUpdateAllDependencies() {
        root.pendingDepAction = "all"
        root.pendingDepKey = ""
        root.pendingDepName = ""
        root.pendingDepUpdate = true
        confirmDeps.open()
    }

    function retranslate() {
        I18n.setLang(bridge.language)
        strings = I18n.getAll()
    }
    function statusText(s) { return strings["s_" + s] || s }
    function badgeColor(s) {
        switch (s) {
        case "done":        return root.theme.badgeDone
        case "error":       return root.theme.badgeError
        case "downloading": return root.theme.badgeDownloading
        case "analyzing":   return root.theme.badgeAnalyzing
        case "encoding":    return root.theme.badgeEncoding
        case "verifying":   return root.theme.badgeAnalyzing
        case "cancelled":   return root.theme.badgeMuted
        case "skipped":     return root.theme.badgeMuted
        default:            return root.theme.badgeMuted
        }
    }
    function isActive(s) {
        return s === "analyzing" || s === "downloading" || s === "encoding"
            || s === "verifying"
    }
    function isFinal(s) { return s === "done" || s === "error" || s === "cancelled" }

    function maybeShowDepsPrompt() {
        if (root.depsPromptShown)
            return
        if (bridge.dependencies.length === 0)
            return
        root.depsPromptShown = true
        if (bridge.anyEssentialMissing && !bridge.depsPromptDismissed)
            depsDialog.open()
    }

    function maybeShowRecovery() {
        if (bridge.recoveryMessages.length > 0)
            recoveryDialog.open()
    }

    function showError(text) {
        root.errorText = text
        errorDialog.open()
    }

    function openCompressionSuggestions() {
        compressSuggestions.open()
    }

    function openSimilarityDialog() {
        similarDialog.open()
        bridge.scanSimilarQueue()
    }

    function openBatchOptions() { batchOptionsDialog.open() }
    function openPlaylistImport() { playlistImportDialog.open() }
    function clearPlaylist() {
        playlistModel.clear()
        root.playlistSelCount = 0
        root.playlistVisibleCount = 0
        bridge.clearPlaylist()
    }
    function goToSettingsTab() { tabBar.currentIndex = 3 }
    function openConfirmCancel() { confirmCancel.open() }
    function openConfirmClear() { confirmClear.open() }
    function openConfirmUpdate() { confirmUpdate.open() }

    function startSingle() {
        var value = singleUrl.text.trim()
        if (value.length === 0)
            return
        // Só limpa quando o link foi realmente aceito; em erro/duplicado o
        // usuário mantém o texto para corrigir ou copiar.
        if (bridge.downloadSingle(value))
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
                // Playlist carregada já vem marcada; o usuário pode
                // desmarcar exceções em vez de selecionar tudo manualmente.
                selected: true
            })
        }
        root.refreshSelCount()
        root.refreshPlaylistVisibleCount()
    }
    function playlistMatches(it) {
        var f = root.playlistFilterText
        if (f.length === 0)
            return true
        return String(it.title).toLowerCase().indexOf(f) !== -1
            || String(it.url).toLowerCase().indexOf(f) !== -1
    }
    function refreshPlaylistVisibleCount() {
        var n = 0
        for (var i = 0; i < playlistModel.count; i++)
            if (root.playlistMatches(playlistModel.get(i)))
                n++
        root.playlistVisibleCount = n
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
    function loadPlaylist(url, limit) {
        var u = String(url || "").trim()
        if (u.length === 0)
            return
        var parsedLimit = Number(limit)
        if (!isFinite(parsedLimit) || parsedLimit < 0)
            parsedLimit = 0
        playlistModel.clear()
        root.playlistSelCount = 0
        root.playlistVisibleCount = 0
        bridge.loadPlaylist(u, Math.floor(parsedLimit))
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

    // Caminho do ícone SVG conforme o tema. Resolvido a partir do main.qml
    // para que páginas/componentes em subpastas não procurem "pages/icons".
    function iconPath(name) {
        return Qt.resolvedUrl("icons/" + name + (root.dark ? "_dark.svg" : "_light.svg"))
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

    function formatBitrate(value) {
        var n = Number(value) || 0
        if (n <= 0)
            return "—"
        if (n >= 1000000)
            return (n / 1000000).toFixed(1) + " Mb/s"
        if (n >= 1000)
            return Math.round(n / 1000) + " kb/s"
        return Math.round(n) + " b/s"
    }

    function isVideoPath(path) {
        var p = String(path).toLowerCase()
        return p.endsWith(".mp4") || p.endsWith(".mkv") || p.endsWith(".mov")
            || p.endsWith(".avi") || p.endsWith(".webm") || p.endsWith(".m4v")
            || p.endsWith(".ts")
    }

    function estimateSaving(codec) {
        var base = codec === "av1" ? 58 : (codec === "hevc" ? 48 : 26)
        return Math.max(5, Math.min(85,
            Math.round(base + (bridge.compressionQuality - 24) * 1.1)))
    }

    // Resumo compacto do perfil de download (aba Downloads).
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

    ListModel { id: playlistModel }

    Connections {
        target: bridge
        function onLanguageChanged() { retranslate() }
        function onDepsChanged() { root.maybeShowDepsPrompt() }
        function onRecoveryChanged() { root.maybeShowRecovery() }
    }
    Component.onCompleted: {
        retranslate()
        bridge.refreshStats()
        root.maybeShowDepsPrompt()
        root.maybeShowRecovery()
    }

    Material.theme: root.dark ? Material.Dark : Material.Light
    Material.accent: root.theme.accentText
    Material.primary: root.theme.accentFill
    Material.foreground: root.theme.text
    // Não usar Material.background aqui: ele também pinta o fundo de botões
    // highlighted, deixando texto branco sobre cinza claro no tema claro.
    background: Rectangle { color: root.theme.windowBg }

    property int statWaiting: 0
    property int statDownloading: 0
    property int statDone: 0
    property int statError: 0
    property int statCancelled: 0
    property int statTotal: 0
    property int compWait: 0
    property int compWork: 0
    property int compDone: 0
    property int compErr: 0
    property int compSkip: 0

    onClosing: function(close) {
        if (!root.allowClose && (bridge.queueActive || bridge.compressionActive)) {
            close.accepted = false
            confirmClose.open()
            return
        }
        minimizeAnimation.stop()
        restoreAnimation.stop()
        if (root.contentItem !== null) {
            root.contentItem.opacity = 1
            root.contentItem.scale = 1
        }
        root.saveWindowGeometry()
    }

    onVisibilityChanged: {
        if (root.visibility === Window.Maximized && root.screen) {
            var geo = root.screen.availableGeometry
            if (geo)
                root.setGeometry(geo.x, geo.y, geo.width, geo.height)
        }
        if (root.visibility === Window.Minimized) {
            root.wasMinimized = true
            return
        }
        if (root.wasMinimized) {
            root.wasMinimized = false
            if (root.contentItem !== null) {
                root.contentItem.opacity = 0
                root.contentItem.scale = 0.985
                restoreAnimation.start()
            }
        }
    }

    // ====================================================== Atalhos
    readonly property bool typing: {
        // Window.activeFocusItem retorna null no Qt 6.12; a propriedade
        // correta é root.activeFocusItem. Não use `item.text !== undefined`:
        // Button também tem `text` e isso desabilitava Ctrl+V/Delete depois
        // de qualquer clique em botão.
        var item = root.activeFocusItem
        return item !== null && (item instanceof TextInput || item instanceof TextEdit
                                 || item instanceof SpinBox)
    }
    SequentialAnimation {
        id: minimizeAnimation
        NumberAnimation {
            target: root.contentItem
            property: "opacity"
            to: 0
            duration: Motion.minimize
            easing.type: Easing.InCubic
        }
        NumberAnimation {
            target: root.contentItem
            property: "scale"
            to: 0.985
            duration: Motion.minimize
            easing.type: Easing.InCubic
        }
        ScriptAction { script: root.showMinimized() }
        onFinished: root.minimizeAnimating = false
    }

    ParallelAnimation {
        id: restoreAnimation
        NumberAnimation {
            target: root.contentItem
            property: "opacity"
            to: 1
            duration: Motion.restore
            easing.type: Easing.OutCubic
        }
        NumberAnimation {
            target: root.contentItem
            property: "scale"
            to: 1
            duration: Motion.restore
            easing.type: Easing.OutCubic
        }
    }

    Shortcut { sequence: "Ctrl+V"; enabled: !root.typing; onActivated: bridge.pasteFromClipboard() }
    Shortcut {
        sequence: "Ctrl+Return"
        enabled: !root.typing && tabBar.currentIndex === 1
        onActivated: {
            if (bridge.addLinks(inputArea.text) > 0)
                inputArea.clear()
        }
    }
    Shortcut {
        sequence: "Ctrl+Enter"
        enabled: !root.typing && tabBar.currentIndex === 1
        onActivated: {
            if (bridge.addLinks(inputArea.text) > 0)
                inputArea.clear()
        }
    }
    Shortcut {
        sequence: "Ctrl+F"
        enabled: true
        onActivated: {
            if (tabBar.currentIndex === 1)
                batchPage.filterField.forceActiveFocus()
            else if (tabBar.currentIndex === 2)
                compressionPage.filterField.forceActiveFocus()
        }
    }
    Shortcut { sequence: "F5"; onActivated: bridge.startQueue() }
    Shortcut {
        sequence: "Delete"
        enabled: !root.typing && tabBar.currentIndex === 1 && root.queueFilterText.length === 0
        onActivated: {
            if (listView.currentIndex >= 0) {
                var source = batchPage.batchSourceIndex(listView.currentIndex)
                if (source >= 0)
                    bridge.removeItem(source)
            }
        }
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
                tabBar.currentIndex = 2
            }
            drop.accept()
        }
    }

    Connections {
        target: bridge
        function onStatsChanged(waiting, downloading, done, errors, cancelled) {
            root.statWaiting = waiting
            root.statDownloading = downloading
            root.statDone = done
            root.statError = errors
            root.statCancelled = cancelled
            root.statTotal = waiting + downloading + done + errors + cancelled
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
        color: root.theme.titleBg
        gradient: Gradient {
            GradientStop { position: 0.0; color: root.theme.titleBg }
            GradientStop {
                position: 1.0
                color: root.theme.dark ? Qt.lighter(root.theme.titleBg, 1.06)
                                       : Qt.darker(root.theme.titleBg, 1.02)
            }
        }
        z: 60

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 1
            color: root.theme.divider
        }

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
                root.toggleMaximize()
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 6
            spacing: 8

            Rectangle {
                width: 7
                height: 28
                radius: 3.5
                color: root.theme.accentFill
                Layout.alignment: Qt.AlignVCenter
            }
            Label {
                text: "HLS Downloader Pro"
                font.pixelSize: 14
                font.weight: Font.DemiBold
                color: root.theme.text
                Layout.alignment: Qt.AlignVCenter
            }
            Label {
                text: strings.titlebar_sub
                font.pixelSize: 11
                color: root.theme.textMuted
                Layout.alignment: Qt.AlignVCenter
                Layout.topMargin: 1
                elide: Text.ElideRight
                Layout.maximumWidth: 260
            }
            Rectangle {
                Layout.alignment: Qt.AlignVCenter
                implicitWidth: versionLabel.implicitWidth + 14
                implicitHeight: 20
                radius: 10
                color: root.theme.dark ? "#202b34" : "#dde5ee"
                border.width: 1
                border.color: root.theme.dark ? "#334553" : "#c9d4df"
                Label {
                    id: versionLabel
                    anchors.centerIn: parent
                    text: "v" + bridge.appVersion
                    font.pixelSize: 10
                    color: root.theme.textMuted
                }
            }
            Item { Layout.fillWidth: true }
            Rectangle {
                width: 1
                height: 18
                color: root.theme.divider
                Layout.alignment: Qt.AlignVCenter
                Layout.rightMargin: 2
            }

            TitleBarButton {
                theme: root.theme
                kind: "minimize"
                tip: strings.win_minimize
                onClicked: root.minimizeAnimated()
            }
            TitleBarButton {
                id: maxBtn
                theme: root.theme
                kind: root.visibility === Window.Maximized ? "restore" : "maximize"
                tip: root.visibility === Window.Maximized
                     ? strings.win_restore
                     : strings.win_maximize
                onClicked: root.toggleMaximize()
            }
            TitleBarButton {
                theme: root.theme
                kind: "close"
                danger: true
                tip: strings.win_close
                onClicked: root.close()
            }
        }
    }

    // ================================================== ABAS
    TabBar {
        id: tabBar
        objectName: "mainTabBar"
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        contentHeight: 42
        background: Rectangle { color: root.theme.tabBg }
        AppTabButton {
            text: strings.tab_single; font.pixelSize: 13; implicitWidth: 170
            tipTitle: strings.tab_single
            tipText: strings.tab_single_tip
        }
        AppTabButton {
            text: strings.tab_downloads; font.pixelSize: 13; implicitWidth: 150
            tipTitle: strings.tab_downloads
            tipText: strings.tab_downloads_tip
        }
        AppTabButton {
            text: strings.tab_compress; font.pixelSize: 13; implicitWidth: 140
            tipTitle: strings.tab_compress
            tipText: strings.tab_compress_tip
        }
        AppTabButton {
            text: strings.tab_settings; font.pixelSize: 13; implicitWidth: 150
            tipTitle: strings.tab_settings
            tipText: strings.tab_settings_tip
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
        SinglePage {
            id: singlePage
            appRoot: root
            strings: root.strings
        }

        // ====================================================== ABA DOWNLOADS
        BatchPage {
            id: batchPage
            appRoot: root
            strings: root.strings
        }

        // ===================================================== ABA COMPRESSÃO
        CompressionPage {
            id: compressionPage
            appRoot: root
            strings: root.strings
        }

        SettingsPage {
            id: settingsPage
            appRoot: root
            strings: root.strings
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
        objectName: "toast"
        visible: false
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        width: Math.min(root.width - 40, Math.min(620, toastMetrics.width + 36))
        height: Math.max(42, toastText.implicitHeight + 20)
        radius: 12
        color: root.theme.toastBg
        z: 100
        Accessible.role: Accessible.StaticText
        Accessible.name: toastText.text
        TextMetrics {
            id: toastMetrics
            font: toastText.font
            text: toastText.text
        }
        Label {
            id: toastText
            anchors.centerIn: parent
            color: root.theme.onAccent
            font.pixelSize: 13
            wrapMode: Text.Wrap
            maximumLineCount: 3
            elide: Text.ElideRight
            width: parent.width - 24
            horizontalAlignment: Text.AlignHCenter
        }
        MouseArea {
            anchors.fill: parent
            onClicked: toast.visible = false
        }
        Timer {
            id: toastTimer
            // Mensagens longas/críticas ficam mais tempo; curtas continuam
            // efêmeras. O usuário também pode fechar clicando.
            interval: Math.max(2600, Math.min(8000, 1800 + toastText.text.length * 45))
            onTriggered: toast.visible = false
        }
    }

    // --------------------------------------------------------- di?logos
    CompressSuggestionsDialog {
        id: compressSuggestions
        appRoot: root
        strings: root.strings
    }

    ErrorDialog {
        id: errorDialog
        objectName: "errorDialog"
        appRoot: root
        strings: root.strings
        message: root.errorText
    }

    ConfirmDialog {
        id: confirmCancel
        appRoot: root
        strings: root.strings
        title: root.strings.confirm_cancel_title
        message: root.strings.confirm_cancel_text
        onConfirmed: bridge.cancelAll()
    }

    ConfirmDialog {
        id: confirmClear
        appRoot: root
        strings: root.strings
        title: root.strings.confirm_clear_title
        message: root.strings.confirm_clear_text
        onConfirmed: bridge.clearFinished()
    }

    BatchOptionsDialog {
        id: batchOptionsDialog
        appRoot: root
        strings: root.strings
    }

    PlaylistImportDialog {
        id: playlistImportDialog
        objectName: "playlistImportDialog"
        appRoot: root
        strings: root.strings
    }

    DepsDialog {
        id: depsDialog
        appRoot: root
        strings: root.strings
        logText: root.depsLog
    }

    ConfirmDepsDialog {
        id: confirmDeps
        appRoot: root
        strings: root.strings
        pendingAction: root.pendingDepAction
        pendingKey: root.pendingDepKey
        pendingName: root.pendingDepName
        pendingUpdate: root.pendingDepUpdate
    }

    ConfirmDialog {
        id: confirmClose
        appRoot: root
        strings: root.strings
        width: 460
        title: root.strings.confirm_close_title
        message: root.strings.confirm_close_text
        okText: root.strings.dlg_error_close
        onConfirmed: {
            root.allowClose = true
            root.close()
        }
    }

    ConfirmDialog {
        id: confirmUpdate
        appRoot: root
        strings: root.strings
        width: 480
        title: root.strings.update_title
        message: root.strings.confirm_close_text
        onConfirmed: bridge.downloadUpdate()
    }

    QualityConfirmDialog {
        id: qualityConfirm
        appRoot: root
        strings: root.strings
        bridge: root.bridgeApi
    }

    SimilarityDialog {
        id: similarDialog
        appRoot: root
        strings: root.strings
        bridge: root.bridgeApi
    }

    RecoveryDialog {
        id: recoveryDialog
        appRoot: root
        strings: root.strings
        bridge: root.bridgeApi
    }
}
