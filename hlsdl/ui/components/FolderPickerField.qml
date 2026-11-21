import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Item {
    id: root
    property var theme: null
    property string label: ""
    property string path: ""
    property string changeText: ""
    property string openText: ""
    property string copyText: ""
    property string folderIcon: ""
    property string copyIcon: ""
    property string changeIcon: ""
    property string openIcon: ""
    property string changeTip: ""
    property string openTip: ""

    signal changeRequested()
    signal openRequested()
    signal copyRequested()

    implicitHeight: layout.implicitHeight

    ColumnLayout {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        spacing: 6

        Label {
            text: root.label
            visible: text.length > 0
            font.pixelSize: 14
            color: root.theme ? root.theme.textSecondary : "#4f5862"
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                id: pathBox
                Layout.fillWidth: true
                Layout.minimumWidth: 160
                implicitHeight: 44
                radius: 6
                color: root.theme ? root.theme.inputBg : "#e9eef2"
                border.width: 1
                border.color: root.theme ? root.theme.inputBorder : "#c6d0d8"

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 10
                    anchors.rightMargin: 10
                    spacing: 8
                    Image {
                        visible: root.folderIcon.length > 0
                        source: root.folderIcon
                        sourceSize.width: 16
                        sourceSize.height: 16
                    }
                    Label {
                        Layout.fillWidth: true
                        text: root.path
                        color: root.theme ? root.theme.text : "#1f2937"
                        font.pixelSize: 13
                        elide: Text.ElideMiddle
                    }
                }
                HoverHandler {
                    id: pathHover
                    cursorShape: Qt.IBeamCursor
                }
                AppToolTip {
                    target: pathBox
                    title: root.label
                    text: root.path
                    available: root.path.length > 0
                    delay: 400
                }
            }

            AppButton {
                text: root.changeText
                variant: "secondary"
                icon.source: root.changeIcon
                icon.width: 18
                icon.height: 18
                display: AbstractButton.TextBesideIcon
                tipTitle: root.changeText
                tipText: root.changeTip.length > 0 ? root.changeTip : root.path
                onClicked: root.changeRequested()
            }
            AppButton {
                text: root.openText
                variant: "secondary"
                icon.source: root.openIcon
                icon.width: 18
                icon.height: 18
                display: AbstractButton.TextBesideIcon
                tipTitle: root.openText
                tipText: root.openTip.length > 0 ? root.openTip : root.path
                onClicked: root.openRequested()
            }
            AppButton {
                text: ""
                variant: "tertiary"
                display: AbstractButton.IconOnly
                icon.source: root.copyIcon
                icon.width: 16
                icon.height: 16
                Accessible.name: root.copyText
                tipTitle: root.copyText
                tipText: root.path
                onClicked: root.copyRequested()
            }
        }
    }
}

