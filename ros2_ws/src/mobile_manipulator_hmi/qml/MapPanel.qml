import QtQuick 2.15
import QtQuick.Layouts 1.15

// Static map with the robot and its plan. Double-click sends a navigation goal.
Card {
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 10
            Layout.topMargin: 14
            Layout.bottomMargin: 14
            Label2 { text: "Map"; font.pixelSize: 13; font.weight: Font.DemiBold }
            Item { Layout.fillWidth: true }
            Label2 { text: ros.robotPose; color: Theme.faint; font.family: Theme.mono; font.pixelSize: 11 }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.border }
        Item {
            id: area
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            // Map image scaled to fit; overlay uses the same transform.
            readonly property real s: ros.mapSize.width > 0
                ? Math.min(width / ros.mapSize.width, height / ros.mapSize.height) : 1
            readonly property real ox: (width - ros.mapSize.width * s) / 2
            readonly property real oy: (height - ros.mapSize.height * s) / 2

            Image {
                x: area.ox; y: area.oy
                width: ros.mapSize.width * area.s
                height: ros.mapSize.height * area.s
                source: ros.mapFrame > 0 ? "image://ros/map?" + ros.mapFrame : ""
                cache: false
                smooth: false
            }
            Canvas {
                id: overlay
                anchors.fill: parent
                property var path: ros.pathPixels
                property point robot: ros.robotPixel
                onPathChanged: requestPaint()
                onRobotChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d")
                    ctx.reset()
                    const tx = p => area.ox + p.x * area.s
                    const ty = p => area.oy + p.y * area.s
                    if (path.length > 1) {
                        ctx.strokeStyle = "#5B9DFF"
                        ctx.lineWidth = 2.5
                        ctx.setLineDash([5, 4])
                        ctx.beginPath()
                        ctx.moveTo(tx(path[0]), ty(path[0]))
                        for (let i = 1; i < path.length; ++i) ctx.lineTo(tx(path[i]), ty(path[i]))
                        ctx.stroke()
                        ctx.setLineDash([])
                    }
                    if (robot.x >= 0) {
                        const x = tx(robot), y = ty(robot)
                        ctx.fillStyle = "#3CC6B8"
                        ctx.beginPath(); ctx.arc(x, y, 8, 0, 2 * Math.PI); ctx.fill()
                        ctx.strokeStyle = "#0B0E13"; ctx.lineWidth = 2.5
                        ctx.beginPath(); ctx.moveTo(x, y)
                        ctx.lineTo(x + 10 * Math.cos(-ros.robotYaw), y + 10 * Math.sin(-ros.robotYaw)); ctx.stroke()
                    }
                }
            }
            MouseArea {
                anchors.fill: parent
                onDoubleClicked: {
                    if (ros.mapSize.width <= 0) return
                    ros.sendGoal((mouse.x - area.ox) / area.s, (mouse.y - area.oy) / area.s)
                }
            }
            Label2 {
                anchors.centerIn: parent
                visible: ros.mapFrame === 0
                text: "Waiting for the map…"
                color: Theme.faint
            }
            Label2 {
                anchors.left: parent.left; anchors.bottom: parent.bottom; anchors.margins: 8
                visible: ros.mapFrame > 0
                text: "double-click to send a goal"
                color: Theme.faint; font.pixelSize: 11
            }
        }
    }
}
