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
    readonly property bool showHero: width >= 1050 && height >= 650
    readonly property int scrollGutter: 16

    ScrollView {
                id: settingsScroll
                objectName: "settingsScroll"
                anchors.fill: parent
                anchors.margins: 16
                clip: true
                contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical.policy: ScrollBar.AlwaysOn

                ColumnLayout {
                    width: settingsScroll.availableWidth - page.scrollGutter
                    spacing: 12

                    PageHero {
                        Layout.fillWidth: true
                        compact: !page.showHero
                        theme: appRoot.theme
                        title: strings.tab_settings
                        description: strings.hero_settings_desc
                    }

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
                            SectionHeader {
                                Layout.fillWidth: true
                                theme: appRoot.theme
                                iconSource: appRoot.dark ? appRoot.settingsIcon("moon")
                                                         : appRoot.settingsIcon("sun")
                                title: strings.cfg_appearance
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_language; Layout.fillWidth: true; font.pixelSize: 14; wrapMode: Text.WordWrap }
                                LanguageComboBox {
                                    id: langCombo
                                    objectName: "languageCombo"
                                    appRoot: page.appRoot
                                    model: bridge.languages
                                    textRole: "name"
                                    valueRole: "code"
                                    currentIndex: {
                                        for (var i = 0; i < model.length; i++)
                                            if (model[i].code === bridge.language)
                                                return i
                                        return 0
                                    }
                                    Layout.preferredWidth: 250
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
                            SectionHeader {
                                Layout.fillWidth: true
                                theme: appRoot.theme
                                iconSource: appRoot.settingsIcon("download")
                                title: strings.cfg_downloads
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_concurrency; Layout.fillWidth: true; font.pixelSize: 14; wrapMode: Text.WordWrap }
                                AppSpinBox {
                                    id: concurrencySpin
                                    from: 1; to: 8
                                    value: bridge.concurrency
                                    editable: true
                                    tipText: strings.cfg_concurrency_tip
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
                                    font.pixelSize: 14
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
                                    tipText: strings.naming_tip
                                    onActivated: bridge.setNamingMode(currentValue)
                                }
                            }
                            FolderPickerField {
                                Layout.fillWidth: true
                                theme: appRoot.theme
                                label: strings.folder_output_label
                                path: bridge.outputFolder
                                changeText: strings.folder_change
                                openText: strings.folder_open
                                copyText: strings.folder_copy
                                folderIcon: appRoot.iconPath("open")
                                copyIcon: appRoot.iconPath("copy")
                                changeIcon: appRoot.iconPath("edit")
                                openIcon: appRoot.iconPath("open")
                                changeTip: strings.folder_output_label
                                openTip: bridge.outputFolder
                                onChangeRequested: bridge.chooseOutputFolder()
                                onOpenRequested: bridge.openOutputFolder()
                                onCopyRequested: bridge.copyLink(bridge.outputFolder)
                            }
                        }
                    }

                    // -------------------------------------------- Integridade
                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: integrityCol.implicitHeight + 32
                        radius: 12
                        color: appRoot.theme.cardBg
                        border.color: appRoot.theme.cardBorder
                        border.width: 1
                        ColumnLayout {
                            id: integrityCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 16
                            spacing: 12
                            SectionHeader {
                                Layout.fillWidth: true
                                theme: appRoot.theme
                                iconSource: appRoot.settingsIcon("shield")
                                title: strings.cfg_sidecars
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label {
                                    text: strings.cfg_sidecars_tip
                                    Layout.fillWidth: true
                                    font.pixelSize: 14
                                    color: appRoot.theme.textSecondary
                                    wrapMode: Text.WordWrap
                                }
                                AppSwitch {
                                    checked: bridge.sidecarsEnabled
                                    Accessible.name: strings.cfg_sidecars
                                    onToggled: bridge.setSidecarsEnabled(checked)
                                }
                            }
                            AppButton {
                                text: strings.cfg_sidecars_cleanup
                                variant: "secondary"
                                dangerHover: true
                                icon.source: appRoot.iconPath("trash")
                                icon.width: 16
                                icon.height: 16
                                display: AbstractButton.TextBesideIcon
                                onClicked: bridge.cleanupSidecars()
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
                            SectionHeader {
                                Layout.fillWidth: true
                                theme: appRoot.theme
                                iconSource: appRoot.settingsIcon("network")
                                title: strings.cfg_network
                                tipTitle: strings.cfg_network
                                tipText: strings.cfg_network_tip
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_limit_rate; Layout.fillWidth: true; font.pixelSize: 14; wrapMode: Text.WordWrap }
                                AppSpinBox {
                                    id: limitRateSpin
                                    from: 0; to: 100; stepSize: 1
                                    value: bridge.limitRateMB
                                    editable: true
                                    tipText: strings.cfg_limit_rate_tip
                                    onValueChanged: if (value !== bridge.limitRateMB) bridge.setLimitRateMB(value)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_fragments; Layout.fillWidth: true; font.pixelSize: 14; wrapMode: Text.WordWrap }
                                AppSpinBox {
                                    id: fragmentsSpin
                                    from: 1; to: 8
                                    value: bridge.fragments
                                    editable: true
                                    tipText: strings.cfg_fragments_tip
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
                            SectionHeader {
                                Layout.fillWidth: true
                                theme: appRoot.theme
                                iconSource: appRoot.settingsIcon("cookie")
                                title: strings.cfg_cookies_title
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_cookies_use; font.pixelSize: 14; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                AppSwitch {
                                    checked: bridge.cookiesEnabled
                                    tipText: strings.cfg_cookies_use_tip
                                    onToggled: bridge.setCookiesEnabled(checked)
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label { text: strings.cfg_browser; font.pixelSize: 14; color: appRoot.theme.textSecondary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                                BrowserComboBox {
                                    id: browserCombo
                                    objectName: "browserCombo"
                                    appRoot: page.appRoot
                                    textRole: "name"
                                    valueRole: "icon"
                                    model: [
                                        { icon: "chrome", name: "Chrome" },
                                        { icon: "chromium", name: "Chromium" },
                                        { icon: "edge", name: "Edge" },
                                        { icon: "firefox", name: "Firefox" },
                                        { icon: "opera", name: "Opera" },
                                        { icon: "vivaldi", name: "Vivaldi" },
                                        { icon: "brave", name: "Brave" }
                                    ]
                                    currentIndex: bridge.cookiesBrowserIndex
                                    onActivated: bridge.setCookiesBrowserIndex(currentIndex)
                                    enabled: bridge.cookiesEnabled
                                    Layout.preferredWidth: 200
                                    tipText: strings.cfg_browser_tip
                                }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Label {
                                    text: strings.cfg_cookies_file
                                    font.pixelSize: 14
                                    color: appRoot.theme.textSecondary
                                    Layout.preferredWidth: 220
                                    wrapMode: Text.WordWrap
                                }
                                AppHintField {
                                    text: bridge.cookiesFile
                                    onEditingFinished: bridge.setCookiesFile(text)
                                    hint: strings.cfg_cookies_placeholder
                                    strings: page.strings
                                    selectByMouse: true
                                    Layout.fillWidth: true
                                    tipText: strings.cfg_cookies_file_tip
                                }
                                AppButton {
                                    text: strings.btn_choose
                                    variant: "secondary"
                                    icon.source: appRoot.iconPath("file")
                                    icon.width: 18; icon.height: 18
                                    display: AbstractButton.TextBesideIcon
                                    tipText: strings.btn_choose_tip
                                    onClicked: bridge.chooseCookiesFile()
                                }
                            }
                            Label {
                                text: strings.cfg_cookies_hint
                                font.pixelSize: 14
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
                                SectionHeader {
                                    Layout.fillWidth: true
                                    theme: appRoot.theme
                                    iconSource: appRoot.settingsIcon("package")
                                    title: strings.cfg_deps_title
                                }
                                Item { Layout.fillWidth: true }
                                Label {
                                    visible: bridge.depsBusy
                                    text: bridge.depsBusy ? strings.dep_busy : ""
                                    color: appRoot.theme.busyText
                                    font.pixelSize: 14
                                    Layout.rightMargin: 6
                                    Layout.alignment: Qt.AlignVCenter
                                }
                                AppButton {
                                    text: strings.dep_update_all
                                    variant: "secondary"
                                    icon.source: appRoot.iconPath("download")
                                    icon.width: 18; icon.height: 18
                                    display: AbstractButton.TextBesideIcon
                                    enabled: !bridge.depsBusy
                                    onClicked: appRoot.askUpdateAllDependencies()
                                }
                                AppButton {
                                    text: strings.dep_recheck
                                    variant: "secondary"
                                    icon.source: appRoot.iconPath("search")
                                    icon.width: 18; icon.height: 18
                                    display: AbstractButton.TextBesideIcon
                                    enabled: !bridge.depsBusy
                                    onClicked: bridge.refreshDependencies()
                                }
                            }
                            Label {
                                text: strings.cfg_deps_tip
                                font.pixelSize: 14
                                color: appRoot.theme.textSecondary
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                            }

                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 12
                                Label {
                                    text: strings.dep_ytdlp_channel
                                    font.pixelSize: 14
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
                                        font.pixelSize: 14
                                        Layout.preferredWidth: 104
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.version ? ("v" + modelData.version) : ""
                                        font.pixelSize: 14
                                        color: appRoot.theme.textSecondary
                                        Layout.preferredWidth: 96
                                        elide: Text.ElideRight
                                    }
                                    Label {
                                        text: modelData.strategy === "bundled"
                                              ? (modelData.found ? strings.dep_bundled : strings.dep_missing)
                                              : ((modelData.required ? strings.dep_required : strings.dep_optional)
                                                 + " · " + (modelData.found ? strings.dep_found : strings.dep_missing))
                                        font.pixelSize: 14
                                        color: modelData.found ? appRoot.theme.textSecondary : appRoot.theme.dangerFill
                                        Layout.fillWidth: true
                                        elide: Text.ElideRight
                                    }
                                    AppButton {
                                        visible: modelData.installable
                                        enabled: !bridge.depsBusy
                                        variant: "secondary"
                                        size: "compact"
                                        text: modelData.found ? strings.dep_update : strings.dep_install
                                        icon.source: appRoot.iconPath(modelData.found ? "retry" : "download")
                                        icon.width: 16; icon.height: 16
                                        display: AbstractButton.TextBesideIcon
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

                }
            }
        }
