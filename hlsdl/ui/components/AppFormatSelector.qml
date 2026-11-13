import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: selector
    property var strings: ({})
    spacing: 14
    ButtonGroup { id: fmtGroup }

    Repeater {
        model: [
            { value: "video_audio", label: strings.fmt_video_audio || "Video + audio" },
            { value: "video_only", label: strings.fmt_video_only || "Video only" },
            { value: "audio_only", label: strings.fmt_audio_only || "Audio only" }
        ]
        delegate: AppRadioButton {
            text: modelData.label
            checked: bridge.formatMode === modelData.value
            Binding on checked { value: bridge.formatMode === modelData.value }
            ButtonGroup.group: fmtGroup
            onToggled: if (checked) bridge.setFormatMode(modelData.value)
        }
    }
}
