import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

ComboBox {
    property var items: bridge.formatMode === "audio_only"
        ? ["mp3", "m4a", "wav", "flac", "opus"]
        : ["mp4", "mkv", "webm", "avi", "mov"]
    model: items
    currentIndex: Math.max(0, items.indexOf(bridge.container))
    onActivated: bridge.setContainer(currentText)
    Layout.preferredWidth: 110
}
