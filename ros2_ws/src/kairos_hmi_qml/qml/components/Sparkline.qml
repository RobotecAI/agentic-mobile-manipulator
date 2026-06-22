import QtQuick 2.15
import "../Theme.js" as T

Canvas {
    id: canvas
    property var values: []
    property string accent: "cyan"
    implicitWidth: 120
    implicitHeight: 34
    onValuesChanged: requestPaint()
    onPaint: {
        var ctx = getContext("2d");
        ctx.reset();
        var n = values.length;
        if (n < 2) return;
        var w = width, h = height;
        var min = Math.min.apply(null, values);
        var max = Math.max.apply(null, values);
        var span = (max - min) || 1;
        var col = T.grad(accent)[0];
        function X(i) { return (i / (n - 1)) * w; }
        function Y(val) { return h - 3 - ((val - min) / span) * (h - 6); }

        // area fill
        ctx.beginPath();
        ctx.moveTo(0, h);
        for (var i = 0; i < n; ++i) ctx.lineTo(X(i), Y(values[i]));
        ctx.lineTo(w, h);
        ctx.closePath();
        var grd = ctx.createLinearGradient(0, 0, 0, h);
        grd.addColorStop(0, col + "55");
        grd.addColorStop(1, col + "00");
        ctx.fillStyle = grd;
        ctx.fill();

        // line
        ctx.beginPath();
        for (var j = 0; j < n; ++j) {
            if (j === 0) ctx.moveTo(X(j), Y(values[j]));
            else ctx.lineTo(X(j), Y(values[j]));
        }
        ctx.lineWidth = 1.8;
        ctx.lineJoin = "round";
        ctx.strokeStyle = col;
        ctx.stroke();

        // head dot
        ctx.beginPath();
        ctx.arc(X(n - 1), Y(values[n - 1]), 2.4, 0, 2 * Math.PI);
        ctx.fillStyle = col;
        ctx.fill();
    }
}
