import QtQuick 2.15
import QtQuick.Controls 2.15

// Pill toggle with an optional color dot (filters, quick tasks, item pickers).
Button {
    id: control
    property color dot: "transparent"
    property bool selected: false
    implicitHeight: 30
    leftPadding: 12
    rightPadding: 12
    hoverEnabled: true
    font.family: Theme.sans
    font.pixelSize: 12
    font.weight: Font.Medium
    contentItem: Row {
        spacing: 6
        Rectangle {
            visible: control.dot !== Qt.rgba(0, 0, 0, 0)
            width: 8; height: 8; radius: 4
            color: control.dot
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: control.text
            font: control.font
            color: control.selected ? Theme.accentSoft : Theme.textSoft
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    background: Rectangle {
        radius: height / 2
        color: control.selected ? Theme.accentBg : control.hovered ? "#1C222C" : Theme.panel2
        border.color: control.selected ? "#3B5F99" : Theme.borderStrong
        border.width: control.activeFocus ? 2 : 1
    }
}
