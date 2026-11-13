import QtQuick
import QtQuick.Layouts

Rectangle {
    id: surface
    property var theme: null
    color: theme
           ? theme.windowBg
           : (typeof bridge !== "undefined" && bridge.dark ? "#14181c" : "#f5f5f5")
    implicitWidth: 400
    implicitHeight: surfaceColumn.implicitHeight
    default property alias content: surfaceColumn.data
    ColumnLayout {
        id: surfaceColumn
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 10
    }
}
