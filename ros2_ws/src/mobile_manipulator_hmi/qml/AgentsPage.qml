import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// How the agents work together: who is doing what, and the trace of the current task.
Item {
    id: page
    property var trace: ros.traceFilter
    property var selected: ({})
    readonly property var agentsByGroup: {
        const g = { orchestrator: [], executor: [], background: [], skill: [] }
        for (const a of ros.agents) g[a.group].push(a)
        return g
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // Flow graph
        Card {
            Layout.fillWidth: true
            implicitHeight: graph.implicitHeight + 32
            ColumnLayout {
                id: graph
                anchors.fill: parent
                anchors.margins: 16
                spacing: 12
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 14
                    Label2 { text: "Agent flow"; font.pixelSize: 16; font.weight: Font.DemiBold }
                    Label2 { text: "Click an agent to filter the trace"; color: Theme.faint; font.pixelSize: 12; Layout.fillWidth: true }
                    Repeater {
                        model: [["working", Theme.accent], ["idle", "#7D8796"], ["offline", Theme.dangerText]]
                        delegate: Row {
                            spacing: 6
                            Rectangle { width: 8; height: 8; radius: 4; color: modelData[1]; anchors.verticalCenter: parent.verticalCenter }
                            Label2 { text: modelData[0]; color: Theme.muted; font.pixelSize: 12 }
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 16
                    // Orchestrator and its executors (one process)
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 3
                        spacing: 8
                        Label2 { text: "ORCHESTRATOR · plans the task and delegates steps"; color: Theme.faint; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.5 }
                        Repeater {
                            model: page.agentsByGroup.orchestrator
                            delegate: AgentCard {
                                Layout.fillWidth: true
                                agent: modelData
                                selected: page.trace.agent === modelData.name
                                onClicked: page.trace.agent = selected ? "" : modelData.name
                            }
                        }
                        Rectangle { Layout.alignment: Qt.AlignHCenter; width: 2; height: 14; color: Theme.borderStrong }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: page.agentsByGroup.executor
                                delegate: AgentCard {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    agent: modelData
                                    selected: page.trace.agent === modelData.name
                                    onClicked: page.trace.agent = selected ? "" : modelData.name
                                }
                            }
                        }
                    }
                    Rectangle { Layout.fillHeight: true; width: 1; color: Theme.border }
                    // Background agents and robot skills
                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: 3
                        spacing: 8
                        Label2 { text: "WATCHING · vision agents running on their own"; color: Theme.faint; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.5 }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: page.agentsByGroup.background
                                delegate: AgentCard {
                                    Layout.fillWidth: true
                                    Layout.preferredWidth: 1
                                    agent: modelData
                                    selected: page.trace.agent === modelData.name
                                    onClicked: page.trace.agent = selected ? "" : modelData.name
                                }
                            }
                        }
                        Label2 { text: "SKILLS · ROS 2 servers the tools call"; color: Theme.faint; font.pixelSize: 11; font.weight: Font.DemiBold; font.letterSpacing: 0.5; Layout.topMargin: 6 }
                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            Repeater {
                                model: page.agentsByGroup.skill
                                delegate: AgentCard { Layout.fillWidth: true; Layout.preferredWidth: 1; agent: modelData; enabled: false }
                            }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            // Trace timeline
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.margins: 14
                        spacing: 10
                        Label2 { text: "Trace"; font.pixelSize: 15; font.weight: Font.DemiBold }
                        Chip { text: page.trace.agent === "" ? "All agents" : page.trace.agent + " only"; selected: page.trace.agent !== ""; onClicked: page.trace.agent = "" }
                        Label2 { text: ros.currentTask; color: Theme.faint; font.pixelSize: 12; Layout.fillWidth: true }
                        Label2 { text: Math.round(timeline.span / 1000) + " s window"; color: Theme.faint; font.family: Theme.mono; font.pixelSize: 11 }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                    ListView {
                        id: timeline
                        // Rows and bars cover the current task (or the last 3 minutes when idle).
                        readonly property real t0: ros.currentTask !== "" ? Math.max(0, ros.taskStartMs - 500) : Math.max(0, ros.nowMs - 180000)
                        readonly property real span: Math.max(1000, ros.nowMs - t0)
                        property bool follow: true
                        property bool autoScroll: false
                        function scrollToEnd() { autoScroll = true; positionViewAtEnd(); autoScroll = false }
                        Binding { target: page.trace; property: "minStartMs"; value: timeline.t0 }
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 6
                        clip: true
                        model: page.trace
                        ScrollBar.vertical: ScrollBar {}
                        onCountChanged: if (follow) Qt.callLater(scrollToEnd)
                        onContentYChanged: if (!autoScroll) follow = atYEnd
                        delegate: AbstractButton {
                            id: row
                            clip: true
                            width: timeline.width
                            height: 30
                            hoverEnabled: true
                            onClicked: page.selected = page.trace.get(index)
                            readonly property bool isSelected: page.selected.startMs === model.startMs && page.selected.agent === model.agent
                            background: Rectangle { radius: 8; color: row.isSelected ? Theme.accentBg : row.hovered ? "#141920" : "transparent" }
                            contentItem: RowLayout {
                                spacing: 12
                                Rectangle { width: 8; height: 8; radius: 4; color: ros.agentColor(model.agent); Layout.leftMargin: 8 }
                                Label2 {
                                    Layout.preferredWidth: 240
                                    text: model.kind === "tool" ? model.toolName : model.kind === "vlm" ? model.agent.toLowerCase() + " finding"
                                        : model.kind === "task" ? model.text : model.agent.toLowerCase() + " · " + model.kind
                                    font.family: Theme.mono
                                    font.pixelSize: 12
                                }
                                Rectangle {
                                    Layout.fillWidth: true
                                    height: 18
                                    radius: 4
                                    color: Theme.well
                                    Rectangle {
                                        readonly property real end: model.status === "running" ? ros.nowMs : model.endMs
                                        y: 3
                                        height: 12
                                        radius: 3
                                        x: Math.min(parent.width - 4, Math.max(0, (model.startMs - timeline.t0) / timeline.span * parent.width))
                                        width: Math.min(parent.width - x, Math.max(4, (end - Math.max(model.startMs, timeline.t0)) / timeline.span * parent.width))
                                        color: ros.agentColor(model.agent)
                                        opacity: model.status === "running" || model.streaming ? 0.55 : 1
                                    }
                                }
                                Label2 {
                                    Layout.preferredWidth: 64
                                    Layout.rightMargin: 8
                                    horizontalAlignment: Text.AlignRight
                                    text: model.status === "running" ? "running" : (model.durationMs / 1000).toFixed(1) + " s"
                                    color: Theme.muted
                                    font.family: Theme.mono
                                    font.pixelSize: 11
                                }
                            }
                        }
                        Label2 {
                            anchors.centerIn: parent
                            visible: timeline.count === 0
                            text: "No agent activity yet."
                            color: Theme.faint
                        }
                    }
                }
            }

            // Detail of the selected entry
            Card {
                Layout.fillHeight: true
                Layout.preferredWidth: Math.max(360, page.width * 0.36)
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 10
                    visible: page.selected.agent !== undefined
                    RowLayout {
                        spacing: 8
                        Rectangle { width: 10; height: 10; radius: 5; color: ros.agentColor(page.selected.agent || "") }
                        Label2 { text: page.selected.agent || ""; color: ros.agentColor(page.selected.agent || ""); font.pixelSize: 13; font.weight: Font.DemiBold }
                        Label2 { text: page.selected.kind || ""; color: Theme.faint; font.pixelSize: 11; font.capitalization: Font.AllUppercase }
                    }
                    Label2 { text: page.selected.toolName || page.selected.node || ""; font.family: Theme.mono; font.pixelSize: 14 }
                    Flow {
                        Layout.fillWidth: true
                        spacing: 6
                        Repeater {
                            model: [
                                page.selected.time ? "at " + page.selected.time : "",
                                page.selected.durationMs !== undefined ? (page.selected.durationMs / 1000).toFixed(1) + " s" : "",
                                page.selected.tokens || "",
                                page.selected.status || ""
                            ].filter(x => x !== "")
                            delegate: Rectangle {
                                height: 22; width: metaText.implicitWidth + 16; radius: 6; color: Theme.panel2
                                Text { id: metaText; anchors.centerIn: parent; text: modelData; color: "#AEB7C4"; font.family: Theme.mono; font.pixelSize: 11 }
                            }
                        }
                    }
                    Image {
                        visible: (page.selected.image || "") !== ""
                        source: visible ? "image://ros/" + page.selected.image : ""
                        Layout.fillWidth: true
                        Layout.preferredHeight: 180
                        fillMode: Image.PreserveAspectFit
                        cache: false
                    }
                    Label2 { text: page.selected.kind === "tool" ? "ARGUMENTS" : "CONTENT"; color: Theme.faint; font.pixelSize: 11; font.weight: Font.DemiBold }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        TextArea {
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextEdit.WrapAnywhere
                            text: (page.selected.text || "") + (page.selected.result ? "\n\nRESULT\n" + page.selected.result : "")
                            color: Theme.textSoft
                            font.family: Theme.mono
                            font.pixelSize: 12
                            background: Rectangle { color: Theme.bg; radius: 10; border.color: Theme.border }
                        }
                    }
                }
                Label2 {
                    anchors.centerIn: parent
                    visible: page.selected.agent === undefined
                    text: "Select a row in the trace to see its full content."
                    color: Theme.faint
                }
            }
        }
    }
}
