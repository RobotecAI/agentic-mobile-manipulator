import QtQuick 2.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string camName: "base"
    radius: 12
    color: "#0a1018"
    border.color: T.line
    border.width: 1
    clip: true

    // placeholder shows through whenever the live frame is absent (transparent)
    Column {
        anchors.centerIn: parent
        spacing: 8
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "□"
            color: T.faint
            font.pixelSize: 22
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "NO SIGNAL"
            color: T.faint
            font.pixelSize: 10
            font.letterSpacing: 2
            font.family: "monospace"
        }
    }

    Image {
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        cache: false
        asynchronous: true
        source: "image://kairos/" + root.camName + "?" + ros.cameraRev
    }

    // inner vignette
    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "transparent"
        border.color: "#33000000"
        border.width: 6
    }
}
