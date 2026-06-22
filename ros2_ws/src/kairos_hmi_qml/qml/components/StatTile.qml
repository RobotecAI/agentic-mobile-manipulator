import QtQuick 2.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string label: ""
    property string value: "—"
    property color valueColor: T.fg

    radius: 12
    color: T.line2
    border.color: T.line
    border.width: 1
    implicitHeight: 72

    Column {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 5
        Kicker { label: root.label }
        Text {
            width: parent.width
            text: root.value
            color: root.valueColor
            font.pixelSize: 23
            font.bold: true
            elide: Text.ElideRight
        }
    }
}
