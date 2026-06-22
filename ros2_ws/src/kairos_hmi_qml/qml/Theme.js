.pragma library

// Kairos Command palette — mirrors web_hmi/src/index.css
var bg      = "#06080d";
var fg      = "#e9eef7";
var dim     = "#9aa6ba";
var faint   = "#5c6779";

var cyan    = "#22d3ee";
var blue    = "#38bdf8";
var indigo  = "#6366f1";
var violet  = "#a78bfa";
var amber   = "#f9a23b";
var emerald = "#34d399";
var red     = "#fb5a5a";
var yellow  = "#fbbf24";

// translucent surfaces (#AARRGGBB)
var line    = "#1cffffff";
var line2   = "#12ffffff";
var panel   = "#0bffffff";
var panelHi = "#16ffffff";
var inset   = "#0a0f1a";

// gradient stop pairs for accents
function grad(accent) {
    if (accent === "violet")  return ["#a78bfa", "#6366f1"];
    if (accent === "amber")   return ["#fbbf24", "#f97316"];
    if (accent === "emerald") return ["#34d399", "#10b981"];
    if (accent === "rose")    return ["#fb7185", "#ef4444"];
    return ["#22d3ee", "#3b82f6"]; // cyan
}

function levelColor(lvl) {
    if (lvl >= 40) return red;
    if (lvl >= 30) return amber;
    return dim;
}
function levelLabel(lvl) {
    if (lvl >= 50) return "FATAL";
    if (lvl >= 40) return "ERROR";
    if (lvl >= 30) return "WARN";
    if (lvl >= 20) return "INFO";
    return "DEBUG";
}
