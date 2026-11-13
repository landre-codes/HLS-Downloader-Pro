import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material

TextField {
    id: hintField
    property string hint: ""
    property string leadingIcon: ""
    property var theme: null
    placeholderText: ""
    Accessible.name: hint
    leftPadding: leadingIcon.length > 0 ? 38 : Material.textFieldHorizontalPadding

    Image {
        x: 12
        anchors.verticalCenter: parent.verticalCenter
        width: 16; height: 16
        visible: hintField.leadingIcon.length > 0
        source: hintField.leadingIcon
        sourceSize.width: 16
        sourceSize.height: 16
        z: 2
    }

    Text {
        x: hintField.leftPadding
        anchors.verticalCenter: parent.verticalCenter
        width: hintField.width - hintField.leftPadding - hintField.rightPadding
        text: hintField.hint
        visible: hintField.text.length === 0
        color: hintField.theme && hintField.theme.textMuted
               ? hintField.theme.textMuted
               : (typeof bridge !== "undefined" && bridge.dark ? "#9aa5af" : "#626b75")
        elide: Text.ElideRight
        font: hintField.font
        z: 1
    }
}
