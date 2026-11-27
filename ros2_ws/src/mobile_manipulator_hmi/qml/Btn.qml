import QtQuick 2.15
import QtQuick.Controls 2.15

// Button in the console style. kind: "default" | "primary" | "danger" | "ghost" | "estop".
Button {
    id: control
    property string kind: "default"
    property string iconName: ""
    property bool selected: false
    property color fg: kind === "primary" ? Theme.bg : kind === "estop" ? "white"
                     : kind === "danger" ? Theme.dangerText : selected ? Theme.accentSoft : Theme.text
    implicitHeight: kind === "estop" ? 44 : 38
    leftPadding: 14
    rightPadding: 14
    hoverEnabled: true
    font.family: Theme.sans
    font.pixelSize: 13
    font.weight: kind === "estop" ? Font.Bold : Font.DemiBold
    font.letterSpacing: kind === "estop" ? 0.6 : 0
    opacity: enabled ? 1 : 0.45

    contentItem: Row {
        spacing: 8
        Icon {
            visible: control.iconName !== ""
            name: control.iconName
            color: control.fg
            size: 16
            strokeWidth: 2.1
            anchors.verticalCenter: parent.verticalCenter
        }
        Text {
            text: control.text
            font: control.font
            color: control.fg
            anchors.verticalCenter: parent.verticalCenter
        }
    }
    background: Rectangle {
        radius: 10
        color: {
            const base = control.kind === "primary" ? Theme.accent : control.kind === "estop" ? Theme.danger
                       : control.kind === "danger" ? Theme.dangerBg : control.kind === "ghost" ? "transparent"
                       : control.selected ? Theme.accentBg : Theme.panel2
            return control.down ? Qt.darker(base, 1.25) : control.hovered ? Qt.lighter(base, 1.12) : base
        }
        border.color: control.kind === "primary" || control.kind === "estop" ? "transparent"
                    : control.kind === "danger" ? "#4A2326" : control.selected ? "#3B5F99" : Theme.borderStrong
        border.width: control.activeFocus ? 2 : 1
    }
}
