import QtQuick 2.15

// Line chart of 0-100 values.
Canvas {
    id: root
    property var values: []
    property color color: Theme.accent
    onValuesChanged: requestPaint()
    onWidthChanged: requestPaint()
    onPaint: {
        const ctx = getContext("2d")
        ctx.reset()
        if (!values || values.length < 2) return
        ctx.strokeStyle = color
        ctx.lineWidth = 1.6
        ctx.lineJoin = "round"
        ctx.beginPath()
        for (let i = 0; i < values.length; ++i) {
            const x = i * (width - 2) / (values.length - 1) + 1
            const y = height - 2 - Math.max(0, Math.min(100, values[i])) / 100 * (height - 4)
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.stroke()
    }
}
