import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

        Item {
    id: page
    property var appRoot
    property var strings: ({})
    property alias settingsScroll: settingsScroll

    ScrollView {
                id: settingsScroll
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AsNeeded

                ColumnLayout {
                    width: settingsScroll.availableWidth
                    spacing: 12

                    // -------------------------------------------- Aparência
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: appearanceCol.implicitHeight + 32
                        radius: 12
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
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
                                AppToolButton {
                                    display: AbstractButton.IconOnly
                                    icon.source: appRoot.dark
                                                 ? appRoot.iconPath("sun")
                                                 : appRoot.iconPath("moon")
                                    icon.width: 20
                                    icon.height: 20
                                    Accessible.name: strings.cfg_dark
                                    ToolTip.text: strings.cfg_dark_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onClicked: bridge.setDark(!appRoot.dark)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_language; Layout.fillWidth: true; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                AppComboBox {
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
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
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
                                AppTipLabel {
                                    text: strings.naming_label
                                    tip: strings.naming_tip
                                    Layout.fillWidth: true
                                    font.pixelSize: 13
                                    wrapMode: Text.WordWrap
                                }
                                AppComboBox {
                                    id: namingCombo
                                    model: [
                                        { text: strings.naming_id, value: "id" },
                                        { text: strings.naming_title, value: "title" }
                                    ]
                                    textRole: "text"
                                    valueRole: "value"
                                    currentIndex: bridge.namingMode === "title" ? 1 : 0
                                    Layout.preferredWidth: 220
                                    ToolTip.text: strings.naming_tip
                                    ToolTip.visible: hovered
                                    ToolTip.delay: 500
                                    onActivated: bridge.setNamingMode(currentValue)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                AppButton {
                                    text: strings.cfg_outdir
                                    ToolTip.text: strings.cfg_outdir_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onClicked: bridge.chooseOutputFolder()
                                }
                                Label {
                                    id: outputFolderLabel
                                    text: bridge.outputFolder
                                    color: appRoot.theme.textSecondary
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
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
                        border.width: 1
                        ColumnLayout {
                            id: networkCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            Label {
                                text: strings.cfg_network; font.pixelSize: 15; font.weight: Font.DemiBold
                                ToolTip.text: strings.cfg_network_tip; ToolTip.visible: networkHover.hovered; ToolTip.delay: 500
                                HoverHandler { id: networkHover }
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
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
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
                                AppSwitch {
                                    checked: bridge.cookiesEnabled
                                    ToolTip.text: strings.cfg_cookies_use_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onToggled: bridge.setCookiesEnabled(checked)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_browser; font.pixelSize: 13; color: appRoot.theme.textSecondary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                AppComboBox {
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
                                    color: appRoot.theme.textSecondary
                                    Layout.preferredWidth: 220
                                    wrapMode: Text.WordWrap
                                }
                                AppHintField {
                                    text: bridge.cookiesFile
                                    onEditingFinished: bridge.setCookiesFile(text)
                                    hint: strings.cfg_cookies_placeholder
                                    selectByMouse: true
                                    Layout.fillWidth: true
                                    ToolTip.text: strings.cfg_cookies_file_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                }
                                AppButton {
                                    text: strings.btn_choose
                                    enabled: bridge.cookiesEnabled
                                    ToolTip.text: strings.btn_choose_tip; ToolTip.visible: hovered; ToolTip.delay: 500
                                    onClicked: bridge.chooseCookiesFile()
                                }
                            }
                            Label {
                                text: strings.cfg_cookies_hint
                                font.pixelSize: 11
                                color: appRoot.theme.textSecondary
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
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
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
                                    color: appRoot.theme.busyText
                                    font.pixelSize: 12
                                    Layout.rightMargin: 6
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                AppButton {
                                    text: strings.dep_update_all
                                    enabled: !bridge.depsBusy
                                    onClicked: appRoot.askUpdateAllDependencies()
                                }
                                AppButton {
                                    text: strings.dep_recheck
                                    enabled: !bridge.depsBusy
                                    onClicked: bridge.refreshDependencies()
                                }
                            }
                            Label {
                                text: strings.cfg_deps_tip
                                font.pixelSize: 11
                                color: appRoot.theme.textSecondary
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label {
                                    text: strings.dep_ytdlp_channel
                                    font.pixelSize: 13
                                    color: appRoot.theme.textSecondary
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                AppComboBox {
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
                                        color: modelData.found ? appRoot.theme.successText : appRoot.theme.dangerFill
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
                                        color: appRoot.theme.textSecondary
                                        Layout.preferredWidth: 96
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.strategy === "bundled"
                                              ? (modelData.found ? strings.dep_bundled : strings.dep_missing)
                                              : ((modelData.required ? strings.dep_required : strings.dep_optional)
                                                 + " · " + (modelData.found ? strings.dep_found : strings.dep_missing))
                                        font.pixelSize: 11
                                        color: modelData.found ? appRoot.theme.textSecondary : appRoot.theme.dangerFill
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    AppButton {
                                        visible: modelData.installable
                                        enabled: !bridge.depsBusy
                                        text: modelData.found ? strings.dep_update : strings.dep_install
                                        onClicked: appRoot.askInstallDependency(
                                            modelData.key, modelData.name, modelData.found
                                        )
                                    }
                                }
                            }

                            AppTerminalPanel {
                                theme: appRoot.theme
                                strings: page.strings
                                title: strings.dep_console
                                output: appRoot.depsLog
                                panelHeight: 140
                            }
                        }
                    }

                    // -------------------------------------------- Sobre/atualizações
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: aboutCol.implicitHeight + 32
                        radius: 12
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
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
                                    color: appRoot.theme.textSecondary
                                }
                                AppButton {
                                    text: strings.update_check
                                    icon.source: appRoot.iconPath("retry")
                                    icon.width: 16; icon.height: 16
                                    display: AbstractButton.TextBesideIcon
                                    enabled: !bridge.updateBusy
                                    onClicked: bridge.checkForUpdates()
                                }
                                AppButton {
                                    text: strings.update_download
                                    icon.source: appRoot.iconPath("download")
                                    icon.width: 16; icon.height: 16
                                    display: AbstractButton.TextBesideIcon
                                    visible: bridge.updateAvailable
                                    enabled: !bridge.updateBusy
                                    highlighted: true
                                    onClicked: {
                                        if (bridge.queueActive || bridge.compressionActive)
                                            appRoot.openConfirmUpdate()
                                        else
                                            bridge.downloadUpdate()
                                    }
                                }
                                AppButton {
                                    text: strings.update_open_page
                                    icon.source: appRoot.iconPath("open")
                                    icon.width: 16; icon.height: 16
                                    display: AbstractButton.TextBesideIcon
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
                                color: appRoot.theme.textSecondary
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
