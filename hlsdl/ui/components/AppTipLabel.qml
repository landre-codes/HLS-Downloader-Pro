import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Label {
    id: tipLabel
    property string tip: ""
    ToolTip.text: tip
    ToolTip.visible: tipHover.hovered
    ToolTip.delay: 500
    HoverHandler { id: tipHover }
}
