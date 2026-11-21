import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import "../components"

// Aba Sobre: identidade do app, atualizações, licença e recursos.
Item {
    id: page
    objectName: "aboutPage"

    property var appRoot
    property var strings: ({})
    readonly property bool showHero: width >= 1050 && height >= 650
    readonly property int scrollGutter: 16
    readonly property string projectUrl: "https://github.com/landre-codes/HLS-Downloader-Pro"

    ScrollView {
        id: aboutScroll
        objectName: "aboutScroll"
        anchors.fill: parent
        anchors.margins: 16
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AlwaysOn

        ColumnLayout {
            width: aboutScroll.availableWidth - page.scrollGutter
            spacing: 12

            PageHero {
                Layout.fillWidth: true
                compact: !page.showHero
                theme: appRoot.theme
                title: strings.about_title
                description: strings.hero_about_desc
            }

            // ------------------------------------------------ Aplicação
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: aboutAppCol.implicitHeight + 32
                radius: 12
                color: appRoot.theme.cardBg
                border.color: appRoot.theme.cardBorder
                border.width: 1

                ColumnLayout {
                    id: aboutAppCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 16
                    spacing: 12

                    SectionHeader {
                        Layout.fillWidth: true
                        theme: appRoot.theme
                        iconSource: appRoot.settingsIcon("info")
                        title: strings.about_app_title
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        Label {
                            text: "HLS Downloader Pro"
                            font.pixelSize: 22
                            font.bold: true
                            color: appRoot.theme.text
                        }
                        Item { Layout.fillWidth: true }
                        Label {
                            text: "v" + bridge.appVersion
                            font.pixelSize: 14
                            color: appRoot.theme.textSecondary
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: strings.about_app_desc
                        wrapMode: Text.Wrap
                        font.pixelSize: 14
                        color: appRoot.theme.textSecondary
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: aboutAppCol.width > 720 ? 2 : 1
                        columnSpacing: 24
                        rowSpacing: 8

                        Label {
                            text: strings.about_version
                            font.pixelSize: 14
                            color: appRoot.theme.textMuted
                        }
                        Label {
                            text: bridge.appVersion
                            font.pixelSize: 14
                            color: appRoot.theme.text
                        }
                        Label {
                            text: strings.about_license
                            font.pixelSize: 14
                            color: appRoot.theme.textMuted
                        }
                        Label {
                            text: strings.about_license_value
                            font.pixelSize: 14
                            color: appRoot.theme.text
                        }
                        Label {
                            text: strings.about_tech
                            font.pixelSize: 14
                            color: appRoot.theme.textMuted
                        }
                        Label {
                            Layout.fillWidth: true
                            text: strings.about_tech_value
                            font.pixelSize: 14
                            color: appRoot.theme.text
                            wrapMode: Text.Wrap
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: strings.about_copyright
                        font.pixelSize: 13
                        color: appRoot.theme.textMuted
                        horizontalAlignment: appRoot.isRtl
                                             ? (Text.AlignRight | Text.AlignAbsolute)
                                             : (Text.AlignLeft | Text.AlignAbsolute)
                    }
                }
            }

            // ------------------------------------------------ Atualizações
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: aboutUpdatesCol.implicitHeight + 32
                radius: 12
                color: appRoot.theme.cardBg
                border.color: appRoot.theme.cardBorder
                border.width: 1

                ColumnLayout {
                    id: aboutUpdatesCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 16
                    spacing: 10

                    SectionHeader {
                        Layout.fillWidth: true
                        theme: appRoot.theme
                        iconSource: appRoot.settingsIcon("download")
                        title: strings.about_updates_title
                    }

                    Label {
                        Layout.fillWidth: true
                        text: strings.about_updates_desc
                        wrapMode: Text.Wrap
                        font.pixelSize: 14
                        color: appRoot.theme.textSecondary
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        AppButton {
                            text: strings.update_check
                            variant: "secondary"
                            icon.source: appRoot.iconPath("retry")
                            icon.width: 18
                            icon.height: 18
                            display: AbstractButton.TextBesideIcon
                            enabled: !bridge.updateBusy
                            onClicked: bridge.checkForUpdates()
                        }
                        AppButton {
                            text: strings.update_download
                            icon.source: appRoot.iconPath("download", enabled)
                            icon.width: 18
                            icon.height: 18
                            display: AbstractButton.TextBesideIcon
                            visible: bridge.updateAvailable
                            enabled: !bridge.updateBusy
                            variant: "warning"
                            onClicked: {
                                if (bridge.queueActive || bridge.compressionActive)
                                    appRoot.openConfirmUpdate()
                                else
                                    bridge.downloadUpdate()
                            }
                        }
                        AppButton {
                            text: strings.update_open_page
                            variant: "secondary"
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16
                            icon.height: 16
                            display: AbstractButton.TextBesideIcon
                            visible: bridge.updateHtmlUrl !== ""
                            onClicked: bridge.openReleasePage()
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: strings.update_current + " " + bridge.appVersion
                        font.pixelSize: 14
                        color: appRoot.theme.textSecondary
                    }

                    Label {
                        Layout.fillWidth: true
                        visible: bridge.updateStatus !== ""
                        text: bridge.updateStatus
                        wrapMode: Text.Wrap
                        font.pixelSize: 14
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
                        font.pixelSize: 14
                        font.bold: true
                        color: appRoot.theme.textSecondary
                        visible: bridge.updateNotes !== ""
                    }

                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 110
                        visible: bridge.updateNotes !== ""
                        clip: true
                        rightPadding: 16

                        TextArea {
                            readOnly: true
                            text: bridge.updateNotes
                            font.pixelSize: 14
                            wrapMode: TextEdit.Wrap
                        }
                    }
                }
            }

            // ------------------------------------------------ Recursos
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: aboutResourcesCol.implicitHeight + 32
                radius: 12
                color: appRoot.theme.cardBg
                border.color: appRoot.theme.cardBorder
                border.width: 1

                ColumnLayout {
                    id: aboutResourcesCol
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: 16
                    spacing: 10

                    SectionHeader {
                        Layout.fillWidth: true
                        theme: appRoot.theme
                        iconSource: appRoot.settingsIcon("package")
                        title: strings.about_resources_title
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        AppButton {
                            text: strings.about_repository
                            variant: "secondary"
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16
                            icon.height: 16
                            display: AbstractButton.TextBesideIcon
                            onClicked: Qt.openUrlExternally(page.projectUrl)
                        }
                        AppButton {
                            text: strings.about_issues
                            variant: "secondary"
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16
                            icon.height: 16
                            display: AbstractButton.TextBesideIcon
                            onClicked: Qt.openUrlExternally(page.projectUrl + "/issues")
                        }
                        AppButton {
                            text: strings.about_dependencies
                            variant: "secondary"
                            icon.source: appRoot.iconPath("settings")
                            icon.width: 16
                            icon.height: 16
                            display: AbstractButton.TextBesideIcon
                            onClicked: appRoot.goToSettingsTab()
                        }
                        AppButton {
                            text: strings.about_open_logs
                            variant: "secondary"
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16
                            icon.height: 16
                            display: AbstractButton.TextBesideIcon
                            onClicked: bridge.openLogFolder()
                        }
                        AppButton {
                            text: strings.about_open_output
                            variant: "secondary"
                            icon.source: appRoot.iconPath("open")
                            icon.width: 16
                            icon.height: 16
                            display: AbstractButton.TextBesideIcon
                            onClicked: bridge.openOutputFolder()
                        }
                    }

                    Label {
                        Layout.fillWidth: true
                        text: strings.about_third_party
                        font.pixelSize: 14
                        font.bold: true
                        color: appRoot.theme.textSecondary
                    }
                    Label {
                        Layout.fillWidth: true
                        text: strings.about_third_party_desc
                        wrapMode: Text.Wrap
                        font.pixelSize: 13
                        color: appRoot.theme.textMuted
                    }
                }
            }
        }
    }
}
