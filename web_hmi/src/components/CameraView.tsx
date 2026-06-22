import { useEffect, useRef, useState } from "react";
import { VideoOff } from "lucide-react";
import { CONFIG } from "../ros/config";
import { useRos } from "../ros/RosProvider";

type Mode = "mjpeg" | "snapshot" | "error";

/**
 * Live camera tile fed by web_video_server.
 *
 * Primary path is the MJPEG stream (`?type=mjpeg`) for smooth video. If no
 * frame paints within a short window (some browsers / headless renderers don't
 * display multipart/x-mixed-replace in <img>), it falls back to polling the
 * single-frame `/snapshot` endpoint, so a feed always shows when one exists.
 */
export function CameraView({ topic }: { topic: string }) {
  const { state } = useRos();
  const connected = state === "connected";
  const [mode, setMode] = useState<Mode>("mjpeg");
  const [tick, setTick] = useState(0);
  const loaded = useRef(false);

  // NOTE: web_video_server does not URL-decode the topic param, so the slashes
  // must stay raw (encodeURIComponent would turn "/" into "%2F" and 404).
  const base = CONFIG.videoServerUrl;

  // reset when the connection or topic changes
  useEffect(() => {
    loaded.current = false;
    setMode(connected ? "mjpeg" : "error");
  }, [connected, topic]);

  // if the MJPEG stream hasn't painted a frame shortly, fall back to snapshots
  useEffect(() => {
    if (!connected || mode !== "mjpeg") return;
    const id = window.setTimeout(() => {
      if (!loaded.current) setMode("snapshot");
    }, 2200);
    return () => window.clearTimeout(id);
  }, [connected, mode, topic]);

  // snapshot polling loop (~6 fps)
  useEffect(() => {
    if (mode !== "snapshot") return;
    const id = window.setInterval(() => setTick((t) => t + 1), 160);
    return () => window.clearInterval(id);
  }, [mode]);

  const showImg = connected && mode !== "error";
  const src =
    mode === "snapshot"
      ? `${base}/snapshot?topic=${topic}&quality=80&t=${tick}`
      : `${base}/stream?topic=${topic}&type=mjpeg`;

  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl bg-[#0a1018] ring-1 ring-white/10">
      {showImg ? (
        <img
          src={src}
          alt={topic}
          className="h-full w-full object-cover"
          onLoad={() => {
            loaded.current = true;
          }}
          onError={() => setMode((m) => (m === "mjpeg" ? "snapshot" : "error"))}
        />
      ) : (
        <div className="absolute inset-0 grid place-items-center">
          <div
            className="absolute inset-0 opacity-[0.07]"
            style={{ backgroundImage: "repeating-linear-gradient(0deg, #fff 0 1px, transparent 1px 4px)" }}
          />
          <div className="relative flex flex-col items-center gap-2 text-faint">
            <VideoOff size={20} />
            <span className="font-mono text-[10px] uppercase tracking-widest">
              {connected ? "no signal" : "offline"}
            </span>
          </div>
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 rounded-xl shadow-[inset_0_0_60px_rgba(0,0,0,0.5)]" />
    </div>
  );
}
