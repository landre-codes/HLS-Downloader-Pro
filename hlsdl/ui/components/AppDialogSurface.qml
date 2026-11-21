import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

// Superfície padrão dos diálogos. O cabeçalho é opcional: diálogos antigos que
// não definem `title`/`subtitle` continuam exibindo apenas o conteúdo.
// Quando `dialog` é informado, o cabeçalho move a janela e o canto inferior
// direito redimensiona, sem depender de barras nativas do sistema.
Rectangle {
    id: surface

    property var theme: null
    property var dialog: null
    property var appRoot: null
    property var strings: ({})
    property string title: ""
    property string subtitle: ""
    property string iconSource: ""
    property bool showCloseButton: false
    property string closeText: ""
    property bool draggable: true
    property bool resizable: false
    property int minDialogWidth: 380
    property int minDialogHeight: 260
    property int contentSpacing: 10
    property int contentMargin: 16
    property bool maximized: false

    readonly property bool hasHeader: title.length > 0
                                       || subtitle.length > 0
                                       || iconSource.toString().length > 0
    readonly property color _windowBg: theme ? theme.windowBg
                                             : (typeof bridge !== "undefined" && bridge.dark
                                                ? "#111923" : "#f3f6fb")
    readonly property color _text: theme ? theme.text : "#1f2937"
    readonly property color _textSecondary: theme ? theme.textSecondary : "#4f5862"
    readonly property color _border: theme ? theme.cardBorder : "#d8e1ee"
    readonly property color _heroFrom: theme ? theme.heroFrom : "#eaf4ff"
    readonly property color _heroTo: theme ? theme.heroTo : "#ffffff"
    readonly property color _heroBorder: theme ? theme.heroBorder : "#cfe0f2"
    readonly property color _accent: theme ? theme.accentFill : "#2563eb"

    property real _restoreX: 0
    property real _restoreY: 0
    property real _restoreWidth: 0
    property real _restoreHeight: 0

    function toggleMaximized() {
        if (!dialog)
            return
        if (maximized) {
            restoreGeometry()
            return
        }
        _restoreX = dialog.x
        _restoreY = dialog.y
        _restoreWidth = dialog.width
        _restoreHeight = dialog.height
        maximized = true
        dialog.x = 0
        dialog.y = 0
        if (appRoot) {
            dialog.width = appRoot.width
            dialog.height = appRoot.height
        }
    }

    function restoreGeometry() {
        if (!dialog || !maximized)
            return
        dialog.x = _restoreX
        dialog.y = _restoreY
        dialog.width = _restoreWidth
        dialog.height = _restoreHeight
        maximized = false
    }

    color: _windowBg
    radius: 12
    border.width: 1
    border.color: _border
    clip: true
    implicitWidth: 420
    implicitHeight: (hasHeader ? header.height : 0)
                    + bodyColumn.implicitHeight + contentMargin * 2
    default property alias content: bodyColumn.data

    Connections {
        target: surface.dialog
        ignoreUnknownSignals: true
        function onClosed() {
            if (surface.maximized)
                surface.restoreGeometry()
        }
    }

    // ------------------------------------------------------------- cabeçalho
    Rectangle {
        id: header
        visible: surface.hasHeader
        height: visible ? headerLayout.implicitHeight + 24 : 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        clip: true
        // O gradiente acompanha o raio da janela apenas nos cantos superiores.
        topLeftRadius: surface.radius
        topRightRadius: surface.radius
        bottomLeftRadius: 0
        bottomRightRadius: 0
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0.0; color: surface._heroFrom }
            GradientStop { position: 1.0; color: surface._heroTo }
        }

        // Brilho decorativo, no mesmo vocabulário visual do PageHero.
        Rectangle {
            width: 170
            height: 170
            radius: 85
            x: header.width - 96
            y: -104
            color: surface._accent
            opacity: 0.07
        }
        Rectangle {
            width: 4
            height: Math.max(0, header.height - 20)
            radius: 2
            anchors.left: parent.left
            anchors.leftMargin: 10
            anchors.verticalCenter: parent.verticalCenter
            color: surface._accent
        }

        MouseArea {
            id: dragArea
            anchors.fill: parent
            acceptedButtons: Qt.LeftButton
            cursorShape: (surface.draggable && surface.dialog)
                         ? Qt.SizeAllCursor : Qt.ArrowCursor
            property real pressX: 0
            property real pressY: 0
            property real startX: 0
            property real startY: 0

            onPressed: function(mouse) {
                if (!surface.draggable || !surface.dialog)
                    return
                var point = mapToItem(surface.dialog.parent, mouse.x, mouse.y)
                pressX = point.x
                pressY = point.y
                startX = surface.dialog.x
                startY = surface.dialog.y
            }
            onPositionChanged: function(mouse) {
                if (!pressed || !surface.draggable || !surface.dialog)
                    return
                var point = mapToItem(surface.dialog.parent, mouse.x, mouse.y)
                var nextX = startX + (point.x - pressX)
                var nextY = startY + (point.y - pressY)
                var maxX = surface.appRoot
                           ? Math.max(0, surface.appRoot.width - surface.dialog.width)
                           : nextX
                var maxY = surface.appRoot
                           ? Math.max(0, surface.appRoot.height - surface.dialog.height)
                           : nextY
                surface.dialog.x = Math.max(0, Math.min(maxX, nextX))
                surface.dialog.y = Math.max(0, Math.min(maxY, nextY))
            }
        }

        RowLayout {
            id: headerLayout
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 12
            anchors.topMargin: 12
            anchors.bottomMargin: 12
            spacing: 12

            Rectangle {
                Layout.preferredWidth: 40
                Layout.preferredHeight: 40
                Layout.alignment: Qt.AlignVCenter
                radius: 10
                color: surface.theme ? surface.theme.cardBg : "#ffffff"
                border.width: 1
                border.color: surface._heroBorder
                Image {
                    anchors.centerIn: parent
                    visible: source.toString().length > 0
                    source: surface.iconSource
                    sourceSize.width: 20
                    sourceSize.height: 20
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 2
                Label {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: surface.title
                    color: surface._text
                    font.pixelSize: 22
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                    clip: true
                }
                Label {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    visible: text.length > 0
                    text: surface.subtitle
                    color: surface._textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.Wrap
                    maximumLineCount: 2
                    elide: Text.ElideRight
                    clip: true
                }
            }

            Row {
                Layout.alignment: Qt.AlignTop
                spacing: 2

                AppToolButton {
                    visible: surface.resizable
                    width: 30
                    height: 30
                    display: AbstractButton.TextOnly
                    text: surface.maximized ? "\u274F" : "\u26F6"
                    font.pixelSize: 13
                    Accessible.name: surface.maximized
                                     ? (surface.strings.dialog_restore || "Restore")
                                     : (surface.strings.dialog_expand || "Maximize")
                    tipTitle: surface.maximized
                              ? (surface.strings.dialog_restore || "Restore")
                              : (surface.strings.dialog_expand || "Maximize")
                    tipText: surface.strings.dialog_resize_tip || ""
                    onClicked: surface.toggleMaximized()
                }
                AppToolButton {
                    objectName: "dialogCloseButton"
                    visible: surface.showCloseButton
                    width: 30
                    height: 30
                    display: AbstractButton.IconOnly
                    danger: true
                    icon.source: surface.appRoot
                                 ? surface.appRoot.iconPath("cancel") : ""
                    icon.width: 15
                    icon.height: 15
                    Accessible.name: surface.closeText.length > 0
                                     ? surface.closeText
                                     : (surface.strings.dlg_error_close || "Close")
                    tipTitle: surface.closeText.length > 0
                              ? surface.closeText
                              : (surface.strings.dlg_error_close || "Close")
                    tipText: surface.closeText
                    onClicked: if (surface.dialog) surface.dialog.close()
                }
            }
        }
    }

    // --------------------------------------------------------------- conteúdo
    ColumnLayout {
        id: bodyColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: header.visible ? header.bottom : parent.top
        anchors.bottom: parent.bottom
        anchors.margins: surface.contentMargin
        spacing: surface.contentSpacing
    }

    // ---------------------------------------------------------- redimensionar
    Item {
        id: resizeGrip
        visible: surface.resizable && surface.dialog !== null
        width: 20
        height: 20
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        z: 20

        // Três traços diagonais: um único traço parecia uma scrollbar.
        Canvas {
            id: gripCanvas
            anchors.fill: parent
            property color strokeColor: surface._textSecondary
            onStrokeColorChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = strokeColor
                ctx.globalAlpha = 0.68
                ctx.lineWidth = 1.4
                ctx.lineCap = "round"
                for (var i = 0; i < 3; i++) {
                    var offset = 4 + i * 4
                    ctx.beginPath()
                    ctx.moveTo(width - offset, height - 2)
                    ctx.lineTo(width - 2, height - offset)
                    ctx.stroke()
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.SizeFDiagCursor
            Accessible.name: surface.strings.dialog_resize_tip || "Resize"
            property real pressX: 0
            property real pressY: 0
            property real startWidth: 0
            property real startHeight: 0

            onPressed: function(mouse) {
                if (!surface.dialog)
                    return
                var point = mapToItem(surface.dialog.parent, mouse.x, mouse.y)
                pressX = point.x
                pressY = point.y
                startWidth = surface.dialog.width
                startHeight = surface.dialog.height
            }
            onPositionChanged: function(mouse) {
                if (!pressed || !surface.dialog)
                    return
                var point = mapToItem(surface.dialog.parent, mouse.x, mouse.y)
                var maxWidth = surface.appRoot
                               ? Math.max(surface.minDialogWidth,
                                          surface.appRoot.width - surface.dialog.x)
                               : surface.dialog.width
                var maxHeight = surface.appRoot
                                ? Math.max(surface.minDialogHeight,
                                           surface.appRoot.height - surface.dialog.y)
                                : surface.dialog.height
                surface.dialog.width = Math.max(
                    surface.minDialogWidth,
                    Math.min(maxWidth, startWidth + point.x - pressX))
                surface.dialog.height = Math.max(
                    surface.minDialogHeight,
                    Math.min(maxHeight, startHeight + point.y - pressY))
            }
        }
    }
}
