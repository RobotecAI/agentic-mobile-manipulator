import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../Theme.js" as T

Item {
    id: view

    property var cpuHist: []
    property var ramHist: []
    property var gpuHist: []
    property var vramHist: []
    function push(a, v) { var b = a.slice(-39); b.push(v); return b; }

    readonly property var models: [
        { name: "gpt-oss-20b", role: "orchestrator LLM", port: ":8080", vram: "11.5 GB" },
        { name: "lfm2-vl", role: "VLM hazard analysis", port: ":8081", vram: "3.8 GB" },
        { name: "qwen3-embedding", role: "memory retrieval", port: ":8082", vram: "0.7 GB" },
        { name: "qwen3-reranker", role: "memory ranking", port: ":8083", vram: "0.7 GB" }
    ]

    Connections {
        target: ros
        function onTelemetryChanged() {
            if (!ros.hasTelemetry) return;
            view.cpuHist = view.push(view.cpuHist, ros.cpu);
            view.ramHist = view.push(view.ramHist, ros.ram);
            view.gpuHist = view.push(view.gpuHist, ros.gpu);
            view.vramHist = view.push(view.vramHist, ros.vram);
        }
    }

    ColumnLayout {
        id: tcol
        anchors.fill: parent
        spacing: 18

        // ---- gauges (~26% height, capped) ----
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: tcol.height * 0.26
            Layout.maximumHeight: tcol.height * 0.26
            spacing: 18
            GaugeCard { gaugeLabel: "CPU"; gaugeAccent: "cyan"; gaugeValue: ros.hasTelemetry ? ros.cpu : -1; series: view.cpuHist }
            GaugeCard { gaugeLabel: "RAM"; gaugeAccent: "violet"; gaugeValue: ros.hasTelemetry ? ros.ram : -1; series: view.ramHist }
            GaugeCard { gaugeLabel: "GPU"; gaugeAccent: "amber"; gaugeValue: ros.hasTelemetry ? ros.gpu : -1; series: view.gpuHist }
            GaugeCard { gaugeLabel: "VRAM"; gaugeAccent: "emerald"; gaugeValue: ros.hasTelemetry ? ros.vram : -1; series: view.vramHist }
        }

        // ---- event timeline (left, full height) | right stack ----
        RowLayout {
            id: lower
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 18

            // LEFT — event timeline, fills all remaining height
            GlassPanel {
                Layout.preferredWidth: lower.width * 0.58
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Event timeline"
                Flickable {
                    anchors.fill: parent
                    contentHeight: evCol.implicitHeight
                    clip: true
                    Column {
                        id: evCol
                        width: parent.width
                        spacing: 3
                        Text { visible: ros.events.length === 0; text: "waiting for /rosout…"; color: T.faint; font.pixelSize: 13 }
                        Repeater {
                            model: ros.events
                            Row {
                                width: evCol.width; spacing: 10; topPadding: 4; bottomPadding: 4
                                Rectangle { width: 7; height: 7; radius: 3.5; y: 6; color: T.levelColor(modelData.level) }
                                Text {
                                    width: evCol.width - 24
                                    font.family: "monospace"; font.pixelSize: 13; wrapMode: Text.WordWrap
                                    textFormat: Text.StyledText
                                    text: "<b><font color='" + T.levelColor(modelData.level) + "'>" + T.levelLabel(modelData.level) +
                                          "</font></b> <font color='" + T.faint + "'>" + modelData.name + "</font> <font color='" + T.fg + "'>" + modelData.msg + "</font>"
                                }
                            }
                        }
                    }
                }
            }

            // RIGHT — inference stack + subsystems + llm + run stats, stacked
            ColumnLayout {
                Layout.preferredWidth: lower.width * 0.42
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 18

                // inference stack (fixed-width numeric columns to avoid overlap)
                GlassPanel {
                    Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredHeight: 232; Layout.minimumHeight: 222
                    title: "Inference stack"
                    ColumnLayout {
                        anchors.fill: parent; spacing: 6
                        RowLayout {
                            Layout.fillWidth: true; spacing: 10
                            Kicker { Layout.fillWidth: true; label: "model" }
                            Kicker { Layout.preferredWidth: 52; horizontalAlignment: Text.AlignRight; label: "port" }
                            Kicker { Layout.preferredWidth: 64; horizontalAlignment: Text.AlignRight; label: "vram" }
                            Kicker { Layout.preferredWidth: 52; horizontalAlignment: Text.AlignRight; label: "slots" }
                        }
                        Repeater {
                            model: view.models
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: false
                                Layout.preferredHeight: 34
                                spacing: 10
                                StatusOrb { Layout.alignment: Qt.AlignVCenter; dotColor: "#9aa6ba" }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.alignment: Qt.AlignVCenter
                                    spacing: 1
                                    Text { text: modelData.name; color: T.fg; font.pixelSize: 14; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                                    Text { text: modelData.role; color: T.faint; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                }
                                Text { Layout.preferredWidth: 52; Layout.alignment: Qt.AlignVCenter; horizontalAlignment: Text.AlignRight; text: modelData.port; color: T.dim; font.family: "monospace"; font.pixelSize: 12 }
                                Text { Layout.preferredWidth: 64; Layout.alignment: Qt.AlignVCenter; horizontalAlignment: Text.AlignRight; text: modelData.vram; color: T.dim; font.family: "monospace"; font.pixelSize: 12 }
                                Text { Layout.preferredWidth: 52; Layout.alignment: Qt.AlignVCenter; horizontalAlignment: Text.AlignRight; text: "0"; color: T.faint; font.family: "monospace"; font.pixelSize: 12 }
                            }
                        }
                        Item { Layout.fillHeight: true }
                    }
                }

                // subsystems (compact 2-col grid)
                GlassPanel {
                    Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredHeight: 150
                    title: "Subsystems"
                    GridLayout {
                        anchors.fill: parent
                        columns: 2; columnSpacing: 10; rowSpacing: 10
                        SubRow { name: "Nav2"; ok: ros.hasTelemetry && ros.nav2Ok; known: ros.hasTelemetry }
                        SubRow { name: "MoveIt2"; ok: ros.hasTelemetry && ros.moveit2Ok; known: ros.hasTelemetry }
                        SubRow { name: "Orchestrator"; ok: ros.agentOnline; known: true; okText: "online"; badText: "no beat" }
                        SubRow { name: "DDS shm"; known: false }
                        SubRow { name: "Watchdog"; known: false }
                        SubRow { name: "Entities"; known: false }
                    }
                }

                // last LLM call
                GlassPanel {
                    Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredHeight: 135
                    title: "Last LLM call"
                    ColumnLayout {
                        anchors.fill: parent; spacing: 0
                        StatRow { k: "Model"; v: "gpt-oss-20b" }
                        StatRow { k: "Latency"; v: "—" }
                        StatRow { k: "Tokens in / out"; v: "—" }
                        StatRow { k: "Tool"; v: "—" }
                        Item { Layout.fillHeight: true }
                    }
                }

                // run stats
                GlassPanel {
                    Layout.fillWidth: true; Layout.fillHeight: true; Layout.preferredHeight: 135
                    title: "Run stats"
                    ColumnLayout {
                        anchors.fill: parent; spacing: 0
                        StatRow { k: "Iters total"; v: "—" }
                        StatRow { k: "Completed"; v: "—" }
                        StatRow { k: "Tool errors"; v: "—" }
                        StatRow { k: "lfm2-vl restarts"; v: "—" }
                        Item { Layout.fillHeight: true }
                    }
                }
            }
        }
    }

    // ---- inline helpers ----
    component GaugeCard: GlassPanel {
        id: gcard
        property string gaugeLabel: ""
        property string gaugeAccent: "cyan"
        property real gaugeValue: -1
        property var series: []
        Layout.fillWidth: true
        Layout.fillHeight: true
        ColumnLayout {
            anchors.centerIn: parent
            spacing: 6
            RadialGauge { Layout.alignment: Qt.AlignHCenter; label: gcard.gaugeLabel; accent: gcard.gaugeAccent; value: gcard.gaugeValue }
            Sparkline { Layout.alignment: Qt.AlignHCenter; width: 130; height: 30; accent: gcard.gaugeAccent; values: gcard.series }
        }
    }

    // NB: inline components do not see the file's JS import (T), so use literals.
    component SubRow: Rectangle {
        id: sr
        property string name: ""
        property bool ok: false
        property bool known: false
        property string okText: "online"
        property string badText: "down"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 40
        radius: 11; color: "#12ffffff"; border.color: "#1cffffff"; border.width: 1
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 14; anchors.rightMargin: 14
            Text { text: sr.name; color: "#e9eef7"; font.pixelSize: 14 }
            Item { Layout.fillWidth: true }
            StatusOrb { dotColor: !sr.known ? "#7c8696" : (sr.ok ? "#34d399" : "#fb5a5a"); pulse: sr.known && sr.ok }
            Text { text: !sr.known ? "—" : (sr.ok ? sr.okText : sr.badText); color: "#9aa6ba"; font.pixelSize: 12 }
        }
    }

    component StatRow: RowLayout {
        id: srow
        property string k: ""
        property string v: "—"
        Layout.fillWidth: true
        Layout.fillHeight: false
        Layout.preferredHeight: 30
        Text { text: srow.k; color: "#9aa6ba"; font.pixelSize: 14 }
        Item { Layout.fillWidth: true }
        Text { text: srow.v; color: "#e9eef7"; font.pixelSize: 14; font.bold: true; font.family: "monospace" }
    }
}
