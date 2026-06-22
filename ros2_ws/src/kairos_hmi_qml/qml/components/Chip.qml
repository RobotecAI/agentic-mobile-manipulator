import QtQuick 2.15
import "../Theme.js" as T

Rectangle {
    id: root
    property color dotColor: T.emerald
    property string text: ""
    property bool pulse: false

    radius: height / 2
    color: T.panelHi
    border.color: T.line
    border.width: 1
    implicitHeight: 30
    implicitWidth: row.implicitWidth + 26

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        StatusOrb { anchors.verticalCenter: parent.verticalCenter; dotColor: root.dotColor; pulse: root.pulse }
        Text { anchors.verticalCenter: parent.verticalCenter; text: root.text; color: T.dim; font.pixelSize: 13 }
    }
}
