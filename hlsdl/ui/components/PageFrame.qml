import QtQuick

// Moldura de página para transições de entrada em estilo card.
// Mantém a página viva; apenas desloca/opacifica a moldura.
Item {
    id: frame

    property real enterOffset: 0
    opacity: 1
    transform: Translate { x: frame.enterOffset }

    function reveal(direction) {
        // A transição é aplicada apenas quando a janela está em um backend
        // gráfico real. O plugin offscreen (testes) não cria animações vivas.
        if (Qt.platform && Qt.platform.pluginName === "offscreen") {
            enterOffset = 0
            opacity = 1
            return
        }
        enterOffset = (direction || 1) * 28
        opacity = 0.92
        slide.restart()
        fade.restart()
    }

    Component.onDestruction: {
        slide.stop()
        fade.stop()
    }

    NumberAnimation {
        id: slide
        target: frame
        property: "enterOffset"
        to: 0
        duration: 190
        easing.type: Easing.OutCubic
    }
    NumberAnimation {
        id: fade
        target: frame
        property: "opacity"
        to: 1
        duration: 170
        easing.type: Easing.OutCubic
    }
}
