import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

// Área de texto multilinha com viewport próprio. O TextArea interno cresce
// com o conteúdo; o Flickable mantém o cursor visível e impede que o texto
// invada a página ao pressionar Enter dezenas de vezes.
Rectangle {
    id: root

    property string hint: ""
    property var theme: null
    property var strings: ({})
    property bool showClearButton: true
    property alias text: area.text
    property alias cursorPosition: area.cursorPosition
    property alias readOnly: area.readOnly
    property alias wrapMode: area.wrapMode
    property alias selectByMouse: area.selectByMouse
    readonly property bool _hasClearButton: showClearButton && enabled
                                            && area.text.length > 0

    Accessible.name: hint
    implicitHeight: 56
    radius: 6
    clip: true
    color: theme ? theme.inputBg
                 : (typeof bridge !== "undefined" && bridge.dark
                    ? "#14191e" : "#e9eef2")
    border.width: 1
    border.color: area.activeFocus
                  ? (theme ? theme.accentText
                           : (typeof bridge !== "undefined" && bridge.dark
                              ? "#93c5fd" : "#1d4ed8"))
                  : (theme ? theme.inputBorder
                           : (typeof bridge !== "undefined" && bridge.dark
                              ? "#3d4a55" : "#c6d0d8"))

    function clear() {
        area.clear()
    }

    function clearField() {
        area.clear()
        area.forceActiveFocus()
    }

    function ensureCursorVisible() {
        var caretTop = area.cursorRectangle.y
        var caretBottom = caretTop + area.cursorRectangle.height
        var viewTop = flick.contentY
        var viewBottom = viewTop + flick.height
        if (caretTop < viewTop + 4) {
            flick.contentY = Math.max(0, caretTop - 4)
        } else if (caretBottom > viewBottom - 4) {
            flick.contentY = Math.min(
                Math.max(0, flick.contentHeight - flick.height),
                caretBottom - flick.height + 4)
        }
    }

    onHeightChanged: ensureCursorVisible()

    Flickable {
        id: flick
        objectName: "hintAreaFlickable"
        anchors.fill: parent
        clip: true
        contentWidth: width
        contentHeight: Math.max(height, area.height)
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        onContentHeightChanged: root.ensureCursorVisible()

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }

        TextArea {
            id: area
            objectName: "hintAreaTextArea"
            y: 0
            width: Math.max(0, flick.width - 16)
            height: Math.max(flick.height,
                             contentHeight + topPadding + bottomPadding)
            topPadding: 8
            bottomPadding: 8
            leftPadding: 12
            rightPadding: root._hasClearButton ? 38 : 12
            color: root.theme ? root.theme.text
                               : (typeof bridge !== "undefined" && bridge.dark
                                  ? "#e6eef7" : "#1f2937")
            placeholderText: ""
            background: null
            selectByMouse: true
            wrapMode: TextEdit.Wrap
            Accessible.name: root.hint
            onCursorRectangleChanged: root.ensureCursorVisible()

            Keys.onEscapePressed: function(event) {
                if (text.length > 0) {
                    root.clearField()
                    event.accepted = true
                } else {
                    event.accepted = false
                }
            }
        }
    }

    // Placeholder do campo multilinha: sempre no canto superior esquerdo.
    Text {
        objectName: "hintAreaPlaceholder"
        x: area.leftPadding
        y: area.topPadding
        width: Math.max(0, root.width - area.leftPadding
                        - (root._hasClearButton ? 38 : 12) - 16)
        text: root.hint
        visible: area.text.length === 0
        color: root.theme && root.theme.textMuted
               ? root.theme.textMuted
               : (typeof bridge !== "undefined" && bridge.dark
                  ? "#9aa5af" : "#626b75")
        wrapMode: Text.WordWrap
        font: area.font
        z: 1
    }

    AppToolButton {
        objectName: "hintAreaClearButton"
        visible: root._hasClearButton
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.rightMargin: 18
        anchors.topMargin: 4
        width: 24
        height: 24
        display: AbstractButton.TextOnly
        text: "\u00d7"
        font.pixelSize: 16
        font.weight: Font.Medium
        danger: true
        focusPolicy: Qt.NoFocus
        z: 4
        Accessible.name: root.strings.btn_clear || "Clear field"
        tipTitle: root.strings.btn_clear || "Clear field"
        tipText: root.strings.btn_clear_tip || ""
        tipShortcut: "Esc"
        onClicked: root.clearField()
    }

    // O menu nativo do Qt usa os catálogos internos do Qt e aparece em inglês
    // quando eles não estão instalados. Este menu usa o mesmo i18n da UI.
    Menu {
        id: contextMenu
        objectName: "hintAreaContextMenu"
        popupType: Popup.Item
        padding: 6
        background: Rectangle {
            implicitWidth: 200
            radius: 6
            readonly property bool _dark: typeof bridge !== "undefined" && bridge.dark
            color: root.theme ? root.theme.cardBg
                              : (_dark ? "#1b2633" : "#ffffff")
            border.width: 1
            border.color: root.theme ? root.theme.cardBorder
                                     : (_dark ? "#304152" : "#d8e1ee")
        }
        MenuItem {
            text: root.strings.menu_undo || "Undo"
            enabled: area.canUndo
            onTriggered: area.undo()
        }
        MenuItem {
            text: root.strings.menu_redo || "Redo"
            enabled: area.canRedo
            onTriggered: area.redo()
        }
        MenuSeparator {}
        MenuItem {
            text: root.strings.menu_cut || "Cut"
            enabled: area.selectedText.length > 0
            onTriggered: area.cut()
        }
        MenuItem {
            text: root.strings.menu_copy || "Copy"
            enabled: area.selectedText.length > 0
            onTriggered: area.copy()
        }
        MenuItem {
            text: root.strings.menu_paste || "Paste"
            enabled: area.canPaste
            onTriggered: area.paste()
        }
        MenuItem {
            text: root.strings.menu_delete || "Delete"
            enabled: area.selectedText.length > 0
            onTriggered: area.remove(area.selectionStart, area.selectionEnd)
        }
        MenuSeparator {}
        MenuItem {
            text: root.strings.menu_select_all || "Select all"
            enabled: area.length > 0
            onTriggered: area.selectAll()
        }
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        z: 3
        onPressed: function(mouse) {
            area.forceActiveFocus()
            contextMenu.x = mouse.x
            contextMenu.y = mouse.y
            contextMenu.open()
        }
    }
}
