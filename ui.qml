import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "i18n.js" as I18n

// =============================================================================
// HLS Downloader Pro — Interface Qt Quick com Material Design
//
//   - Barra de título EXCLUSIVA (janela sem borda nativa: arrastar,
//     duplo-clique p/ maximizar, botões minimizar/maximizar/fechar próprios).
//   - Abas: Downloads | Configurações (configurações persistidas em
//     settings.ini via ponte com o Python).
// =============================================================================

ApplicationWindow {
    id: root
    // IMPORTANTE: definir `flags` no QML SUBSTITUI o conjunto inteiro.
    // Sem Qt.Window a janela não aparece no Alt+Tab / barra de tarefas.
    flags: Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinimizeButtonHint
           | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
           | Qt.WindowSystemMenuHint
    width: 1120
    height: 740
    minimumWidth: 940
    minimumHeight: 620
    visible: false // exibido pelo Python depois de restaurar a geometria
    title: "HLS Downloader Pro"

    // Tema (persistido) vem da ponte
    property bool dark: bridge.dark

    // Traduções (PT/EN): T é reatribuído quando o idioma muda, reavaliando
    // todos os bindings `strings.chave`.
    property var strings: ({})
    // Erro selecionado para exibição no diálogo de detalhes
    property string errorText: ""
    function retranslate() {
        I18n.setLang(bridge.language)
        strings = I18n.getAll()
    }
    Connections {
        target: bridge
        function onLanguageChanged() { retranslate() }
    }
    Component.onCompleted: retranslate()

    Material.theme: root.dark ? Material.Dark : Material.Light
    Material.accent: "#00bfa5"
    Material.background: root.dark ? "#14181c" : "#f5f5f5"

    // Estatísticas recebidas do backend via sinal `statsChanged`
    property int statWaiting: 0
    property int statDownloading: 0
    property int statDone: 0
    property int statError: 0
    property int statTotal: 0

    onClosing: bridge.saveGeometry(
        root.x, root.y, root.width, root.height,
        root.visibility === Window.Maximized
    )

    // Maximizado: ajusta para não cobrir a barra de tarefas
    onVisibilityChanged: {
        if (root.visibility === Window.Maximized && root.screen)
            root.setGeometry(root.screen.availableGeometry)
    }

    // ------------------------------------------------------ ponte com o Python
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
        function onOutputFolderChanged(path) {
            outputFolderLabel.text = path
        }
    }

    // ========================================================= BARRA DE TÍTULO
    Rectangle {
        id: titleBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 44
        color: root.dark ? "#101419" : "#e9ebee"
        z: 60

        // Arrastar a janela + duplo clique para maximizar/restaurar.
        // Debounce de 220ms: chama startSystemMove() só quando for clique
        // único — chamar showMaximized() durante uma sessão de mover (o
        // segundo clique do duplo-clique) crasha em algumas versões do Qt.
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
                    return // mover já começou; não maximizar durante a sessão
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

            Rectangle {
                width: 10
                height: 30
                radius: 5
                color: Material.accent
            }
            Label {
                text: "HLS Downloader Pro"
                font.pixelSize: 13
                font.weight: Font.DemiBold
                color: root.dark ? "#e8ebee" : "#202428"
            }
            Label {
                text: strings.titlebar_sub
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
                Label {
                    anchors.centerIn: parent
                    text: "—"
                    font.pixelSize: 14
                    color: root.dark ? "#dfe3e8" : "#3c4043"
                }
                MouseArea {
                    id: minHov
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.showMinimized()
                }
            }
            Rectangle {
                id: maxBtn
                width: 46; height: 30; radius: 6
                color: maxHov.containsMouse ? (root.dark ? "#2a323a" : "#d8dce0") : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: root.visibility === Window.Maximized ? "❐" : "▢"
                    font.pixelSize: 14
                    color: root.dark ? "#dfe3e8" : "#3c4043"
                }
                MouseArea {
                    id: maxHov
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: {
                        if (root.visibility === Window.Maximized)
                            root.showNormal()
                        else
                            root.showMaximized()
                    }
                }
            }
            Rectangle {
                id: closeBtn
                width: 46; height: 30; radius: 6
                color: closeHov.containsMouse ? "#c62828" : "transparent"
                Label {
                    anchors.centerIn: parent
                    text: "✕"
                    font.pixelSize: 14
                    color: root.dark ? "#dfe3e8" : "#3c4043"
                }
                MouseArea {
                    id: closeHov
                    anchors.fill: parent
                    hoverEnabled: true
                    onClicked: root.close()
                }
            }
        }
    }

    // ================================================== ABAS (Downloads/Config)
    TabBar {
        id: tabBar
        anchors.top: titleBar.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        contentHeight: 42
        background: Rectangle { color: root.dark ? "#181d22" : "#eef0f3" }
        TabButton {
            text: strings.tab_downloads
            font.pixelSize: 13
            implicitWidth: 160
            ToolTip.text: strings.tab_downloads_tip
            ToolTip.visible: hovered
            ToolTip.delay: 500
        }
        TabButton {
            text: strings.tab_settings
            font.pixelSize: 13
            implicitWidth: 160
            ToolTip.text: strings.tab_settings_tip
            ToolTip.visible: hovered
            ToolTip.delay: 500
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

        // ========================================================== ABA DOWNLOADS
        Item {
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12

                // ------------------------------------------------ Cartão de entrada
                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 260
                    Layout.minimumHeight: 260
                    radius: 12
                    color: root.dark ? "#1d2329" : "#ffffff"
                    border.color: root.dark ? "#2a323a" : "#e0e0e0"
                    border.width: 1

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 10

                        Label {
                            text: strings.entry_title
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                        }

                        // Área de colagem (dezenas/centenas de links, um por linha)
                        TextArea {
                            id: inputArea
                            Layout.fillWidth: true
                            Layout.preferredHeight: 110
                            placeholderText: strings.entry_placeholder
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Button {
                                text: strings.btn_add
                                highlighted: true
                                ToolTip.text: strings.btn_add_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: {
                                    bridge.addLinks(inputArea.text)
                                    inputArea.clear()
                                }
                            }
                            Button {
                                text: strings.btn_paste
                                ToolTip.text: strings.btn_paste_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: {
                                    bridge.pasteFromClipboard()
                                    inputArea.clear()
                                }
                            }
                            Button {
                                text: strings.btn_import
                                ToolTip.text: strings.btn_import_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: bridge.importTxt()
                            }
                            Item { Layout.fillWidth: true }
                            Button {
                                text: strings.btn_clear
                                flat: true
                                ToolTip.text: strings.btn_clear_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                                onClicked: inputArea.clear()
                            }
                        }

                        Label {
                            text: strings.entry_hint
                            font.pixelSize: 11
                            color: Material.secondaryTextColor
                            wrapMode: Text.Wrap
                        }
                    }
                }

                // ----------------------------------- Aviso de dependências externas
                Rectangle {
                    Layout.fillWidth: true
                    visible: !bridge.ytdlpAvailable || !bridge.ffmpegAvailable
                    height: 40
                    radius: 8
                    color: "#4a2c1f"
                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 12
                        anchors.rightMargin: 12
                        spacing: 8
                        Label {
                            text: strings.warn_attention
                            font.bold: true
                            color: "#ffcc80"
                        }
                        Label {
                            text: (bridge.ytdlpAvailable ? "" : strings.warn_ytdlp_missing + " ")
                                  + (bridge.ffmpegAvailable ? "" : strings.warn_ffmpeg_missing + " ")
                                  + strings.warn_tools
                            color: "#ffcc80"
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                    }
                }

                // --------------------------------------------------- Fila de downloads
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

                        Label {
                            text: strings.queue_title
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                        }

                        // Cabeçalho das colunas (alinhado com os itens abaixo)
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10
                            Item { Layout.fillWidth: true; Layout.minimumWidth: 180 }
                            Label { text: strings.h_status; Layout.preferredWidth: 104; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor }
                            Label { text: strings.h_progress; Layout.preferredWidth: 150; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor; horizontalAlignment: Text.AlignHCenter }
                            Label { text: strings.h_speed_size; Layout.preferredWidth: 130; font.pixelSize: 11; font.bold: true; color: Material.secondaryTextColor }
                            Item { Layout.preferredWidth: 136 }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: root.dark ? "#2a323a" : "#e0e0e0"
                        }

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

                            // Estado vazio
                            Rectangle {
                                anchors.fill: parent
                                visible: listView.count === 0
                                color: "transparent"
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 6
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: strings.empty_title
                                        font.pixelSize: 15
                                        color: Material.secondaryTextColor
                                    }
                                    Label {
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        text: strings.empty_hint
                                        font.pixelSize: 12
                                        color: Material.secondaryTextColor
                                    }
                                }
                            }
                        }
                    }
                }

                // ------------------------------------------------------- Barra de ações
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
                        Layout.preferredWidth: 200
                        value: root.statTotal > 0 ? (root.statDone + root.statError) / root.statTotal : 0
                        from: 0
                        to: 1
                    }

                    Button {
                        text: strings.btn_start
                        highlighted: true
                        ToolTip.text: strings.btn_start_tip
                        ToolTip.visible: hovered
                        ToolTip.delay: 500
                        onClicked: bridge.startQueue()
                    }
                    Button {
                        text: strings.btn_cancel_all
                        ToolTip.text: strings.btn_cancel_all_tip
                        ToolTip.visible: hovered
                        ToolTip.delay: 500
                        onClicked: bridge.cancelAll()
                    }
                    Button {
                        text: strings.btn_clear_finished
                        ToolTip.text: strings.btn_clear_finished_tip
                        ToolTip.visible: hovered
                        ToolTip.delay: 500
                        onClicked: bridge.clearFinished()
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

                    // ------------------------------------------------- Aparência
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        Layout.minimumHeight: 160
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 10
                            Label {
                                text: strings.cfg_appearance
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_dark
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                }
                                Switch {
                                    checked: root.dark
                                    ToolTip.text: strings.cfg_dark_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onToggled: bridge.setDark(checked)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_language
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                }
                                ComboBox {
                                    objectName: "langCombo"
                                    model: [{ text: "Português", value: "pt" },
                                            { text: "English", value: "en" }]
                                    textRole: "text"
                                    valueRole: "value"
                                    currentIndex: bridge.language === "en" ? 1 : 0
                                    Layout.preferredWidth: 160
                                    onActivated: bridge.setLanguage(currentValue)
                                }
                            }
                        }
                    }

                    // ------------------------------------------------- Downloads
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 185
                        Layout.minimumHeight: 185
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label {
                                text: strings.cfg_downloads
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_concurrency
                                    font.pixelSize: 13
                                }
                                SpinBox {
                                    id: concurrencySpin
                                    from: 1
                                    to: 8
                                    value: bridge.concurrency
                                    editable: true
                                    ToolTip.text: strings.cfg_concurrency_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onValueChanged: {
                                        if (value !== bridge.concurrency)
                                            bridge.setConcurrency(value)
                                    }
                                }
                                Item { Layout.fillWidth: true }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Button {
                                    text: strings.cfg_outdir
                                    ToolTip.text: strings.cfg_outdir_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
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

                    // ------------------------------------------------------- Rede
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 150
                        Layout.minimumHeight: 150
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label {
                                text: strings.cfg_network
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                ToolTip.text: strings.cfg_network_tip
                                ToolTip.visible: hovered
                                ToolTip.delay: 500
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_limit_rate
                                    font.pixelSize: 13
                                }
                                SpinBox {
                                    id: limitRateSpin
                                    from: 0
                                    to: 100
                                    stepSize: 1
                                    value: bridge.limitRateMB
                                    editable: true
                                    ToolTip.text: strings.cfg_limit_rate_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onValueChanged: {
                                        if (value !== bridge.limitRateMB)
                                            bridge.setLimitRateMB(value)
                                    }
                                }
                                Item { Layout.fillWidth: true }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_fragments
                                    font.pixelSize: 13
                                }
                                SpinBox {
                                    id: fragmentsSpin
                                    from: 1
                                    to: 8
                                    value: bridge.fragments
                                    editable: true
                                    ToolTip.text: strings.cfg_fragments_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onValueChanged: {
                                        if (value !== bridge.fragments)
                                            bridge.setFragments(value)
                                    }
                                }
                                Item { Layout.fillWidth: true }
                            }
                        }
                    }

                    // -------------------------------------------------- Cookies
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 285
                        Layout.minimumHeight: 285
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label {
                                text: strings.cfg_cookies_title
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_cookies_use
                                    font.pixelSize: 13
                                    Layout.fillWidth: true
                                }
                                Switch {
                                    checked: bridge.cookiesEnabled
                                    ToolTip.text: strings.cfg_cookies_use_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onToggled: bridge.setCookiesEnabled(checked)
                                }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_browser
                                    font.pixelSize: 13
                                    color: Material.secondaryTextColor
                                }
                                ComboBox {
                                    id: browserCombo
                                    model: ["Chrome", "Chromium", "Edge", "Firefox", "Opera", "Vivaldi", "Brave"]
                                    currentIndex: bridge.cookiesBrowserIndex
                                    onActivated: bridge.setCookiesBrowserIndex(currentIndex)
                                    enabled: bridge.cookiesEnabled
                                    Layout.preferredWidth: 200
                                    ToolTip.text: strings.cfg_browser_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                }
                                Item { Layout.fillWidth: true }
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                Label {
                                    text: strings.cfg_cookies_file
                                    font.pixelSize: 12
                                    color: Material.secondaryTextColor
                                }
                                TextField {
                                    text: bridge.cookiesFile
                                    onEditingFinished: bridge.setCookiesFile(text)
                                    placeholderText: strings.cfg_cookies_placeholder
                                    selectByMouse: true
                                    Layout.fillWidth: true
                                    Layout.maximumWidth: 360
                                    ToolTip.text: strings.cfg_cookies_file_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                }
                                Button {
                                    text: strings.btn_choose
                                    enabled: bridge.cookiesEnabled
                                    ToolTip.text: strings.btn_choose_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
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

                    // ------------------------------------------------ Ferramentas
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 130
                        Layout.minimumHeight: 130
                        radius: 12
                        color: root.dark ? "#1d2329" : "#ffffff"
                        border.color: root.dark ? "#2a323a" : "#e0e0e0"
                        border.width: 1
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 16
                            spacing: 12
                            Label {
                                text: strings.cfg_tools
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "yt-dlp"; font.pixelSize: 13; Layout.preferredWidth: 90 }
                                Rectangle {
                                    width: 10; height: 10; radius: 5
                                    color: bridge.ytdlpAvailable ? "#2e7d32" : "#c62828"
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Label {
                                    text: bridge.ytdlpAvailable ? strings.tool_found : strings.tool_ytdlp_missing
                                    font.pixelSize: 12
                                    color: Material.secondaryTextColor
                                    Layout.fillWidth: true
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "ffmpeg"; font.pixelSize: 13; Layout.preferredWidth: 90 }
                                Rectangle {
                                    width: 10; height: 10; radius: 5
                                    color: bridge.ffmpegAvailable ? "#2e7d32" : "#c62828"
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                Label {
                                    text: bridge.ffmpegAvailable ? strings.tool_found : strings.tool_ffmpeg_missing
                                    font.pixelSize: 12
                                    color: Material.secondaryTextColor
                                    Layout.fillWidth: true
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // ===================================================== ZONAS DE REDIMENSIONAR
    // Janela sem borda nativa: cantos e bordas próprios (resize nativo do OS)
    Item {
        anchors.fill: parent
        z: 80
        MouseArea {
            anchors.left: parent.left; anchors.top: parent.top
            width: 8; height: 8
            cursorShape: Qt.SizeFDiagCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.TopEdge | Qt.LeftEdge)
        }
        MouseArea {
            anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top
            width: 60; height: 8
            cursorShape: Qt.SizeVerCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.TopEdge)
        }
        MouseArea {
            anchors.right: parent.right; anchors.top: parent.top
            width: 8; height: 8
            cursorShape: Qt.SizeBDiagCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.TopEdge | Qt.RightEdge)
        }
        MouseArea {
            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 60
            cursorShape: Qt.SizeHorCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.LeftEdge)
        }
        MouseArea {
            anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
            width: 8; height: 60
            cursorShape: Qt.SizeHorCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.RightEdge)
        }
        MouseArea {
            anchors.left: parent.left; anchors.bottom: parent.bottom
            width: 8; height: 8
            cursorShape: Qt.SizeBDiagCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.BottomEdge | Qt.LeftEdge)
        }
        MouseArea {
            anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom
            width: 60; height: 8
            cursorShape: Qt.SizeVerCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.BottomEdge)
        }
        MouseArea {
            anchors.right: parent.right; anchors.bottom: parent.bottom
            width: 8; height: 8
            cursorShape: Qt.SizeFDiagCursor
            onPressed: if (root.visibility !== Window.Maximized) root.startSystemResize(Qt.BottomEdge | Qt.RightEdge)
        }
    }

    // -------------------------------------------------------------------- Toast
    Rectangle {
        id: toast
        visible: false
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 28
        width: toastText.implicitWidth + 36
        height: 42
        radius: 21
        color: root.dark ? "#2b3138" : "#32363c"
        z: 100

        Label {
            id: toastText
            anchors.centerIn: parent
            color: "white"
            font.pixelSize: 13
        }
        Timer {
            id: toastTimer
            interval: 2600
            onTriggered: toast.visible = false
        }
    }

    // ----------------------------------------------------------- Cores de status
    function badgeColor(status) {
        switch (status) {
        case "Concluído":       return "#2e7d32"
        case "Erro":            return "#c62828"
        case "Baixando":        return "#00838f"
        case "Analisando HTML": return "#ef6c00"
        case "Cancelado":       return "#546e7a"
        default:                return "#455a64"
        }
    }

    // ------------------------------------------------------------ Delegate
    Component {
        id: downloadDelegate
        Item {
            id: rowItem
            width: listView.width
            height: 64
            property bool editing: false

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 12
                spacing: 10

                // Miniatura + URL / Título (edição inline)
                Row {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 180
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 8

                    // Miniatura gerada do próprio vídeo (fallback: ▶)
                    Rectangle {
                        width: 72; height: 40
                        radius: 4
                        color: root.dark ? "#262e35" : "#eef0f3"
                        border.color: root.dark ? "#2a323a" : "#dddddd"
                        border.width: 1
                        Image {
                            anchors.fill: parent
                            visible: model.thumb !== ""
                            source: model.thumb
                            fillMode: Image.PreserveAspectCrop
                            clip: true
                        }
                        Label {
                            anchors.centerIn: parent
                            visible: model.thumb === ""
                            text: "▶"
                            font.pixelSize: 12
                            color: Material.secondaryTextColor
                        }
                    }

                    Column {
                        width: parent.width - 80
                        spacing: 2

                        Label {
                            width: parent.width
                            text: model.title
                            elide: Text.ElideMiddle
                            font.weight: Font.DemiBold
                            font.pixelSize: 13
                        }
                        TextField {
                            visible: rowItem.editing
                            height: 24
                            width: parent.width
                            padding: 4
                            font.pixelSize: 11
                            onVisibleChanged: if (visible) text = model.url
                            onAccepted: {
                                bridge.editUrl(index, text)
                                rowItem.editing = false
                            }
                            onEditingFinished: {
                                bridge.editUrl(index, text)
                                rowItem.editing = false
                            }
                            Keys.onEscapePressed: rowItem.editing = false
                        }
                        Label {
                            width: parent.width
                            visible: !rowItem.editing
                            text: model.url
                            elide: Text.ElideMiddle
                            font.pixelSize: 11
                            color: Material.secondaryTextColor
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onDoubleClicked: rowItem.editing = true
                            }
                        }
                    }
                }

                // Selo de status + erro visível
                Column {
                    Layout.preferredWidth: 104
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 3

                    Rectangle {
                        width: 104
                        height: 24
                        radius: 12
                        color: root.badgeColor(model.status)

                        Label {
                            anchors.centerIn: parent
                            text: strings["s_" + model.status] || model.status
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

                    // Erro truncado, clicável → diálogo com a mensagem completa
                    Label {
                        width: parent.width
                        visible: model.status === "Erro" && model.error.length > 0
                        text: model.error
                        elide: Text.ElideRight
                        font.pixelSize: 9
                        color: "#c62828"
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.errorText = model.error
                                errorDialog.open()
                            }
                        }
                    }
                }

                // Progresso
                Column {
                    Layout.preferredWidth: 150
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2

                    ProgressBar {
                        width: 150
                        height: 6
                        from: 0
                        to: 100
                        value: model.progress
                        indeterminate: model.status === "Analisando HTML"
                    }
                    Label {
                        anchors.right: parent.right
                        text: model.status === "Concluído" ? "100%" : model.progress + "%"
                        font.pixelSize: 11
                        color: Material.secondaryTextColor
                    }
                }

                // Velocidade / Tamanho
                Column {
                    Layout.preferredWidth: 130
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 2
                    Label {
                        width: parent.width
                        text: model.speed
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }
                    Label {
                        width: parent.width
                        text: model.size
                        font.pixelSize: 11
                        color: Material.secondaryTextColor
                        elide: Text.ElideRight
                    }
                }

                // Ações: copiar / editar / cancelar / abrir pasta
                Item {
                    Layout.preferredWidth: 136
                    Layout.alignment: Qt.AlignVCenter
                    Row {
                        anchors.centerIn: parent
                        spacing: 3

                        ToolButton {
                            width: 30; height: 28
                            text: "✎"
                            font.pixelSize: 11
                            visible: model.status === "Aguardando"
                                     || model.status === "Erro"
                                     || model.status === "Cancelado"
                            ToolTip.text: strings.tip_edit
                            ToolTip.visible: hovered
                            ToolTip.delay: 500
                            onClicked: rowItem.editing = true
                        }
                        ToolButton {
                            width: 30; height: 28
                            text: "⧉"
                            font.pixelSize: 11
                            ToolTip.text: strings.tip_copy
                            ToolTip.visible: hovered
                            ToolTip.delay: 500
                            onClicked: bridge.copyLink(model.url)
                        }
                        ToolButton {
                            width: 30; height: 28
                            text: "✕"
                            font.pixelSize: 11
                            visible: model.status === "Baixando"
                                     || model.status === "Analisando HTML"
                                     || model.status === "Aguardando"
                            ToolTip.text: strings.tip_cancel
                            ToolTip.visible: hovered
                            ToolTip.delay: 500
                            onClicked: bridge.cancelItem(index)
                        }
                        ToolButton {
                            width: 40; height: 28
                            text: strings.btn_open
                            font.pixelSize: 9
                            visible: model.status === "Concluído"
                            ToolTip.text: strings.tip_open
                            ToolTip.visible: hovered
                            ToolTip.delay: 500
                            onClicked: bridge.openDownloadPath(model.path)
                        }
                    }
                }
            }

            // Separador
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
        standardButtons: Dialog.Ok
        width: 540
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        contentItem: Label {
            width: errorDialog.availableWidth
            text: root.errorText
            wrapMode: Text.Wrap
            font.pixelSize: 12
            color: "#c62828"
        }
    }
}
