import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts

AppComboBox {
    property var strings: ({})
    property var items: [
        { text: strings.compress_light || "Light", value: "light" },
        { text: strings.compress_medium || "Medium", value: "medium" },
        { text: strings.compress_strong || "Strong", value: "strong" }
    ]
    model: items
    textRole: "text"
    valueRole: "value"
    currentIndex: {
        for (var i = 0; i < items.length; i++)
            if (items[i].value === bridge.compressLevel)
                return i
        return 1
    }
    onActivated: bridge.setCompressLevel(currentValue)
    Layout.preferredWidth: 150
}
