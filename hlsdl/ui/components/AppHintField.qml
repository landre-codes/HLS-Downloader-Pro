import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

TextField {
    id: hintField
    property string hint: ""
    property string leadingIcon: ""
    property var theme: null
    property var strings: ({})
    property string tipTitle: ""
    property string tipText: ""
    property string tipShortcut: ""
    property bool tipEnabled: true
    property bool showClearButton: true
    readonly property bool _hasClearButton: showClearButton && enabled
                                            && text.length > 0
    placeholderText: ""
    Accessible.name: hint
    clip: true
    topPadding: 8
    bottomPadding: 8
    leftPadding: leadingIcon.length > 0 ? 38 : Material.textFieldHorizontalPadding
    rightPadding: _hasClearButton ? 32 : Material.textFieldHorizontalPadding

    function clearField() {
        clear()
        forceActiveFocus()
    }

    Keys.onEscapePressed: function(event) {
        if (text.length > 0) {
            clearField()
            event.accepted = true
        } else {
            event.accepted = false
        }
    }

    background: Rectangle {
        anchors.fill: parent
        implicitHeight: 56
        radius: 4
        color: hintField.theme ? hintField.theme.inputBg
                               : (typeof bridge !== "undefined" && bridge.dark
                                  ? "#14191e" : "#e9eef2")
        border.width: 1
        border.color: hintField.activeFocus
                      ? (hintField.theme ? hintField.theme.accentText
                                         : (typeof bridge !== "undefined" && bridge.dark
                                            ? "#93c5fd" : "#1d4ed8"))
                      : (hintField.theme ? hintField.theme.inputBorder
                                         : (typeof bridge !== "undefined" && bridge.dark
                                            ? "#3d4a55" : "#c6d0d8"))
    }

    AppToolTip {
        target: hintField
        title: hintField.tipTitle
        text: hintField.tipText.length > 0 ? hintField.tipText : hintField.hint
        shortcut: hintField.tipShortcut
        available: hintField.tipEnabled && hintField.enabled
                   && (hintField.tipText.length > 0 || hintField.text.length === 0)
    }

    Image {
        objectName: "hintFieldLeadingIcon"
        x: 12
        y: hintField.cursorRectangle.y
           + (hintField.cursorRectangle.height - height) / 2
        width: 16; height: 16
        visible: hintField.leadingIcon.length > 0
        source: hintField.leadingIcon
        sourceSize.width: 16
        sourceSize.height: 16
        z: 2
    }

    // Mesma linha de base do cursor: o placeholder do Material flutua sobre
    // o campo, então o hint é desenhado na geometria exata do texto digitado.
    Text {
        objectName: "hintFieldPlaceholder"
        x: hintField.leftPadding
        y: hintField.cursorRectangle.y
        width: Math.max(0, hintField.width - hintField.leftPadding
                        - hintField.rightPadding)
        height: hintField.cursorRectangle.height
        text: hintField.hint
        visible: hintField.text.length === 0
        color: hintField.theme && hintField.theme.textMuted
               ? hintField.theme.textMuted
               : (typeof bridge !== "undefined" && bridge.dark
                  ? "#9aa5af" : "#626b75")
        elide: Text.ElideRight
        verticalAlignment: Text.AlignVCenter
        font: hintField.font
        z: 1
    }

    AppToolButton {
        objectName: "hintFieldClearButton"
        visible: hintField._hasClearButton
        anchors.right: parent.right
        anchors.rightMargin: 3
        anchors.verticalCenter: parent.verticalCenter
        width: 24
        height: 24
        display: AbstractButton.TextOnly
        text: "\u00d7"
        font.pixelSize: 16
        font.weight: Font.Medium
        danger: true
        focusPolicy: Qt.NoFocus
        z: 4
        Accessible.name: hintField.strings.btn_clear || "Clear field"
        tipTitle: hintField.strings.btn_clear || "Clear field"
        tipText: hintField.strings.btn_clear_tip || ""
        tipShortcut: "Esc"
        onClicked: hintField.clearField()
    }

    // Substitui o menu nativo (em inglês) pelo catálogo da UI.
    Menu {
        id: contextMenu
        objectName: "hintFieldContextMenu"
        popupType: Popup.Item
        padding: 6
        background: Rectangle {
            implicitWidth: 200
            radius: 6
            readonly property bool _dark: typeof bridge !== "undefined" && bridge.dark
            color: hintField.theme ? hintField.theme.cardBg
                                   : (_dark ? "#1b2633" : "#ffffff")
            border.width: 1
            border.color: hintField.theme ? hintField.theme.cardBorder
                                          : (_dark ? "#304152" : "#d8e1ee")
        }
        MenuItem {
            text: hintField.strings.menu_undo || "Undo"
            enabled: hintField.canUndo
            onTriggered: hintField.undo()
        }
        MenuItem {
            text: hintField.strings.menu_redo || "Redo"
            enabled: hintField.canRedo
            onTriggered: hintField.redo()
        }
        MenuSeparator {}
        MenuItem {
            text: hintField.strings.menu_cut || "Cut"
            enabled: hintField.selectedText.length > 0
            onTriggered: hintField.cut()
        }
        MenuItem {
            text: hintField.strings.menu_copy || "Copy"
            enabled: hintField.selectedText.length > 0
            onTriggered: hintField.copy()
        }
        MenuItem {
            text: hintField.strings.menu_paste || "Paste"
            enabled: hintField.canPaste
            onTriggered: hintField.paste()
        }
        MenuItem {
            text: hintField.strings.menu_delete || "Delete"
            enabled: hintField.selectedText.length > 0
            onTriggered: hintField.remove(hintField.selectionStart,
                                          hintField.selectionEnd)
        }
        MenuSeparator {}
        MenuItem {
            text: hintField.strings.menu_select_all || "Select all"
            enabled: hintField.length > 0
            onTriggered: hintField.selectAll()
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        z: 3
        onPressed: function(mouse) {
            hintField.forceActiveFocus()
            contextMenu.x = mouse.x
            contextMenu.y = mouse.y
            contextMenu.open()
        }
    }
}
