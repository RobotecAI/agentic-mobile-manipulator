import QtQuick 2.15
import QtGraphicalEffects 1.15

Item {
    id: root
    property color dotColor: "#34d399"
    property bool pulse: false
    implicitWidth: 12
    implicitHeight: 12

    Rectangle {
        id: ring
        anchors.centerIn: parent
        width: 10; height: 10; radius: 5
        color: root.dotColor
        opacity: 0
        visible: root.pulse
    }
    ParallelAnimation {
        running: root.pulse
        loops: Animation.Infinite
        NumberAnimation { target: ring; property: "scale"; from: 1; to: 2.7; duration: 1700; easing.type: Easing.OutQuad }
        NumberAnimation { target: ring; property: "opacity"; from: 0.6; to: 0; duration: 1700 }
    }

    Rectangle {
        id: dot
        anchors.centerIn: parent
        width: 9; height: 9; radius: 4.5
        color: root.dotColor
        layer.enabled: true
        layer.effect: Glow { radius: 7; samples: 15; spread: 0.25; color: root.dotColor }
    }
}
