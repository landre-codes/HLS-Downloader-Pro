import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

TextArea {
    id: hintArea
    property string hint: ""
    property var theme: null
    placeholderText: ""
    Accessible.name: hint
    topPadding: 8
    bottomPadding: 8
    leftPadding: 12
    rightPadding: 12

    Text {
        x: hintArea.leftPadding
        y: hintArea.topPadding
        width: hintArea.width - hintArea.leftPadding - hintArea.rightPadding
        text: hintArea.hint
        visible: hintArea.text.length === 0
        color: hintArea.theme && hintArea.theme.textMuted
               ? hintArea.theme.textMuted
               : (typeof bridge !== "undefined" && bridge.dark ? "#9aa5af" : "#626b75")
        wrapMode: Text.WordWrap
        font: hintArea.font
        z: 1
    }
}
