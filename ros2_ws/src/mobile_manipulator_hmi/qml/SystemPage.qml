import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Resources, services and logs.
Item {
    id: page
    property string level: "WARN+"
    property string query: ""
    readonly property var levelRank: ({ DEBUG: 0, INFO: 1, WARN: 2, ERROR: 3, FATAL: 4 })
    readonly property var shownLogs: ros.logs.filter(l => {
        const okLevel = page.level === "All" || (page.level === "WARN+" ? levelRank[l.level] >= 2 : l.level === page.level)
        const q = page.query.toLowerCase()
        return okLevel && (q === "" || (l.node + " " + l.msg).toLowerCase().indexOf(q) >= 0)
    })
    readonly property var tones: ({ CPU: "#5B9DFF", GPU: "#B08CFF", NPU: "#3CC6B8", RAM: "#FFB547" })
    readonly property var levelColors: ({ DEBUG: Theme.muted, INFO: Theme.accentSoft, WARN: Theme.warn, ERROR: Theme.dangerText, FATAL: Theme.dangerText })

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 16

        // Resource tiles
        GridLayout {
            Layout.fillWidth: true
            columns: 4
            columnSpacing: 12
            Repeater {
                model: ros.resources
                delegate: Card {
                    Layout.fillWidth: true
                    Layout.preferredWidth: 1
                    implicitHeight: 128
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Label2 { text: modelData.name; font.weight: Font.DemiBold; Layout.fillWidth: true }
                            Label2 {
                                text: modelData.value < 0 ? "n/a" : Math.round(modelData.value) + "%"
                                color: modelData.value < 0 ? Theme.faint : page.tones[modelData.name]
                                font.family: Theme.mono
                                font.pixelSize: 22
                                font.weight: Font.DemiBold
                            }
                        }
                        Sparkline {
                            visible: modelData.value >= 0
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            values: modelData.history
                            color: page.tones[modelData.name]
                        }
                        Item { visible: modelData.value < 0; Layout.fillHeight: true }
                        Label2 {
                            text: modelData.value < 0 ? "not reported by utilization_node" : "last " + modelData.history.length * 5 + " s"
                            color: Theme.faint
                            font.pixelSize: 11
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 16

            // Services
            Card {
                Layout.fillHeight: true
                Layout.preferredWidth: Math.max(420, page.width * 0.42)
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    Label2 { text: "Services"; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.margins: 14 }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ColumnLayout {
                            width: parent.width
                            spacing: 2
                            Label2 { text: "AGENTS"; color: Theme.faint; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.margins: 12; Layout.bottomMargin: 2 }
                            Repeater {
                                model: ros.agents.filter(a => a.group !== "executor")
                                delegate: ServiceRow {
                                    name: modelData.name
                                    detail: modelData.heartbeatAge >= 0 ? "heartbeat " + modelData.heartbeatAge.toFixed(1) + " s ago" : "no heartbeat yet"
                                    metric: modelData.state
                                    tone: modelData.state === "working" || modelData.state === "idle" ? "ok" : modelData.state === "offline" ? "danger" : "neutral"
                                }
                            }
                            Label2 { text: "INFERENCE · config.toml"; color: Theme.faint; font.pixelSize: 11; font.weight: Font.DemiBold; Layout.margins: 12; Layout.bottomMargin: 2 }
                            Repeater {
                                model: ros.endpoints
                                delegate: ServiceRow {
                                    name: modelData.name
                                    detail: modelData.model + " · " + modelData.backend + " · :" + modelData.port
                                    metric: !modelData.checked ? "…" : modelData.ok ? modelData.latencyMs + " ms" : "down"
                                    tone: !modelData.checked ? "neutral" : modelData.ok ? "ok" : "danger"
                                }
                            }
                        }
                    }
                }
            }

            // Logs
            Card {
                Layout.fillWidth: true
                Layout.fillHeight: true
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.margins: 12
                        spacing: 6
                        Label2 { text: "Logs"; font.pixelSize: 15; font.weight: Font.DemiBold; Layout.rightMargin: 6 }
                        Repeater {
                            model: ["WARN+", "All", "ERROR", "WARN", "INFO", "DEBUG"]
                            delegate: Chip { text: modelData; selected: page.level === modelData; onClicked: page.level = modelData }
                        }
                        Item { Layout.fillWidth: true }
                        TextField {
                            Layout.preferredWidth: 200
                            placeholderText: "Filter by node or text"
                            placeholderTextColor: Theme.faint
                            color: Theme.text
                            font.family: Theme.sans
                            font.pixelSize: 12
                            Accessible.name: "Filter logs"
                            onTextChanged: page.query = text
                            background: Rectangle { radius: 8; color: Theme.bg; border.color: Theme.borderStrong }
                        }
                    }
                    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
                    ListView {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.margins: 6
                        clip: true
                        model: page.shownLogs
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Rectangle {
                            width: ListView.view.width
                            height: logRow.implicitHeight + 6
                            radius: 6
                            color: modelData.level === "ERROR" || modelData.level === "FATAL" ? Theme.dangerBg : modelData.level === "WARN" ? "#1E1A12" : "transparent"
                            RowLayout {
                                id: logRow
                                anchors.left: parent.left
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                anchors.leftMargin: 8
                                anchors.rightMargin: 8
                                spacing: 10
                                Text { text: modelData.t; color: "#7D8796"; font.family: Theme.mono; font.pixelSize: 12; Layout.preferredWidth: 64; Layout.alignment: Qt.AlignTop }
                                Text { text: modelData.level; color: page.levelColors[modelData.level]; font.family: Theme.mono; font.pixelSize: 12; font.weight: Font.DemiBold; Layout.preferredWidth: 48; Layout.alignment: Qt.AlignTop }
                                Text { text: modelData.node; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 12; elide: Text.ElideRight; Layout.preferredWidth: 150; Layout.alignment: Qt.AlignTop }
                                Text { text: modelData.msg; color: "#D5DCE6"; font.family: Theme.mono; font.pixelSize: 12; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true; maximumLineCount: 4; elide: Text.ElideRight }
                            }
                        }
                        Label2 { anchors.centerIn: parent; visible: parent.count === 0; text: "No log lines match."; color: Theme.faint }
                    }
                }
            }
        }
    }
}
