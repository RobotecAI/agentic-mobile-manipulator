import QtQuick 2.15
import QtQuick.Shapes 1.15

// Stroke icon drawn from Theme.icons path data on a 24x24 grid.
Item {
    id: root
    property string name
    property color color: Theme.muted
    property real size: 20
    property real strokeWidth: 1.8
    width: size
    height: size

    Shape {
        width: 24
        height: 24
        scale: root.size / 24
        transformOrigin: Item.TopLeft
        layer.enabled: true
        layer.samples: 4
        ShapePath {
            strokeColor: root.color
            strokeWidth: root.strokeWidth
            fillColor: "transparent"
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            PathSvg { path: Theme.icons[root.name] || "" }
        }
    }
}
