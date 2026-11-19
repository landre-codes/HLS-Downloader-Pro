import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

Label {
    id: tipLabel
    property string tip: ""
    property string tipTitle: ""
    HoverHandler { id: tipHover }
    AppToolTip {
        target: tipLabel
        title: tipLabel.tipTitle
        text: tipLabel.tip
        available: tipLabel.tip.length > 0
    }
}
