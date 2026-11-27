import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// Set up the warehouse, build tasks, drive the robot by hand.
Item {
    id: page
    property var racks: ["J01","J02","A01","A02","A03","A04","A05","A06","B01","B02","B03","B04","C01","C02","C03","C04",
                         "D01","D02","D03","D04","F01","F02","F03","F04","F05","F06","F07","F08","F09","F10",
                         "G01","G02","G03","G04","G05","G06","H01","H02","I01","I02","K01","K02",
                         "L01","L02","L03","L04","L05","L06","L07","L08","L09","L10"]
    property var pickedRacks: []
    // Shipment items and the wording the orchestrator prompt expects.
    property var items: [["CPU", "one CPU"], ["GPU", "one GPU"], ["Motherboard", "motherboard"],
                         ["Pipes", "pipes"], ["Hammers", "hammers"], ["Nails", "nails"]]
    property var pickedItems: []
    property bool manual: false
    property real speed: 0.4

    function toggle(list, value) {
        return list.indexOf(value) >= 0 ? list.filter(x => x !== value) : list.concat([value])
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: page.width
            spacing: 16

            // 1 · Scene
            Card {
                Layout.fillWidth: true
                Layout.margins: 16
                Layout.bottomMargin: 0
                implicitHeight: sceneCol.implicitHeight + 32
                ColumnLayout {
                    id: sceneCol
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10
                        Label2 { text: "1 · Scene"; font.pixelSize: 16; font.weight: Font.DemiBold }
                        Label2 { text: "Populate the warehouse before assigning tasks. Loaded: " + ros.loadedScene; color: Theme.faint; font.pixelSize: 12; Layout.fillWidth: true }
                        BusyIndicator { running: ros.sceneBusy !== ""; visible: running; implicitWidth: 24; implicitHeight: 24 }
                    }
                    GridLayout {
                        Layout.fillWidth: true
                        columns: 4
                        columnSpacing: 10
                        rowSpacing: 10
                        Repeater {
                            model: [
                                { id: "standard", name: "Standard", desc: "Racks filled with boxes, return packages on the tables. The usual start.", color: "#5B9DFF" },
                                { id: "housekeep", name: "Housekeeping", desc: "Misplaced and fallen items across racks for tidy-up runs.", color: "#3CC6B8" },
                                { id: "anomalies", name: "Anomalies", desc: "Out-of-place objects and a barrel stack for inspection and safety.", color: "#FF9F43" },
                                { id: "cleanup", name: "Cleanup", desc: "Reset the simulation and remove every spawned object.", color: "#FF8A8E" }
                            ]
                            delegate: AbstractButton {
                                id: sceneBtn
                                Layout.fillWidth: true
                                Layout.preferredWidth: 1
                                implicitHeight: 96
                                hoverEnabled: true
                                padding: 14
                                enabled: ros.sceneBusy === ""
                                onClicked: ros.loadScene(modelData.id)
                                readonly property bool loaded: ros.loadedScene === modelData.id
                                readonly property bool busy: ros.sceneBusy === modelData.id
                                background: Rectangle {
                                    radius: 14
                                    color: sceneBtn.loaded ? "#161D28" : sceneBtn.hovered ? "#1A2029" : Theme.panel2
                                    border.width: sceneBtn.loaded || sceneBtn.activeFocus ? 2 : 1
                                    border.color: sceneBtn.loaded || sceneBtn.busy ? modelData.color : Theme.border
                                }
                                contentItem: ColumnLayout {
                                    spacing: 8
                                    RowLayout {
                                        spacing: 8
                                        Icon { name: "building"; color: modelData.color; size: 18 }
                                        Label2 { text: modelData.name; font.weight: Font.Bold; Layout.fillWidth: true }
                                        Label2 {
                                            text: sceneBtn.busy ? "LOADING…" : sceneBtn.loaded ? "LOADED" : ""
                                            color: modelData.color; font.pixelSize: 11; font.weight: Font.DemiBold
                                        }
                                    }
                                    Label2 { text: modelData.desc; color: "#AEB7C4"; font.pixelSize: 12; wrapMode: Text.Wrap; Layout.fillWidth: true; maximumLineCount: 2 }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 16
                Layout.rightMargin: 16
                Layout.bottomMargin: 16
                spacing: 16

                // 2 · Tasks
                Card {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    implicitHeight: tasksCol.implicitHeight + 32
                    ColumnLayout {
                        id: tasksCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14
                        Label2 { text: "2 · Assign tasks"; font.pixelSize: 16; font.weight: Font.DemiBold }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 64
                            radius: 12
                            color: Theme.panel2
                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2
                                    Label2 { text: "Sort package returns"; font.weight: Font.DemiBold }
                                    Label2 { text: "Check each returned package on the tables and route it by condition."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                }
                                Btn { kind: "primary"; text: "Add to queue"; onClicked: ros.sendTask("Do Sort Package Returns") }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: rackCol.implicitHeight + 24
                            radius: 12
                            color: Theme.panel2
                            ColumnLayout {
                                id: rackCol
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 10
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Label2 { text: "Housekeeping"; font.weight: Font.DemiBold }
                                        Label2 { text: "Pick racks to tidy; they are queued in the order you pick them. " + page.pickedRacks.length + " selected."; color: Theme.muted; font.pixelSize: 12; Layout.fillWidth: true }
                                    }
                                    Btn { text: "Clear"; enabled: page.pickedRacks.length > 0; onClicked: page.pickedRacks = [] }
                                    Btn {
                                        kind: "primary"
                                        text: "Queue " + page.pickedRacks.length + " rack" + (page.pickedRacks.length === 1 ? "" : "s")
                                        enabled: page.pickedRacks.length > 0
                                        onClicked: {
                                            for (const r of page.pickedRacks) ros.sendTask("Do Housekeeping of rack " + r)
                                            page.pickedRacks = []
                                        }
                                    }
                                }
                                GridLayout {
                                    Layout.fillWidth: true
                                    columns: 13
                                    columnSpacing: 6
                                    rowSpacing: 6
                                    Repeater {
                                        model: page.racks
                                        delegate: Button {
                                            id: rack
                                            readonly property int order: page.pickedRacks.indexOf(modelData)
                                            Layout.fillWidth: true
                                            implicitHeight: 32
                                            text: modelData
                                            hoverEnabled: true
                                            Accessible.name: "Rack " + modelData + (order >= 0 ? ", selected" : "")
                                            onClicked: page.pickedRacks = page.toggle(page.pickedRacks, modelData)
                                            contentItem: Text {
                                                text: rack.order >= 0 ? (rack.order + 1) + "·" + modelData : modelData
                                                color: rack.order >= 0 ? "#B5D2FF" : Theme.muted
                                                font.family: Theme.mono
                                                font.pixelSize: 11
                                                horizontalAlignment: Text.AlignHCenter
                                                verticalAlignment: Text.AlignVCenter
                                            }
                                            background: Rectangle {
                                                radius: 8
                                                color: rack.order >= 0 ? "#1A2B45" : rack.hovered ? "#161C25" : Theme.chrome
                                                border.color: rack.order >= 0 ? Theme.accent : Theme.border
                                                border.width: rack.activeFocus ? 2 : 1
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: shipCol.implicitHeight + 24
                            radius: 12
                            color: Theme.panel2
                            ColumnLayout {
                                id: shipCol
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10
                                RowLayout {
                                    Layout.fillWidth: true
                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 2
                                        Label2 { text: "Prepare shipment"; font.weight: Font.DemiBold }
                                        Label2 { text: "Collect the selected items onto the shipping table."; color: Theme.muted; font.pixelSize: 12 }
                                    }
                                    Btn {
                                        kind: "primary"
                                        text: "Add to queue"
                                        enabled: page.pickedItems.length > 0
                                        onClicked: {
                                            let prompt = "Prepare shipping of the following items: "
                                            for (const it of page.items) if (page.pickedItems.indexOf(it[0]) >= 0) prompt += it[1] + ", "
                                            ros.sendTask(prompt)
                                        }
                                    }
                                }
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 8
                                    Repeater {
                                        model: page.items
                                        delegate: Chip {
                                            text: (page.pickedItems.indexOf(modelData[0]) >= 0 ? "✓ " : "+ ") + modelData[0]
                                            selected: page.pickedItems.indexOf(modelData[0]) >= 0
                                            implicitHeight: 36
                                            onClicked: page.pickedItems = page.toggle(page.pickedItems, modelData[0])
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // 3 · Manual control
                Card {
                    Layout.preferredWidth: Math.max(340, page.width * 0.3)
                    Layout.alignment: Qt.AlignTop
                    implicitHeight: manualCol.implicitHeight + 32
                    focus: page.manual
                    Keys.onPressed: {
                        if (!page.manual || event.isAutoRepeat) return
                        const keys = { [Qt.Key_W]: [1, 0], [Qt.Key_S]: [-1, 0], [Qt.Key_A]: [0, 1], [Qt.Key_D]: [0, -1], [Qt.Key_Space]: [0, 0] }
                        if (keys[event.key] !== undefined) { driver.start(keys[event.key][0], keys[event.key][1]); event.accepted = true }
                    }
                    Keys.onReleased: if (!event.isAutoRepeat && page.manual) driver.stop()

                    ColumnLayout {
                        id: manualCol
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 14
                        RowLayout {
                            Layout.fillWidth: true
                            Label2 { text: "3 · Manual control"; font.pixelSize: 16; font.weight: Font.DemiBold; Layout.fillWidth: true }
                            Chip {
                                text: page.manual ? "Manual drive ON" : "Enable"
                                selected: page.manual
                                onClicked: { page.manual = !page.manual; if (!page.manual) driver.stop() }
                            }
                        }
                        Label2 {
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                            text: "Drives the base directly over /cmd_vel. Agents keep running, so pause missions first. Keys: W A S D, space = stop."
                            color: Theme.muted
                            font.pixelSize: 12
                        }
                        // Publishes the held direction at 10 Hz; stops on release.
                        Timer {
                            id: driver
                            property real lin: 0
                            property real ang: 0
                            interval: 100
                            repeat: true
                            onTriggered: ros.drive(lin * page.speed, ang * page.speed * 1.5)
                            function start(l, a) { lin = l; ang = a; ros.drive(l * page.speed, a * page.speed * 1.5); restart() }
                            function stop() { running = false; lin = 0; ang = 0; ros.drive(0, 0) }
                        }
                        GridLayout {
                            Layout.alignment: Qt.AlignHCenter
                            columns: 3
                            columnSpacing: 8
                            rowSpacing: 8
                            enabled: page.manual
                            opacity: enabled ? 1 : 0.4
                            Repeater {
                                model: [
                                    { icon: "", l: 0, a: 0 }, { icon: "up", l: 1, a: 0, label: "Forward" }, { icon: "", l: 0, a: 0 },
                                    { icon: "left", l: 0, a: 1, label: "Turn left" }, { icon: "stop", l: 0, a: 0, label: "Stop" }, { icon: "right", l: 0, a: -1, label: "Turn right" },
                                    { icon: "", l: 0, a: 0 }, { icon: "down", l: -1, a: 0, label: "Backward" }, { icon: "", l: 0, a: 0 }
                                ]
                                delegate: Item {
                                    implicitWidth: 68
                                    implicitHeight: 64
                                    Button {
                                        id: pad
                                        anchors.fill: parent
                                        visible: modelData.icon !== ""
                                        Accessible.name: modelData.label || ""
                                        onPressed: modelData.icon === "stop" ? driver.stop() : driver.start(modelData.l, modelData.a)
                                        onReleased: driver.stop()
                                        onCanceled: driver.stop()
                                        contentItem: Item { Icon { anchors.centerIn: parent; name: modelData.icon; size: 22; strokeWidth: 2; color: modelData.icon === "stop" ? Theme.dangerText : Theme.text } }
                                        background: Rectangle {
                                            radius: 12
                                            color: pad.down ? Theme.accentBg : modelData.icon === "stop" ? Theme.dangerBg : Theme.panel2
                                            border.color: modelData.icon === "stop" ? "#4A2326" : Theme.borderStrong
                                        }
                                    }
                                }
                            }
                        }
                        RowLayout {
                            Layout.fillWidth: true
                            Label2 { text: "Speed"; color: Theme.muted; font.pixelSize: 12 }
                            Slider {
                                id: speedSlider
                                Layout.fillWidth: true
                                from: 0.1; to: 1.0; stepSize: 0.1
                                value: page.speed
                                onMoved: page.speed = value
                                Accessible.name: "Drive speed"
                            }
                            Label2 { text: page.speed.toFixed(1) + " m/s"; font.family: Theme.mono; font.pixelSize: 12 }
                        }
                    }
                }
            }
        }
    }
}
