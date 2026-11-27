import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

// One agent on the flow graph: state, what it is doing, click to filter the trace.
AbstractButton {
    id: card
    property var agent: ({})
    property bool selected: false
    readonly property color stateColor: agent.state === "working" ? Theme.accent : agent.state === "idle" ? "#7D8796"
                                      : agent.state === "offline" ? Theme.dangerText : "#4A5363"
    implicitHeight: col.implicitHeight + 24
    hoverEnabled: true
    padding: 12
    Accessible.name: agent.name + ", " + agent.state

    background: Rectangle {
        radius: 14
        color: agent.state === "working" ? "#15202F" : Theme.panel2
        border.width: card.selected || card.activeFocus ? 2 : 1
        border.color: card.selected ? agent.color : agent.state === "working" ? "#2F4D7A" : Theme.border
    }
    contentItem: ColumnLayout {
        id: col
        spacing: 6
        RowLayout {
            spacing: 8
            Rectangle { width: 10; height: 10; radius: 5; color: card.agent.color }
            Label2 { text: card.agent.name; font.pixelSize: 13; font.weight: Font.Bold; Layout.fillWidth: true }
        }
        Rectangle {
            implicitWidth: stateRow.implicitWidth + 16
            height: 20
            radius: 10
            color: Theme.bg
            Row {
                id: stateRow
                anchors.centerIn: parent
                spacing: 6
                Rectangle { width: 6; height: 6; radius: 3; color: card.stateColor; anchors.verticalCenter: parent.verticalCenter }
                Text { text: card.agent.state; color: card.stateColor; font.family: Theme.sans; font.pixelSize: 11; font.weight: Font.DemiBold }
            }
        }
        Label2 {
            Layout.fillWidth: true
            text: card.agent.doing || ""
            color: "#AEB7C4"
            font.pixelSize: 12
            wrapMode: Text.Wrap
            maximumLineCount: 2
        }
    }
}
