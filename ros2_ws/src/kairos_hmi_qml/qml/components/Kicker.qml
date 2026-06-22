import QtQuick 2.15
import "../Theme.js" as T

Text {
    property string label: ""
    text: label.toUpperCase()
    color: T.faint
    font.pixelSize: 11
    font.bold: true
    font.letterSpacing: 1.6
    font.family: "monospace"
    elide: Text.ElideRight
}
