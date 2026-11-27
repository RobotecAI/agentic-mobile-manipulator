import QtQuick 2.15
import QtQuick.Layouts 1.15

RowLayout {
    property string name
    property string detail
    property string metric
    property string tone: "ok"
    Layout.fillWidth: true
    Layout.leftMargin: 12
    Layout.rightMargin: 12
    height: 32
    spacing: 10
    Rectangle {
        width: 8; height: 8; radius: 4
        color: tone === "ok" ? Theme.ok : tone === "danger" ? Theme.dangerText : tone === "warn" ? Theme.warn : "#4A5363"
    }
    Label2 { text: name; font.pixelSize: 13; font.weight: Font.Medium; Layout.preferredWidth: 150 }
    Label2 { text: detail; color: Theme.muted; font.family: Theme.mono; font.pixelSize: 12; Layout.fillWidth: true }
    Label2 { text: metric; color: "#AEB7C4"; font.family: Theme.mono; font.pixelSize: 12 }
}
