import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Live agent stream: every agent's messages, tool calls and findings, filterable by agent.
Card {
    id: root
    signal openTrace()
    property var filter: ros.streamFilter

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ColumnLayout {
            Layout.fillWidth: true
            Layout.margins: 14
            spacing: 10
            RowLayout {
                Layout.fillWidth: true
                Label2 { text: "Agent stream"; font.pixelSize: 15; font.weight: Font.DemiBold }
                Rectangle {
                    width: 7; height: 7; radius: 4; color: Theme.ok
                    SequentialAnimation on opacity { loops: Animation.Infinite; NumberAnimation { to: 0.3; duration: 800 } NumberAnimation { to: 1; duration: 800 } }
                }
                Item { Layout.fillWidth: true }
                Chip { visible: !list.follow; text: "↓ Latest"; onClicked: { list.follow = true; list.scrollToEnd() } }
                Btn { kind: "ghost"; text: "Open trace →"; implicitHeight: 30; onClicked: root.openTrace() }
            }
            Flow {
                Layout.fillWidth: true
                spacing: 6
                Repeater {
                    model: ["", "Orchestrator", "Housekeep", "Package movement", "Image analysis", "Inspection", "Safety"]
                    delegate: Chip {
                        text: modelData === "" ? "All" : modelData
                        dot: modelData === "" ? Theme.text : ros.agentColor(modelData)
                        selected: root.filter.agent === modelData
                        onClicked: root.filter.agent = modelData
                    }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }

        ListView {
            id: list
            // Follows new entries while the view is at the bottom; scrolling up pauses it.
            property bool follow: true
            property bool autoScroll: false
            function scrollToEnd() { autoScroll = true; positionViewAtEnd(); autoScroll = false }
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 6
            clip: true
            spacing: 4
            model: root.filter
            delegate: StreamEntry {}
            ScrollBar.vertical: ScrollBar {}
            onCountChanged: if (follow) Qt.callLater(scrollToEnd)
            onContentHeightChanged: if (follow) Qt.callLater(scrollToEnd)
            onContentYChanged: if (!autoScroll) follow = atYEnd

            Label2 {
                anchors.centerIn: parent
                visible: list.count === 0
                text: "Waiting for agents…\nAssign a task to see the agents think and act here."
                horizontalAlignment: Text.AlignHCenter
                color: Theme.faint
            }
        }

        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
        Flow {
            Layout.fillWidth: true
            Layout.margins: 10
            spacing: 6
            Repeater {
                model: ros.endpoints.filter(e => e.type === "llm" || e.type === "vlm")
                delegate: Rectangle {
                    height: 24
                    width: epText.implicitWidth + 16
                    radius: 6
                    color: Theme.panel2
                    Text {
                        id: epText
                        anchors.centerIn: parent
                        text: modelData.model + " · " + modelData.backend
                        color: modelData.ok ? "#AEB7C4" : Theme.dangerText
                        font.family: Theme.mono
                        font.pixelSize: 11
                    }
                }
            }
        }
    }
}
