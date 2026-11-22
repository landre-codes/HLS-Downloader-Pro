import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Tooltip rico e reutilizável.
//
// Diferente do ToolTip anexado padrão, aceita título, descrição longa,
// atalho de teclado e ícone. O posicionamento é calculado em coordenadas de
// cena (por isso o popup vive no Overlay), com flip automático para baixo
// quando não há espaço acima do alvo. Também abre por foco de teclado, para
// que a informação não dependa do mouse.
Popup {
    id: tip
    objectName: "appToolTip"

    property Item target: null
    property string title: ""
    property string text: ""
    property string shortcut: ""
    property string footer: ""
    property string iconSource: ""
    property bool available: true
    property bool showOnFocus: true
    property int delay: 450
    // Tooltip aberto por foco não pode ficar preso depois que o alvo perde e
    // recupera o foco (ex.: fechar um diálogo devolve o foco ao botão).
    property int focusHideDelay: 3500
    property bool _openedByFocus: false
    // Distingue navegação por Tab (o tooltip já foi mostrado) de uma ação que
    // abriu um diálogo (pressionou o botão; o próximo foco é restauração).
    property bool _focusScheduled: false
    property bool _focusTipShown: false
    property int minWidth: 190
    property int maxWidth: 380
    property var theme: null

    readonly property bool darkTheme: theme && theme.dark !== undefined
                                      ? theme.dark
                                      : (typeof bridge !== "undefined" && bridge.dark)
    readonly property string effectiveTitle: {
        if (title.length > 0)
            return title
        // Só usa o texto do controle como título quando existe um detalhe
        // explícito; caso contrário o tooltip seria apenas o rótulo repetido.
        if (text.length === 0 && shortcut.length === 0 && footer.length === 0)
            return ""
        var targetText = target ? target["text"] : undefined
        if (targetText !== undefined && String(targetText).length > 0)
            return String(targetText)
        return ""
    }
    readonly property string effectiveText: text.length > 0 && text !== effectiveTitle
                                           ? text : ""
    readonly property bool hasContent: effectiveTitle.length > 0
                                       || effectiveText.length > 0
                                       || shortcut.length > 0

    readonly property color surfaceColor: darkTheme ? "#232b33" : "#ffffff"
    readonly property color borderColor: darkTheme ? "#4b5966" : "#c6d0d9"
    readonly property color titleColor: darkTheme ? "#e6eef7" : "#1f2937"
    readonly property color bodyColor: darkTheme ? "#d3dbe2" : "#3f4852"
    readonly property color mutedColor: darkTheme ? "#a8b3bd" : "#5b6570"
    readonly property color accentColor: darkTheme ? "#93c5fd" : "#1d4ed8"
    readonly property color shortcutBg: darkTheme ? "#304152" : "#e6edf7"

    parent: Overlay.overlay
    popupType: Popup.Item
    focus: false
    modal: false
    dim: false
    padding: 0
    closePolicy: Popup.CloseOnPressOutside | Popup.CloseOnEscape
    z: 10000

    width: {
        var titleWidth = titleMetrics.advanceWidth + (iconSource.length > 0 ? 26 : 0)
        var shortcutWidth = shortcut.length > 0 ? shortcutMetrics.advanceWidth + 26 : 0
        var bodyWidth = bodyMetrics.advanceWidth
        var desired = Math.max(titleWidth + shortcutWidth, bodyWidth)
        return Math.min(maxWidth, Math.max(minWidth, desired + 26))
    }
    height: contentColumn.implicitHeight + 20

    function schedule(focusOnly) {
        if (!available || !hasContent || target === null)
            return
        _openedByFocus = focusOnly === true
        if (focusOnly === true)
            _focusScheduled = true
        showTimer.restart()
    }

    function cancelFocusAutoHide() {
        _openedByFocus = false
        focusHideTimer.stop()
    }

    function hideNow() {
        showTimer.stop()
        focusHideTimer.stop()
        if (opened)
            close()
    }

    function openTip() {
        if (!available || !hasContent || target === null || !target.visible)
            return
        open()
        reposition()
        Qt.callLater(reposition)
        if (_openedByFocus) {
            _focusTipShown = true
            if (!targetHover.hovered)
                focusHideTimer.restart()
        } else {
            focusHideTimer.stop()
        }
    }

    function reposition() {
        if (target === null || tip.parent === null || tip.width <= 0)
            return
        var overlayItem = tip.parent
        var point = target.mapToItem(overlayItem, 0, 0)
        var x = point.x + (target.width - tip.width) / 2
        var y = point.y - tip.height - 8
        if (y < 8)
            y = point.y + target.height + 8
        x = Math.max(8, Math.min(x, overlayItem.width - tip.width - 8))
        y = Math.max(8, Math.min(y, overlayItem.height - tip.height - 8))
        tip.x = x
        tip.y = y
    }

    onWidthChanged: reposition()
    onHeightChanged: reposition()
    onOpened: reposition()
    onClosed: focusHideTimer.stop()

    Timer {
        id: showTimer
        interval: tip.delay
        onTriggered: tip.openTip()
    }

    Timer {
        id: focusHideTimer
        objectName: "tooltipFocusHideTimer"
        interval: tip.focusHideDelay
        onTriggered: tip.hideNow()
    }

    HoverHandler {
        id: targetHover
        enabled: tip.target !== null
        parent: tip.target
        onHoveredChanged: {
            if (hovered) {
                tip.cancelFocusAutoHide()
                tip.schedule()
            } else {
                tip.hideNow()
            }
        }
    }

    Connections {
        target: tip.target
        ignoreUnknownSignals: true
        function onActiveFocusChanged() {
            if (tip.target === null)
                return
            if (tip.target.activeFocus && tip.showOnFocus) {
                // Um tooltip agendado que nunca chegou a abrir (pressed ou
                // diálogo) não deve reaparecer quando o foco é restaurado.
                if (tip._focusScheduled && !tip._focusTipShown) {
                    tip._focusScheduled = false
                    tip.hideNow()
                    return
                }
                tip.schedule(true)
            } else if (!tip.target.activeFocus) {
                tip.hideNow()
            }
        }
        function onPressedChanged() {
            if (tip.target !== null && tip.target["pressed"]) {
                // A ação consome o tooltip daquela sessão de foco; se um
                // diálogo abrir e fechar, o foco restaurado não o reabre.
                tip._focusTipShown = false
                tip.hideNow()
            }
        }
        function onVisibleChanged() {
            if (tip.target !== null && !tip.target.visible)
                tip.hideNow()
        }
    }

    TextMetrics {
        id: titleMetrics
        font: titleText.font
        text: tip.effectiveTitle
    }
    TextMetrics {
        id: shortMetrics
        font: bodyText.font
        text: tip.effectiveText
    }
    TextMetrics {
        id: bodyMetrics
        font: bodyText.font
        text: shortMetrics.advanceWidth > tip.maxWidth - 26
              ? tip.effectiveText.substring(0, 64)
              : tip.effectiveText
    }
    TextMetrics {
        id: shortcutMetrics
        font: shortcutText.font
        text: tip.shortcut
    }

    background: Rectangle {
        radius: 7
        color: tip.surfaceColor
        border.width: 1
        border.color: tip.borderColor
    }

    contentItem: Item {
        id: contentHost
        implicitWidth: contentColumn.implicitWidth
        implicitHeight: contentColumn.implicitHeight

        ColumnLayout {
            id: contentColumn
            objectName: "tooltipContentColumn"
            anchors.centerIn: parent
            width: tip.width - 20
            spacing: 5

            Item {
                Layout.fillWidth: true
                visible: tip.effectiveTitle.length > 0 || tip.shortcut.length > 0
                implicitHeight: Math.max(titleText.implicitHeight,
                                         shortcutBadge.visible ? shortcutBadge.height : 0,
                                         iconImage.visible ? 16 : 0)

                Image {
                    id: iconImage
                    visible: tip.iconSource.length > 0
                    source: tip.iconSource
                    sourceSize.width: 16
                    sourceSize.height: 16
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    id: titleText
                    objectName: "tipTitleText"
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.verticalCenter: parent.verticalCenter
                    visible: tip.effectiveTitle.length > 0
                    width: Math.max(0, Math.min(implicitWidth,
                        parent.width
                        - (shortcutBadge.visible ? shortcutBadge.width * 2 + 16 : 8)
                        - (iconImage.visible ? 2 * (iconImage.width + 8) : 0)))
                    text: tip.effectiveTitle
                    color: tip.titleColor
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    wrapMode: Text.WrapAnywhere
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                }

                Rectangle {
                    id: shortcutBadge
                    visible: tip.shortcut.length > 0
                    implicitWidth: shortcutText.implicitWidth + 12
                    implicitHeight: 20
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    radius: 4
                    color: tip.shortcutBg
                    border.width: 1
                    border.color: tip.borderColor
                    Text {
                        id: shortcutText
                        anchors.centerIn: parent
                        text: tip.shortcut
                        color: tip.mutedColor
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                    }
                }
            }

            Text {
                id: bodyText
                objectName: "tipBodyText"
                Layout.fillWidth: true
                visible: tip.effectiveText.length > 0
                text: tip.effectiveText
                color: tip.bodyColor
                font.pixelSize: 12
                lineHeight: 1.15
                wrapMode: Text.WrapAnywhere
                textFormat: Text.PlainText
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Text {
                id: footerText
                objectName: "tipFooterText"
                Layout.fillWidth: true
                visible: tip.footer.length > 0
                text: tip.footer
                color: tip.mutedColor
                font.pixelSize: 11
                wrapMode: Text.WrapAnywhere
                textFormat: Text.PlainText
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
    }
}
