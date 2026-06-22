import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string accent: "cyan"
    property string glyph: "●"
    property string title: ""
    property string desc: ""
    signal spawn()

    radius: 16
    color: T.panel
    border.color: ma.containsMouse ? "#33ffffff" : T.line
    border.width: 1
    implicitHeight: 152
    clip: true

    Rectangle {
        width: 110; height: 110; radius: 55
        x: parent.width - 55; y: -45
        color: T.grad(root.accent)[0]
        opacity: ma.containsMouse ? 0.30 : 0.16
        Behavior on opacity { NumberAnimation { duration: 150 } }
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 5
        Rectangle {
            width: 36; height: 36; radius: 10
            gradient: Gradient {
                GradientStop { position: 0.0; color: T.grad(root.accent)[0] }
                GradientStop { position: 1.0; color: T.grad(root.accent)[1] }
            }
            Text { anchors.centerIn: parent; text: root.glyph; color: "#04121a"; font.pixelSize: 16; font.bold: true }
        }
        Text { text: root.title; color: T.fg; font.pixelSize: 16; font.bold: true }
        Text { Layout.fillWidth: true; Layout.fillHeight: true; text: root.desc; color: T.dim; font.pixelSize: 12; wrapMode: Text.WordWrap }
        Text { text: "Spawn scenario →"; color: T.cyan; font.pixelSize: 12; font.bold: true }
    }

    MouseArea { id: ma; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: root.spawn() }
}
