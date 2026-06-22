import QtQuick 2.15
import QtQuick.Layouts 1.15
import "../components"
import "../Theme.js" as T

Item {
    id: view
    property string baseCam: "base"

    ColumnLayout {
        id: rootCol
        anchors.fill: parent
        spacing: 14

        // ===== Agent telemetry strip (~11% tall) =====
        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: rootCol.height * 0.12
            Layout.minimumHeight: 96
            title: "Agent telemetry"
            pad: 14
            RowLayout {
                anchors.fill: parent
                spacing: 10
                CompactStat { Layout.fillWidth: true; label: "Drive"; value: "IDLE"; valueColor: "#34d399" }
                CompactStat { Layout.fillWidth: true; label: "Task"; value: ros.currentTask ? ros.currentTask.substring(0, 16) : "—" }
                CompactStat { Layout.fillWidth: true; label: "Iter"; value: "0 / 0" }
                CompactStat { Layout.fillWidth: true; label: "Phase"; value: "—" }
                CompactStat { Layout.fillWidth: true; label: "Elapsed"; value: "00:00" }
                CompactStat { Layout.fillWidth: true; label: "Drift"; value: "0"; valueColor: "#34d399" }
                AppButton { Layout.alignment: Qt.AlignVCenter; variant: "primary"; text: "Reset scene"; onClicked: ros.restart() }
            }
        }

        // ===== main area (~88%) : left 50% | Agent 25% | VLM 25% =====
        RowLayout {
            id: mainRow
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 14

            // ---------- LEFT 50% : videos (top) + navigation (bottom) ----------
            ColumnLayout {
                id: leftCol
                Layout.preferredWidth: mainRow.width * 0.5
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 14

                // videos (top, ~55%)
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.preferredHeight: (leftCol.height - 14) * 0.55
                    Layout.minimumHeight: 220
                    title: "Live cameras"
                    RowLayout {
                        anchors.fill: parent
                        spacing: 12
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            CameraTile {
                                anchors.centerIn: parent
                                height: Math.min(parent.height, parent.width * 9 / 16)
                                width: height * 16 / 9
                                camName: view.baseCam
                            }
                            Kicker {
                                anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 10
                                label: view.baseCam === "base" ? "base camera" : "wrist camera"
                            }
                            Row {
                                anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 10
                                spacing: 4
                                Repeater {
                                    model: ["base", "wrist"]
                                    Rectangle {
                                        width: 26; height: 22; radius: 6
                                        property bool on: view.baseCam === modelData
                                        color: on ? T.cyan : "#0c1422cc"
                                        border.color: on ? T.cyan : T.line
                                        Text { anchors.centerIn: parent; text: index + 1; font.pixelSize: 11; font.bold: true; color: parent.on ? "#04121a" : T.dim }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: view.baseCam = modelData }
                                    }
                                }
                            }
                        }
                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            CameraTile {
                                anchors.centerIn: parent
                                height: Math.min(parent.height, parent.width * 9 / 16)
                                width: height * 16 / 9
                                camName: "top"
                            }
                            Kicker {
                                anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 10
                                label: "top view"
                            }
                        }
                    }
                }

                // navigation (bottom-left, ~45%)
                GlassPanel {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 200
                    title: "Navigation"
                    Rectangle {
                        anchors.fill: parent
                        radius: 12
                        color: "#0a1018"
                        border.color: T.line
                        clip: true
                        Image {
                            anchors.fill: parent
                            fillMode: Image.PreserveAspectFit
                            cache: false
                            source: "image://kairos/map?" + ros.mapRev
                        }
                        Chip {
                            anchors.left: parent.left; anchors.top: parent.top; anchors.margins: 12
                            dotColor: T.cyan; pulse: true; text: "autonomous nav"
                        }
                        Kicker {
                            anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 14
                            label: "occupancy + plan"
                        }
                    }
                }
            }

            // ---------- AGENT 25% ----------
            GlassPanel {
                Layout.preferredWidth: mainRow.width * 0.25
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "Agent"
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    Kicker { label: "current task" }
                    Text {
                        Layout.fillWidth: true
                        text: ros.currentTask || "Awaiting dispatch…"
                        color: T.fg; font.pixelSize: 17; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight
                    }
                    Rectangle {
                        Layout.fillWidth: true
                        radius: 10; color: "#0a1422"; border.color: T.line
                        implicitHeight: actionCol.implicitHeight + 22
                        ColumnLayout {
                            id: actionCol
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 11; spacing: 5
                            RowLayout {
                                spacing: 8
                                StatusOrb { dotColor: T.cyan; pulse: ros.currentAction.length > 0 }
                                Kicker { label: "current action" }
                            }
                            Text {
                                Layout.fillWidth: true
                                text: ros.currentAction || "idle"
                                color: T.cyan; font.pixelSize: 13; font.family: "monospace"; wrapMode: Text.WordWrap; maximumLineCount: 3; elide: Text.ElideRight
                            }
                        }
                    }
                    Kicker { label: "plan & history" }
                    Flickable {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        contentHeight: planCol.implicitHeight; clip: true
                        Column {
                            id: planCol
                            width: parent.width; spacing: 0
                            Repeater {
                                model: ros.pastSteps
                                Row {
                                    spacing: 10; bottomPadding: 9
                                    Rectangle { width: 9; height: 9; radius: 4.5; color: "#40ffffff"; y: 3 }
                                    Text { text: modelData; color: T.faint; font.pixelSize: 13; font.strikeout: true; width: planCol.width - 24; wrapMode: Text.WordWrap }
                                }
                            }
                            Repeater {
                                model: ros.taskQueue
                                Row {
                                    spacing: 10; bottomPadding: 9
                                    Rectangle { width: 9; height: 9; radius: 4.5; color: index === 0 ? T.cyan : "#66ffffff"; y: 3 }
                                    Text { text: modelData; color: index === 0 ? T.fg : T.dim; font.pixelSize: 13; width: planCol.width - 24; wrapMode: Text.WordWrap }
                                }
                            }
                        }
                    }
                }
            }

            // ---------- VLM 25% ----------
            GlassPanel {
                Layout.preferredWidth: mainRow.width * 0.25
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: "VLM stream"
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 10
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2; columnSpacing: 10; rowSpacing: 10
                        StatTile { Layout.fillWidth: true; label: "Drives"; value: "0" }
                        StatTile { Layout.fillWidth: true; label: "Success"; value: "—" }
                        StatTile { Layout.fillWidth: true; label: "Avg drift"; value: "—" }
                        StatTile { Layout.fillWidth: true; label: "Avg dur"; value: "—" }
                    }
                    Text {
                        Layout.fillWidth: true
                        text: "Live scene descriptions and hazard analysis from the vision-language model."
                        color: T.dim; font.pixelSize: 13; wrapMode: Text.WordWrap
                    }
                    Flickable {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        contentHeight: vlmCol.implicitHeight; clip: true
                        Column {
                            id: vlmCol
                            width: parent.width; spacing: 10
                            Text {
                                visible: ros.vlmFeed.length === 0
                                text: "waiting for /vlm_topic…"; color: T.faint; font.pixelSize: 13
                            }
                            Repeater {
                                model: ros.vlmFeed
                                Rectangle {
                                    width: vlmCol.width
                                    radius: 12; color: "#0a1422"; border.color: T.line
                                    implicitHeight: vc.implicitHeight + 24
                                    Column {
                                        id: vc
                                        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                                        anchors.margins: 12; spacing: 7
                                        Rectangle {
                                            radius: 5
                                            color: modelData.source === "Safety" ? T.blue : T.amber
                                            implicitWidth: badge.implicitWidth + 14; implicitHeight: 18
                                            Text { id: badge; anchors.centerIn: parent; text: (modelData.source || "vlm").toUpperCase(); color: "#04121a"; font.pixelSize: 10; font.bold: true }
                                        }
                                        Text { width: parent.width; text: modelData.description; color: T.fg; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // compact telemetry tile (literals only — inline components don't see T)
    component CompactStat: ColumnLayout {
        property string label: ""
        property string value: "—"
        property color valueColor: "#e9eef7"
        spacing: 3
        Text {
            text: label.toUpperCase()
            color: "#6b7686"; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.4; font.family: "monospace"
        }
        Text {
            Layout.fillWidth: true
            text: value; color: valueColor; font.pixelSize: 19; font.bold: true; elide: Text.ElideRight
        }
    }
}
