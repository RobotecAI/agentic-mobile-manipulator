import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.15
import QtGraphicalEffects 1.15
import "../components"
import "../Theme.js" as T

Item {
    id: view

    property var racks: ["J01", "B02", "C03", "A04", "F01", "L07"]
    property int rackIdx: 0
    property var sel: ({})
    readonly property var items: ["hammers", "CPU", "GPU", "pipes", "nails", "motherboard"]

    function shipmentPrompt() {
        var chosen = [];
        for (var i = 0; i < items.length; ++i) if (sel[items[i]]) chosen.push(items[i]);
        return "Prepare shipping of the following items: " + chosen.join(", ");
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 18

        // ---- hero command ----
        GlassPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 188
            glow: true
            ColumnLayout {
                anchors.fill: parent
                spacing: 10
                Kicker { label: "natural-language command" }
                Row {
                    spacing: 8
                    Text { text: "Tell the robot "; color: T.fg; font.pixelSize: 26; font.bold: true }
                    Item {
                        width: gt.implicitWidth; height: gt.implicitHeight
                        Text { id: gt; text: "anything"; font.pixelSize: 26; font.bold: true; visible: false }
                        LinearGradient {
                            anchors.fill: gt; source: gt
                            start: Qt.point(0, 0); end: Qt.point(gt.width, 0)
                            gradient: Gradient {
                                GradientStop { position: 0; color: T.cyan }
                                GradientStop { position: 1; color: T.violet }
                            }
                        }
                    }
                    Text { text: "."; color: T.fg; font.pixelSize: 26; font.bold: true }
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12
                    TextField {
                        id: prompt
                        Layout.fillWidth: true
                        placeholderText: "e.g. Sort the returned packages, then inspect aisle C for hazards"
                        color: T.fg
                        placeholderTextColor: T.faint
                        font.pixelSize: 15
                        leftPadding: 14; rightPadding: 14; topPadding: 13; bottomPadding: 13
                        selectionColor: T.cyan
                        background: Rectangle {
                            radius: 11; color: "#0c1422"
                            border.color: prompt.activeFocus ? T.cyan : T.line
                            border.width: 1
                        }
                        onAccepted: { ros.sendPrompt(text); text = "" }
                    }
                    AppButton { variant: "primary"; text: "Run task"; onClicked: { ros.sendPrompt(prompt.text); prompt.text = "" } }
                }
                Flow {
                    Layout.fillWidth: true
                    spacing: 8
                    Repeater {
                        model: ["Bring two hammers to the packing table", "Check aisle C for spills", "Restock rack B02"]
                        Rectangle {
                            radius: height / 2; color: T.panelHi; border.color: T.line; border.width: 1
                            height: 30; width: t.implicitWidth + 24
                            Text { id: t; anchors.centerIn: parent; text: modelData; color: T.dim; font.pixelSize: 12 }
                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: ros.sendPrompt(modelData) }
                        }
                    }
                }
            }
        }

        // ---- dispatch a mission ----
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Kicker { label: "dispatch a mission" }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
                ActionCard {
                    Layout.fillWidth: true; Layout.fillHeight: true; accent: "cyan"; glyph: "⇅"
                    title: "Sort package returns"
                    desc: "Drive to the returns area and sort returned packages onto the correct racks."
                    cta: "Start sorting"
                    onRun: ros.sendPrompt("Do Sort Package Returns")
                }
                ActionCard {
                    Layout.fillWidth: true; Layout.fillHeight: true; accent: "violet"; glyph: "✦"
                    title: "Housekeeping"
                    desc: "Tidy a single rack — the robot returns stray items to their slots."
                    hint: "Next rack: " + view.racks[view.rackIdx]
                    cta: "Tidy next rack"
                    onRun: { ros.sendPrompt("Do Housekeeping of rack " + view.racks[view.rackIdx]); view.rackIdx = (view.rackIdx + 1) % view.racks.length }
                }
                ActionCard {
                    Layout.fillWidth: true; Layout.fillHeight: true; accent: "amber"; glyph: "⚠"
                    title: "Inspect for hazards"
                    desc: "Patrol with the VLM and report spills, blockages and anomalies on the Mission view."
                    cta: "Begin inspection"
                    onRun: ros.sendPrompt("Drive the warehouse and inspect for hazards such as spills, blocked paths or misplaced items. Report any anomalies you find.")
                }
            }
        }

        // ---- stage the warehouse ----
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Kicker { label: "stage the warehouse" }
            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
                ScenarioTile { Layout.fillWidth: true; Layout.fillHeight: true; accent: "cyan"; glyph: "▦"; title: "Standard"; desc: "Returns to sort and routine housekeeping."; onSpawn: ros.runScenario("standard") }
                ScenarioTile { Layout.fillWidth: true; Layout.fillHeight: true; accent: "violet"; glyph: "✦"; title: "Housekeeping"; desc: "Items left out of place across racks."; onSpawn: ros.runScenario("housekeep") }
                ScenarioTile { Layout.fillWidth: true; Layout.fillHeight: true; accent: "amber"; glyph: "⚠"; title: "Anomalies"; desc: "Spills, blocked paths and hazards."; onSpawn: ros.runScenario("anomalies") }
                ScenarioTile { Layout.fillWidth: true; Layout.fillHeight: true; accent: "emerald"; glyph: "⌫"; title: "Cleanup"; desc: "Reset to an empty, ordered warehouse."; onSpawn: ros.runScenario("cleanup") }
            }
        }

        // ---- shipment + manual drive ----
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16

            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredWidth: 2
                Layout.fillHeight: true
                title: "Prepare a shipment"
                ColumnLayout {
                    anchors.fill: parent; spacing: 12
                    Text { Layout.fillWidth: true; text: "Select items to pick, pack and stage for shipping."; color: T.dim; font.pixelSize: 13 }
                    Flow {
                        Layout.fillWidth: true; spacing: 10
                        Repeater {
                            model: view.items
                            Rectangle {
                                property bool on: view.sel[modelData] === true
                                radius: height / 2; height: 36; width: it.implicitWidth + 30
                                color: on ? T.cyan : T.panelHi
                                border.color: T.line; border.width: 1
                                Text { id: it; anchors.centerIn: parent; text: modelData; color: parent.on ? "#04121a" : T.dim; font.pixelSize: 13 }
                                MouseArea {
                                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                    onClicked: { var s = view.sel; s[modelData] = !s[modelData]; view.sel = Object.assign({}, s) }
                                }
                            }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    AppButton { variant: "primary"; text: "Prepare shipment"; onClicked: ros.sendPrompt(view.shipmentPrompt()) }
                }
            }

            GlassPanel {
                Layout.fillWidth: true
                Layout.preferredWidth: 1
                Layout.fillHeight: true
                title: "Manual drive"
                GridLayout {
                    anchors.centerIn: parent
                    columns: 3; rowSpacing: 8; columnSpacing: 8
                    Item { width: 56; height: 52 }
                    DpadButton { glyph: "▲"; onDown: ros.teleop(0.5, 0); onUp: ros.teleop(0, 0) }
                    Item { width: 56; height: 52 }
                    DpadButton { glyph: "◀"; onDown: ros.teleop(0, 0.5); onUp: ros.teleop(0, 0) }
                    Rectangle { width: 56; height: 52; radius: 12; color: "#0a0f1a"; border.color: T.line; Text { anchors.centerIn: parent; text: "•"; color: T.faint } }
                    DpadButton { glyph: "▶"; onDown: ros.teleop(0, -0.5); onUp: ros.teleop(0, 0) }
                    Item { width: 56; height: 52 }
                    DpadButton { glyph: "▼"; onDown: ros.teleop(-0.5, 0); onUp: ros.teleop(0, 0) }
                    Item { width: 56; height: 52 }
                }
            }
        }
    }
}
