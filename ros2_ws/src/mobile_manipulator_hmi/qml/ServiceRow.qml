import QtQuick 2.15
import QtQuick.Layouts 1.15

// One row of the Services list. With `columns` set, the detail is split into fixed-width
// columns so rows line up like a table; `header: true` draws the column titles instead.
RowLayout {
    id: row
    property string name
    property string detail
    property var columns: []
    property var columnWidths: [220, 56, 64]
    property string metric
    property string tone: "ok"
    property bool header: false
    readonly property color dim: header ? Theme.faint : Theme.muted
    Layout.fillWidth: true
    Layout.leftMargin: 12
    Layout.rightMargin: 12
    height: 32
    spacing: 10
    Rectangle {
        width: 8; height: 8; radius: 4
        opacity: row.header ? 0 : 1
        color: tone === "ok" ? Theme.ok : tone === "danger" ? Theme.dangerText : tone === "warn" ? Theme.warn : "#4A5363"
    }
    Label2 {
        text: name; Layout.preferredWidth: 150
        font.pixelSize: row.header ? 11 : 13; font.weight: row.header ? Font.DemiBold : Font.Medium
        color: row.header ? Theme.faint : Theme.text
    }
    Label2 {
        visible: row.columns.length === 0
        text: detail; color: row.dim; font.family: Theme.mono; font.pixelSize: 12; Layout.fillWidth: true
    }
    Repeater {
        model: row.columns
        delegate: Label2 {
            text: modelData
            color: row.dim
            font.family: row.header ? Theme.sans : Theme.mono
            font.pixelSize: row.header ? 11 : 12
            font.weight: row.header ? Font.DemiBold : Font.Normal
            Layout.preferredWidth: row.columnWidths[index] || 80
        }
    }
    Item { visible: row.columns.length > 0; Layout.fillWidth: true }
    Label2 {
        text: metric; color: row.header ? Theme.faint : "#AEB7C4"
        font.family: row.header ? Theme.sans : Theme.mono; font.pixelSize: row.header ? 11 : 12
        font.weight: row.header ? Font.DemiBold : Font.Normal
        horizontalAlignment: Text.AlignRight; Layout.preferredWidth: 72
    }
}
