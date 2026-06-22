import QtQuick 2.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string glyph: "▲"
    signal down()
    signal up()

    width: 56; height: 52; radius: 12
    color: ma.pressed ? "#16263e" : T.panelHi
    border.color: ma.pressed ? T.cyan : T.line
    border.width: 1

    Text { anchors.centerIn: parent; text: root.glyph; color: ma.pressed ? T.cyan : T.fg; font.pixelSize: 17 }

    MouseArea {
        id: ma
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onPressed: root.down()
        onReleased: root.up()
        onCanceled: root.up()
    }
}
