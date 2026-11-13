import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ComboBox {
    property var strings: ({})
    property var items: [
        { text: strings.q_best || "Best", value: "best" },
        { text: "2160p (4K)", value: "2160" },
        { text: "1440p (2K)", value: "1440" },
        { text: "1080p", value: "1080" },
        { text: "720p", value: "720" },
        { text: "480p", value: "480" },
        { text: "360p", value: "360" },
        { text: "240p", value: "240" },
        { text: "144p", value: "144" }
    ]
    model: items
    textRole: "text"
    valueRole: "value"
    currentIndex: {
        for (var i = 0; i < items.length; i++)
            if (items[i].value === bridge.quality)
                return i
        return 0
    }
    onActivated: bridge.setQuality(currentValue)
    Layout.preferredWidth: 170
}
