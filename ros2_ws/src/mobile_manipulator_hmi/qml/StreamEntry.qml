import QtQuick 2.15
import QtQuick.Layouts 1.15

// One agent stream entry. Roles come from AgentEventModel.
Item {
    id: root
    property bool selected: false
    signal clicked()
    readonly property color agentColor: ros.agentColor(model.agent)
    width: ListView.view ? ListView.view.width : 300
    height: body.implicitHeight + 14

    Rectangle {
        anchors.fill: parent
        anchors.bottomMargin: 2
        radius: 10
        color: root.selected ? "#151C27" : mouse.containsMouse ? "#141920" : "transparent"
    }
    MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: root.clicked() }

    // Timeline rail
    Rectangle { x: 14; y: 8; width: 10; height: 10; radius: 5; color: root.agentColor }
    Rectangle { x: 18; y: 22; width: 2; height: root.height - 24; color: Theme.border }

    Column {
        id: body
        x: 34
        y: 4
        width: root.width - 44
        spacing: 6

        RowLayout {
            width: parent.width
            spacing: 8
            Label2 { text: model.agent; color: root.agentColor; font.pixelSize: 13; font.weight: Font.DemiBold }
            Label2 {
                text: model.kind === "tool" ? "tool call" : model.kind === "vlm" ? "finding" : model.kind
                color: Theme.faint; font.pixelSize: 11; font.capitalization: Font.AllUppercase; font.letterSpacing: 0.5
            }
            Item { Layout.fillWidth: true }
            Label2 { visible: model.tokens !== ""; text: model.tokens; color: Theme.faint; font.family: Theme.mono; font.pixelSize: 11 }
            Label2 { text: model.time; color: Theme.faint; font.family: Theme.mono; font.pixelSize: 11 }
        }

        // Text / thinking / task marker
        Text {
            visible: model.kind === "text" || model.kind === "thinking" || model.kind === "task"
            width: parent.width
            text: model.text + (model.streaming ? " ▍" : "")
            wrapMode: Text.Wrap
            textFormat: Text.PlainText
            color: model.kind === "text" ? "#D5DCE6" : Theme.muted
            font.family: Theme.sans
            font.pixelSize: model.kind === "thinking" ? 12.5 : 13
            font.italic: model.kind === "thinking"
            maximumLineCount: root.selected ? 400 : 12
            elide: Text.ElideRight
            lineHeight: 1.15
        }

        // Tool call
        Rectangle {
            visible: model.kind === "tool"
            width: parent.width
            height: visible ? toolCol.height : 0
            radius: 10
            color: Theme.bg
            border.color: Theme.border
            Column {
                id: toolCol
                width: parent.width
                bottomPadding: 8
                Item {
                    width: parent.width
                    height: 34
                    Icon { x: 8; anchors.verticalCenter: parent.verticalCenter; name: "tool"; size: 14; strokeWidth: 2 }
                    Label2 {
                        x: 30; width: parent.width - 120
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.toolName; font.family: Theme.mono; font.pixelSize: 12
                    }
                    Label2 {
                        anchors.right: parent.right; anchors.rightMargin: 8
                        anchors.verticalCenter: parent.verticalCenter
                        text: model.status === "ok" ? "✓ " + (model.durationMs / 1000).toFixed(1) + " s"
                            : model.status === "error" ? "failed" : model.status === "running" ? "running…" : ""
                        color: model.status === "ok" ? Theme.ok : model.status === "error" ? Theme.dangerText : Theme.warn
                        font.pixelSize: 11; font.weight: Font.DemiBold
                    }
                }
                Rectangle { width: parent.width; height: 1; color: "#1B212B"; visible: model.text !== "" }
                Text {
                    visible: model.text !== ""
                    x: 8; width: parent.width - 16
                    topPadding: 8
                    text: model.text
                    wrapMode: Text.WrapAnywhere
                    color: "#AEB7C4"
                    font.family: Theme.mono
                    font.pixelSize: 12
                    maximumLineCount: root.selected ? 200 : 6
                    elide: Text.ElideRight
                }
                Text {
                    visible: model.result !== ""
                    x: 8; width: parent.width - 16
                    topPadding: 6
                    text: "→ " + model.result
                    wrapMode: Text.WrapAnywhere
                    color: Theme.textSoft
                    font.family: Theme.mono
                    font.pixelSize: 12
                    maximumLineCount: root.selected ? 200 : 4
                    elide: Text.ElideRight
                }
            }
        }

        // VLM finding (inspection / safety)
        Rectangle {
            visible: model.kind === "vlm"
            width: parent.width
            height: visible ? Math.max(vlmText.implicitHeight, thumb.visible ? 72 : 0) + 20 : 0
            radius: 10
            color: model.agent === "Safety" ? "#1F1317" : "#1F1810"
            border.color: model.agent === "Safety" ? "#4A2430" : "#4A3A20"
            Image {
                id: thumb
                x: 10; y: 10
                width: visible ? 96 : 0
                height: 72
                visible: model.image !== ""
                source: model.image !== "" ? "image://ros/" + model.image : ""
                fillMode: Image.PreserveAspectCrop
                cache: false
            }
            Text {
                id: vlmText
                x: thumb.visible ? 116 : 10
                y: 10
                width: parent.width - x - 10
                text: model.text
                wrapMode: Text.Wrap
                color: model.agent === "Safety" ? "#F2D5DA" : "#F2E3CC"
                font.family: Theme.sans
                font.pixelSize: 13
                maximumLineCount: root.selected ? 100 : 6
                elide: Text.ElideRight
            }
        }
    }
}
