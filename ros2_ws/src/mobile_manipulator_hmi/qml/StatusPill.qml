import QtQuick 2.15

// Small status label with a dot: ok / warn / danger / neutral.
Rectangle {
    id: root
    property string text
    property string tone: "ok"
    property bool pulse: false
    readonly property color fg: tone === "ok" ? Theme.ok : tone === "warn" ? Theme.warn
                              : tone === "danger" ? Theme.dangerText : Theme.muted
    implicitWidth: row.implicitWidth + 20
    implicitHeight: 30
    radius: tone === "neutral" ? 8 : height / 2
    color: tone === "ok" ? Theme.okBg : tone === "warn" ? Theme.warnBg : tone === "danger" ? "#2C1416" : Theme.panel2

    Row {
        id: row
        anchors.centerIn: parent
        spacing: 8
        Rectangle {
            id: dot
            width: 8; height: 8; radius: 4
            color: root.fg
            anchors.verticalCenter: parent.verticalCenter
            SequentialAnimation on opacity {
                running: root.pulse
                loops: Animation.Infinite
                NumberAnimation { to: 0.35; duration: 700 }
                NumberAnimation { to: 1; duration: 700 }
            }
        }
        Text {
            text: root.text
            color: root.tone === "neutral" ? Theme.textSoft : root.fg
            font.family: Theme.sans
            font.pixelSize: 12
            font.weight: Font.DemiBold
            anchors.verticalCenter: parent.verticalCenter
        }
    }
}
