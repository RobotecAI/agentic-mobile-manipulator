import QtQuick 2.15
import QtGraphicalEffects 1.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string text: ""
    property string variant: "ghost"   // primary | danger | ghost | subtle
    signal clicked()

    implicitHeight: 42
    implicitWidth: label.implicitWidth + 40
    radius: 11

    readonly property bool accent: variant === "primary" || variant === "danger"
    // solid bright base colour so the button is always legible even if the
    // gradient layer does not render on a given GPU
    color: variant === "primary" ? T.cyan
         : variant === "danger" ? T.red
         : variant === "ghost" ? T.panelHi : "transparent"
    border.width: variant === "ghost" ? 1 : 0
    border.color: T.line

    gradient: accent ? accentGrad : null
    Gradient {
        id: accentGrad
        GradientStop { position: 0.0; color: variant === "danger" ? "#ff7a7a" : "#3fe0f5" }
        GradientStop { position: 1.0; color: variant === "danger" ? "#fb5a5a" : "#2aa8e8" }
    }

    Rectangle {
        anchors.fill: parent
        radius: parent.radius
        color: "#16ffffff"
        opacity: ma.containsMouse ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 120 } }
    }

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.pixelSize: 14
        font.bold: true
        color: variant === "primary" ? "#04121a"
             : variant === "danger" ? "#ffffff"
             : variant === "subtle" ? T.dim : T.fg
    }

    MouseArea {
        id: ma
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
        onPressed: root.scale = 0.97
        onReleased: root.scale = 1.0
        onCanceled: root.scale = 1.0
    }
    Behavior on scale { NumberAnimation { duration: 90 } }

    layer.enabled: accent
    layer.effect: DropShadow {
        transparentBorder: true
        verticalOffset: 6
        radius: 22
        samples: 23
        color: variant === "danger" ? "#88fb5a5a" : "#8822d3ee"
    }
}
