import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtGraphicalEffects 1.15
import "../Theme.js" as T

Rectangle {
    id: root
    property string accent: "cyan"
    property string glyph: "●"
    property string title: ""
    property string desc: ""
    property string cta: "Run"
    property string hint: ""
    signal run()

    radius: 16
    color: T.panel
    border.color: cardMa.containsMouse ? T.grad(accent)[0] : T.line
    border.width: 1
    implicitHeight: 236

    // whole-card hover lift (scale is safe inside a Layout; y is not)
    scale: cardMa.containsMouse ? 1.012 : 1.0
    Behavior on scale { NumberAnimation { duration: 130; easing.type: Easing.OutCubic } }
    Behavior on border.color { ColorAnimation { duration: 130 } }

    layer.enabled: true
    layer.effect: DropShadow {
        transparentBorder: true; verticalOffset: 14; radius: 26; samples: 27
        color: cardMa.containsMouse ? T.grad(root.accent)[0] + "55" : "#88000000"
    }

    // entire card is clickable
    MouseArea {
        id: cardMa
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.run()
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 18
        spacing: 10

        Rectangle {
            width: 44; height: 44; radius: 12
            gradient: Gradient {
                GradientStop { position: 0.0; color: T.grad(root.accent)[0] }
                GradientStop { position: 1.0; color: T.grad(root.accent)[1] }
            }
            Text { anchors.centerIn: parent; text: root.glyph; color: "#04121a"; font.pixelSize: 20; font.bold: true }
        }
        Text { text: root.title; color: T.fg; font.pixelSize: 18; font.bold: true }
        Text {
            Layout.fillWidth: true; Layout.fillHeight: true
            text: root.desc; color: T.dim; font.pixelSize: 14; wrapMode: Text.WordWrap
        }
        Text { visible: root.hint !== ""; text: root.hint; color: T.dim; font.pixelSize: 13 }
        // CTA — clicking it (or anywhere on the card) dispatches
        AppButton { Layout.fillWidth: true; variant: "primary"; text: root.cta; onClicked: root.run() }
    }
}
