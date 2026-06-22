import QtQuick 2.15
import QtQuick.Window 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import QtGraphicalEffects 1.15
import "components"
import "views"
import "Theme.js" as T

ApplicationWindow {
    id: win
    visible: true
    width: 1920
    height: 1080
    visibility: startFullscreen ? Window.FullScreen : Window.Windowed
    title: "Kairos+ Command"
    color: T.bg

    property int currentIndex: initialTab
    readonly property var tabs: ["Mission", "Control", "Telemetry"]
    readonly property int itemW: 150

    // ---------------- ambient background ----------------
    Item {
        anchors.fill: parent
        RadialGradient {
            anchors.fill: parent
            horizontalRadius: 900; verticalRadius: 700
            horizontalOffset: -width * 0.38; verticalOffset: -height * 0.42
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#2a38bdf8" }
                GradientStop { position: 0.55; color: "transparent" }
            }
        }
        RadialGradient {
            anchors.fill: parent
            horizontalRadius: 850; verticalRadius: 700
            horizontalOffset: width * 0.42; verticalOffset: -height * 0.46
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#26a78bfa" }
                GradientStop { position: 0.55; color: "transparent" }
            }
        }
        RadialGradient {
            anchors.fill: parent
            horizontalRadius: 1000; verticalRadius: 800
            horizontalOffset: width * 0.28; verticalOffset: height * 0.55
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#1ef9a23b" }
                GradientStop { position: 0.5; color: "transparent" }
            }
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ---------------- header ----------------
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 64
            color: "#0a1018cc"
            Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: T.line }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 22; anchors.rightMargin: 22
                spacing: 14

                Rectangle {
                    width: 38; height: 38; radius: 11
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#3322d3ee" }
                        GradientStop { position: 1; color: "#33a78bfa" }
                    }
                    border.color: "#22ffffff"
                    Text { anchors.centerIn: parent; text: "⬡"; color: T.cyan; font.pixelSize: 18 }
                }
                ColumnLayout {
                    spacing: 0
                    Text { text: "Kairos+ Command"; color: T.fg; font.pixelSize: 16; font.bold: true }
                    Text { text: "Agentic warehouse manipulator"; color: T.faint; font.pixelSize: 11 }
                }

                Item { Layout.fillWidth: true }

                Text {
                    id: clock
                    color: T.dim; font.pixelSize: 14; font.family: "monospace"
                    property var now: new Date()
                    text: Qt.formatTime(now, "hh:mm:ss")
                    Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.now = new Date() }
                }
                Chip { dotColor: T.emerald; pulse: true; text: "ROS 2 graph" }
                Chip { dotColor: ros.agentOnline ? T.emerald : T.red; pulse: ros.agentOnline; text: ros.agentOnline ? "agent online" : "agent offline" }
                AppButton { variant: "danger"; text: "E-STOP"; onClicked: ros.estop() }
            }
        }

        // ---------------- nav ----------------
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 78
            Rectangle {
                id: nav
                anchors.centerIn: parent
                height: 54
                width: navRow.implicitWidth + 12
                radius: 16
                color: T.panel
                border.color: T.line

                Rectangle {
                    id: pill
                    height: 42; radius: 11; y: 6
                    width: win.itemW
                    x: 6 + win.currentIndex * win.itemW
                    gradient: Gradient {
                        GradientStop { position: 0; color: T.cyan }
                        GradientStop { position: 1; color: T.blue }
                    }
                    Behavior on x { NumberAnimation { duration: 240; easing.type: Easing.OutCubic } }
                }
                Row {
                    id: navRow
                    anchors.centerIn: parent
                    Repeater {
                        model: win.tabs
                        Item {
                            width: win.itemW; height: 42
                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                font.pixelSize: 15; font.bold: true
                                color: index === win.currentIndex ? "#04121a" : T.dim
                            }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: win.currentIndex = index }
                        }
                    }
                }
            }
        }

        // ---------------- views ----------------
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 20
            currentIndex: win.currentIndex
            MissionView {}
            ControlView {}
            TelemetryView {}
        }
    }
}
