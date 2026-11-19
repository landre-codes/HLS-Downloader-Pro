import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

Rectangle {
    id: term
    property string title: ""
    property string output: ""
    property int panelHeight: 150
    property var theme: null
    property var strings: ({})

    Layout.fillWidth: true
    Layout.preferredHeight: panelHeight
    radius: 8
    color: theme ? theme.terminalBg : "#0d1117"
    border.color: theme ? theme.terminalBorder : "#30363d"
    border.width: 1
    clip: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 10
        spacing: 6

        RowLayout {
            Layout.fillWidth: true
            spacing: 6
            Label {
                text: ">_"
                color: term.theme ? term.theme.terminalPrompt : "#27c93f"
                font.family: "monospace"
                font.pixelSize: 12
                font.bold: true
            }
            Label {
                Layout.fillWidth: true
                text: term.title
                color: term.theme ? term.theme.terminalMuted : "#9aa5af"
                font.family: "monospace"
                font.pixelSize: 11
                elide: Text.ElideRight
            }
            AppToolButton {
                display: AbstractButton.IconOnly
                icon.source: "../icons/copy_dark.svg"
                icon.width: 14; icon.height: 14
                enabled: term.output.length > 0
                opacity: enabled ? 1 : 0.4
                Accessible.name: term.strings.terminal_copy || ""
                tipText: term.strings.terminal_copy || ""
                onClicked: {
                    termArea.selectAll()
                    termArea.copy()
                    termArea.deselect()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: term.theme ? term.theme.terminalBorder : "#30363d"
        }

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AsNeeded
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            TextArea {
                id: termArea
                text: term.output
                readOnly: true
                wrapMode: TextEdit.NoWrap
                selectByMouse: true
                color: term.theme ? term.theme.terminalText : "#d6dde5"
                selectionColor: term.theme ? term.theme.terminalSelection : "#264f78"
                selectedTextColor: term.theme ? term.theme.onAccent : "#ffffff"
                font.family: "monospace"
                font.pixelSize: 12
                background: null
            }
        }
    }

    Label {
        anchors.centerIn: parent
        text: term.strings.terminal_empty || ""
        visible: term.output.length === 0
        color: term.theme ? term.theme.terminalMuted : "#9aa5af"
        font.family: "monospace"
        font.pixelSize: 11
        z: 2
    }
}
