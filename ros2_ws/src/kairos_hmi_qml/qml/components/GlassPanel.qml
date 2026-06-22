import QtQuick 2.15
import QtGraphicalEffects 1.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string title: ""
    property int pad: 18
    property bool glow: false
    default property alias content: body.data

    radius: 16
    color: T.panel
    border.color: glow ? "#5522d3ee" : T.line
    border.width: 1

    // soft depth
    layer.enabled: true
    layer.effect: DropShadow {
        transparentBorder: true
        horizontalOffset: 0
        verticalOffset: 16
        radius: 30
        samples: 31
        color: "#9c000000"
    }

    Kicker {
        id: hdr
        label: root.title
        visible: root.title !== ""
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.leftMargin: root.pad
        anchors.topMargin: root.pad
    }

    Item {
        id: body
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.top: root.title !== "" ? hdr.bottom : parent.top
        anchors.leftMargin: root.pad
        anchors.rightMargin: root.pad
        anchors.bottomMargin: root.pad
        anchors.topMargin: root.title !== "" ? 14 : root.pad
    }
}
