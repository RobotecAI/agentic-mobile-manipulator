// Colors, type and icon paths shared by every screen.
pragma Singleton
import QtQuick 2.15

QtObject {
    readonly property color bg: "#0B0E13"
    readonly property color chrome: "#0F131A"
    readonly property color panel: "#12161D"
    readonly property color panel2: "#161B23"
    readonly property color well: "#0E1219"
    readonly property color border: "#232A35"
    readonly property color borderStrong: "#2C3442"
    readonly property color text: "#E6EAF0"
    readonly property color textSoft: "#C9D1DC"
    readonly property color muted: "#9AA4B2"
    readonly property color faint: "#8C96A5"
    readonly property color accent: "#5B9DFF"
    readonly property color accentSoft: "#8AB8FF"
    readonly property color accentBg: "#1A2333"
    readonly property color ok: "#3DD68C"
    readonly property color okBg: "#10261C"
    readonly property color warn: "#FFB547"
    readonly property color warnBg: "#2A2111"
    readonly property color danger: "#E5484D"
    readonly property color dangerText: "#FF8A8E"
    readonly property color dangerBg: "#1E1214"

    readonly property string sans: "Inter"
    readonly property string mono: "JetBrains Mono"
    readonly property int radius: 16

    // 24x24 stroke icons (SVG path data).
    readonly property var icons: ({
        robot: "M3 11h18v8H3z M12 11V6l4-2 M16 4l2 2",
        mission: "M12 3a9 9 0 1 0 0.01 0 M12 8a4 4 0 1 0 0.01 0 M12 3v3 M12 18v3 M3 12h3 M18 12h3",
        agents: "M12 2.5a2.5 2.5 0 1 0 0.01 0 M5 15.5a2.5 2.5 0 1 0 0.01 0 M19 15.5a2.5 2.5 0 1 0 0.01 0 M12 7.5v4 M12 11.5L6.5 16 M12 11.5l5.5 4.5",
        sim: "M12 3l8 4.5v9L12 21l-8-4.5v-9z M12 12l8-4.5 M12 12v9 M12 12L4 7.5",
        system: "M3 12h4l3-7 4 14 3-7h4",
        stop: "M8 3h8l5 5v8l-5 5H8l-5-5V8z M9 12h6",
        pause: "M8 5v14 M16 5v14",
        play: "M7 4l13 8-13 8z",
        tool: "M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z",
        prompt: "M4 17l6-5-6-5 M12 19h8",
        up: "M12 19V5 M6 11l6-6 6 6",
        down: "M12 5v14 M6 13l6 6 6-6",
        left: "M9 14L4 9l5-5 M4 9h10a6 6 0 0 1 0 12h-3",
        right: "M15 14l5-5-5-5 M20 9H10a6 6 0 0 0 0 12h3",
        close: "M6 6l12 12 M18 6L6 18",
        eye: "M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z M12 9a3 3 0 1 0 0.01 0",
        building: "M3 21h18 M5 21V8l7-5 7 5v13 M9 21v-6h6v6"
    })
}
