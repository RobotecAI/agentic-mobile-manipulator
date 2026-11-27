import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Home: assign tasks, watch the robot, follow the agents.
Item {
    id: page
    signal openTrace()

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            // Command bar
            Card {
                Layout.fillWidth: true
                implicitHeight: cmd.implicitHeight + 28
                ColumnLayout {
                    id: cmd
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 10
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Rectangle {
                            Layout.fillWidth: true
                            height: 48
                            radius: 12
                            color: Theme.bg
                            border.color: input.activeFocus ? Theme.accent : Theme.borderStrong
                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                spacing: 10
                                Icon { name: "prompt"; size: 18; color: Theme.faint; strokeWidth: 2 }
                                TextField {
                                    id: input
                                    Layout.fillWidth: true
                                    placeholderText: "Tell the robot what to do, e.g. “Do housekeeping of rack J01”"
                                    placeholderTextColor: Theme.faint
                                    color: Theme.text
                                    font.family: Theme.sans
                                    font.pixelSize: 15
                                    background: null
                                    Accessible.name: "Task for the robot"
                                    onAccepted: { ros.sendTask(text); text = "" }
                                }
                            }
                        }
                        Btn {
                            kind: "primary"
                            text: "Assign"
                            implicitHeight: 48
                            enabled: input.text.trim() !== ""
                            onClicked: { ros.sendTask(input.text); input.text = "" }
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        Label2 { text: "Quick tasks"; color: Theme.faint; font.pixelSize: 12; height: 30; verticalAlignment: Text.AlignVCenter }
                        Repeater {
                            model: [
                                { label: "Sort returns", prompt: "Do Sort Package Returns" },
                                { label: "Housekeeping J01", prompt: "Do Housekeeping of rack J01" }
                            ]
                            delegate: Chip { text: modelData.label; onClicked: ros.sendTask(modelData.prompt) }
                        }
                    }
                }
            }

            // Viewport
            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 300
                spacing: 16
                CameraPanel { Layout.fillWidth: true; Layout.fillHeight: true }
                MapPanel { Layout.fillHeight: true; Layout.preferredWidth: Math.max(240, parent.width * 0.36) }
            }

            // Current task, steps, queue
            Card {
                Layout.fillWidth: true
                implicitHeight: taskCol.implicitHeight + 32
                ColumnLayout {
                    id: taskCol
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Label2 { text: "Current task"; font.weight: Font.DemiBold }
                        Rectangle {
                            visible: ros.currentTask !== ""
                            Layout.maximumWidth: 520
                            implicitWidth: taskName.implicitWidth + 16
                            height: 24
                            radius: 6
                            color: Theme.accentBg
                            Label2 {
                                id: taskName
                                anchors.fill: parent
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                verticalAlignment: Text.AlignVCenter
                                text: ros.currentTask
                                color: Theme.accentSoft
                                font.pixelSize: 12
                                font.weight: Font.DemiBold
                            }
                        }
                        Label2 {
                            text: ros.currentTask === "" ? "No task running. Assign one above or from Simulation."
                                : "running " + Math.round((ros.nowMs - ros.taskStartMs) / 1000) + " s · "
                                  + ros.pastSteps.length + " step" + (ros.pastSteps.length === 1 ? "" : "s") + " done"
                            color: Theme.faint
                            font.pixelSize: 12
                            Layout.fillWidth: true
                        }
                    }
                    // Steps: done ones, then the one in progress.
                    Flow {
                        Layout.fillWidth: true
                        spacing: 8
                        visible: ros.currentTask !== "" || ros.pastSteps.length > 0
                        Repeater {
                            model: ros.pastSteps.concat(ros.currentTask !== "" ? ["…in progress"] : [])
                            delegate: Rectangle {
                                readonly property bool active: index === ros.pastSteps.length
                                width: Math.min(260, stepText.implicitWidth + 24)
                                height: 52
                                radius: 10
                                color: active ? "#15202F" : Theme.panel2
                                border.color: active ? "#2F4D7A" : "#1E2530"
                                Rectangle { x: 10; y: 10; width: parent.width - 20; height: 4; radius: 2; color: active ? Theme.accent : Theme.ok }
                                Label2 {
                                    id: stepText
                                    x: 12; y: 22
                                    width: parent.width - 24
                                    text: (index + 1) + ". " + modelData
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    color: active ? Theme.text : Theme.textSoft
                                }
                            }
                        }
                    }
                    Label2 {
                        text: "QUEUE · " + ros.queue.length
                        color: Theme.faint; font.pixelSize: 12; font.weight: Font.DemiBold; font.letterSpacing: 0.4
                    }
                    Repeater {
                        model: ros.queue
                        delegate: Rectangle {
                            Layout.fillWidth: true
                            height: 34
                            radius: 10
                            color: Theme.panel2
                            Label2 {
                                anchors.fill: parent
                                anchors.leftMargin: 12
                                anchors.rightMargin: 12
                                verticalAlignment: Text.AlignVCenter
                                text: (index + 1) + "   " + modelData
                                font.pixelSize: 13
                            }
                        }
                    }
                    Label2 { visible: ros.queue.length === 0; text: "Queue is empty."; color: Theme.faint; font.pixelSize: 12 }
                }
            }
        }

        AgentStream {
            Layout.fillHeight: true
            Layout.preferredWidth: Math.max(400, page.width * 0.36)
            onOpenTrace: page.openTrace()
        }
    }
}
