import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: window
    width: 1440
    height: 900
    minimumWidth: 1100
    minimumHeight: 720
    visible: true
    visibility: startFullScreen ? Window.FullScreen : Window.Windowed
    title: "Mobile Manipulator · Operator console"
    color: Theme.bg
    font.family: Theme.sans

    property int page: startPage

    Shortcut {
        sequence: "F11"
        onActivated: window.visibility = window.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen
    }

    header: Rectangle {
        height: 60
        color: Theme.chrome
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: Theme.border }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 10

            Icon { name: "robot"; color: Theme.accent; size: 26 }
            Column {
                Layout.rightMargin: 14
                Label2 { text: "Mobile Manipulator"; font.pixelSize: 15; font.weight: Font.Bold }
                Label2 { text: "Operator console"; font.pixelSize: 11; color: Theme.faint }
            }
            StatusPill {
                text: ros.estopped ? "Emergency stop active" : ros.currentTask !== "" ? "Mission running" : "Idle"
                tone: ros.estopped ? "danger" : ros.currentTask !== "" ? "ok" : "neutral"
                pulse: !ros.estopped && ros.currentTask !== ""
            }
            StatusPill { text: "sim " + ros.simTime; tone: "neutral" }
            StatusPill {
                readonly property int up: ros.endpoints.filter(e => e.ok).length
                text: "Inference " + up + "/" + ros.endpoints.length
                tone: up === ros.endpoints.length && up > 0 ? "ok" : "warn"
            }
            StatusPill {
                readonly property var live: ros.agents.filter(a => a.group !== "executor")
                readonly property int up: live.filter(a => a.state === "idle" || a.state === "working").length
                text: "Agents " + up + "/" + live.length
                tone: up === live.length ? "ok" : "warn"
            }
            Item { Layout.fillWidth: true }
            Btn {
                visible: ros.estopped
                text: "Release stop"
                iconName: "play"
                onClicked: ros.releaseStop()
            }
            Btn {
                kind: "estop"
                text: "E-STOP"
                iconName: "stop"
                Accessible.name: "Emergency stop"
                onClicked: ros.emergencyStop()
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Left rail
        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 88
            color: Theme.chrome
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.border }
            Column {
                anchors.fill: parent
                anchors.margins: 10
                anchors.topMargin: 14
                spacing: 6
                Repeater {
                    model: [
                        { label: "Mission", icon: "mission" },
                        { label: "Agents", icon: "agents" },
                        { label: "Simulation", icon: "sim" },
                        { label: "System", icon: "system" }
                    ]
                    delegate: AbstractButton {
                        id: nav
                        width: parent.width
                        height: 64
                        hoverEnabled: true
                        Accessible.name: modelData.label
                        onClicked: window.page = index
                        readonly property bool active: window.page === index
                        background: Rectangle {
                            radius: 12
                            color: nav.active ? Theme.accentBg : nav.hovered ? Theme.panel2 : "transparent"
                            border.width: nav.activeFocus ? 2 : 0
                            border.color: Theme.accent
                        }
                        contentItem: Column {
                            spacing: 6
                            topPadding: 10
                            Icon {
                                name: modelData.icon
                                size: 22
                                color: nav.active ? Theme.accentSoft : Theme.muted
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                            Text {
                                text: modelData.label
                                color: nav.active ? Theme.accentSoft : Theme.muted
                                font.family: Theme.sans
                                font.pixelSize: 11
                                font.weight: Font.DemiBold
                                anchors.horizontalCenter: parent.horizontalCenter
                            }
                        }
                    }
                }
            }
        }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: window.page
            MissionPage { onOpenTrace: window.page = 1 }
            AgentsPage {}
            SimulationPage {}
            SystemPage {}
        }
    }

    // Operator feedback (task sent, scene loaded, service missing).
    Rectangle {
        id: toast
        property bool error: false
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        width: toastText.implicitWidth + 32
        height: 40
        radius: 10
        color: error ? "#2C1416" : "#15202F"
        border.color: error ? "#4A2326" : "#2F4D7A"
        opacity: 0
        visible: opacity > 0
        Text {
            id: toastText
            anchors.centerIn: parent
            color: toast.error ? Theme.dangerText : Theme.text
            font.family: Theme.sans
            font.pixelSize: 13
        }
        Behavior on opacity { NumberAnimation { duration: 180 } }
        Timer { id: toastTimer; interval: 3500; onTriggered: toast.opacity = 0 }
        Connections {
            target: ros
            function onNotify(message, error) {
                toastText.text = message
                toast.error = error
                toast.opacity = 1
                toastTimer.restart()
            }
        }
    }
}
