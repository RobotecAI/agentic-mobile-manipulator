import QtQuick 2.15
import QtQuick.Layouts 1.15

Card {
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 6
            Repeater {
                model: ["Base", "Wrist", "Top"]
                delegate: Chip {
                    text: modelData
                    selected: ros.cameraIndex === index
                    onClicked: ros.cameraIndex = index
                }
            }
            Item { Layout.fillWidth: true }
            Label2 { text: ros.cameraTopic; color: Theme.faint; font.family: Theme.mono; font.pixelSize: 11 }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: Theme.well
            radius: Theme.radius
            Image {
                anchors.fill: parent
                anchors.margins: 2
                source: "image://ros/camera?" + ros.cameraFrame
                fillMode: Image.PreserveAspectFit
                cache: false
                asynchronous: false
                smooth: true
            }
            Label2 {
                anchors.centerIn: parent
                visible: ros.cameraFrame < 2
                text: "No frames on " + ros.cameraTopic
                color: Theme.faint
            }
        }
    }
}
