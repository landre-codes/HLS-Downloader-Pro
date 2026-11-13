import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
    property var strings: ({})
    property var items: [
        { text: strings.codec_copy || "Original", value: "copy" },
        { text: strings.codec_h264 || "H.264", value: "h264" },
        { text: strings.codec_h265 || "H.265", value: "h265" }
    ]
    model: items
    textRole: "text"
    valueRole: "value"
    currentIndex: {
        for (var i = 0; i < items.length; i++)
            if (items[i].value === bridge.codec)
                return i
        return 0
    }
    onActivated: bridge.setCodec(currentValue)
    Layout.preferredWidth: 210
    ToolTip.text: strings.codec_keep_original || ""
    ToolTip.visible: hovered
    ToolTip.delay: 500
}
