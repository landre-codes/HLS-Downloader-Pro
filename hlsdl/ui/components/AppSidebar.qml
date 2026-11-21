import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Navegação vertical principal. Modos: expandida (ícone + texto),
// compacta (ícone) e drawer (sobreposição em janelas estreitas).
Rectangle {
    id: rail

    property var theme: null
    property var strings: ({})
    property var appRoot: null
    property int currentIndex: 0
    property bool expanded: true
    property bool drawer: false
    property int downloadsBadge: 0
    property int compressionBadge: 0

    signal activated(int index)
    signal closeRequested()

    readonly property color _bg: theme ? theme.tabBg
                                       : (typeof bridge !== "undefined" && bridge.dark
                                          ? "#16202c" : "#edf2f9")
    readonly property color _border: theme ? theme.divider
                                            : (typeof bridge !== "undefined" && bridge.dark
                                               ? "#304152" : "#d8e1ee")
    implicitWidth: (drawer || expanded) ? 220 : 64
    width: implicitWidth
    color: _bg
    Behavior on width {
        enabled: Qt.platform && Qt.platform.pluginName !== "offscreen"
        NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
    }

    Rectangle {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: 1
        color: rail._border
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 4

        RowLayout {
            visible: rail.drawer
            Layout.fillWidth: true
            Layout.leftMargin: 4
            Layout.rightMargin: 2
            Layout.bottomMargin: 4
            spacing: 6

            Label {
                Layout.fillWidth: true
                text: rail.strings.nav_menu || "Menu"
                color: rail.theme ? rail.theme.text : "#1f2937"
                font.pixelSize: 14
                font.bold: true
                elide: Text.ElideRight
            }
            AppToolButton {
                width: 30
                height: 30
                display: AbstractButton.IconOnly
                icon.source: rail.appRoot
                             ? rail.appRoot.iconPath("cancel") : ""
                icon.width: 14
                icon.height: 14
                Accessible.name: rail.strings.win_close || "Close"
                tipTitle: rail.strings.win_close || "Close"
                onClicked: rail.closeRequested()
            }
        }

        SidebarNavItem {
            objectName: "navItem0"
            Layout.fillWidth: true
            theme: rail.theme
            appRoot: rail.appRoot
            expanded: rail.expanded
            active: rail.currentIndex === 0
            iconName: "download"
            label: rail.strings.tab_single || ""
            tipTitle: rail.strings.tab_single || ""
            tipText: rail.strings.tab_single_tip || ""
            onActivated: rail.activated(0)
        }

        SidebarNavItem {
            objectName: "navItem1"
            Layout.fillWidth: true
            theme: rail.theme
            appRoot: rail.appRoot
            expanded: rail.expanded
            active: rail.currentIndex === 1
            iconName: "file"
            label: rail.strings.tab_downloads || ""
            tipTitle: rail.strings.tab_downloads || ""
            tipText: rail.strings.tab_downloads_tip || ""
            badge: rail.downloadsBadge
            onActivated: rail.activated(1)
        }

        SidebarNavItem {
            objectName: "navItem2"
            Layout.fillWidth: true
            theme: rail.theme
            appRoot: rail.appRoot
            expanded: rail.expanded
            active: rail.currentIndex === 2
            iconName: "package"
            label: rail.strings.tab_compress || ""
            tipTitle: rail.strings.tab_compress || ""
            tipText: rail.strings.tab_compress_tip || ""
            badge: rail.compressionBadge
            onActivated: rail.activated(2)
        }

        Item { Layout.fillHeight: true }

        Rectangle {
            Layout.fillWidth: true
            Layout.topMargin: 4
            Layout.bottomMargin: 4
            height: 1
            color: rail._border
        }

        SidebarNavItem {
            objectName: "navItem3"
            Layout.fillWidth: true
            theme: rail.theme
            appRoot: rail.appRoot
            expanded: rail.expanded
            active: rail.currentIndex === 3
            iconName: "settings"
            label: rail.strings.tab_settings || ""
            tipTitle: rail.strings.tab_settings || ""
            tipText: rail.strings.tab_settings_tip || ""
            onActivated: rail.activated(3)
        }

        SidebarNavItem {
            objectName: "navItem4"
            Layout.fillWidth: true
            theme: rail.theme
            appRoot: rail.appRoot
            expanded: rail.expanded
            active: rail.currentIndex === 4
            iconName: "info"
            label: rail.strings.tab_about || ""
            tipTitle: rail.strings.tab_about || ""
            tipText: rail.strings.tab_about_tip || ""
            onActivated: rail.activated(4)
        }
    }
}
