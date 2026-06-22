import QtQuick 2.15
import "../Theme.js" as T

Item {
    id: root
    property real value: -1       // <0 → no data
    property string label: ""
    property string unit: "%"
    property string accent: "cyan"
    property int gaugeSize: 132

    implicitWidth: gaugeSize
    implicitHeight: gaugeSize + 26

    Canvas {
        id: canvas
        width: root.gaugeSize
        height: root.gaugeSize
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter

        property real v: root.value < 0 ? 0 : Math.max(0, Math.min(100, root.value))
        Behavior on v { NumberAnimation { duration: 650; easing.type: Easing.OutCubic } }
        onVChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d");
            ctx.reset();
            var s = root.gaugeSize, cx = s / 2, cy = s / 2, lw = 9, r = (s - lw) / 2 - 1;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, 2 * Math.PI);
            ctx.lineWidth = lw;
            ctx.strokeStyle = "#16ffffff";
            ctx.stroke();
            if (root.value >= 0) {
                var stops = T.grad(root.accent);
                var grd = ctx.createLinearGradient(0, 0, s, s);
                grd.addColorStop(0, stops[0]);
                grd.addColorStop(1, stops[1]);
                var a0 = -Math.PI / 2;
                var a1 = a0 + 2 * Math.PI * (v / 100);
                ctx.beginPath();
                ctx.arc(cx, cy, r, a0, a1);
                ctx.lineWidth = lw;
                ctx.lineCap = "round";
                ctx.strokeStyle = grd;
                ctx.stroke();
            }
        }
    }

    Column {
        anchors.centerIn: canvas
        spacing: -2
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.value < 0 ? "—" : Math.round(canvas.v).toString()
            color: T.fg
            font.pixelSize: 30
            font.bold: true
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.unit
            color: T.faint
            font.pixelSize: 12
        }
    }

    Kicker {
        anchors.top: canvas.bottom
        anchors.topMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        label: root.label
    }
}
