import { useEffect, useRef } from "react";
import { useTopic } from "../ros/RosProvider";
import type { OccupancyGrid, Path } from "../ros/types";

/** Renders a nav_msgs/OccupancyGrid (+ planned path) to a crisp canvas. */
export function MapCanvas() {
  const map = useTopic<OccupancyGrid>("map");
  const path = useTopic<Path>("plan");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const draw = () => {
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const cssW = wrap.clientWidth;
      const cssH = wrap.clientHeight;
      canvas.width = Math.max(1, Math.floor(cssW * dpr));
      canvas.height = Math.max(1, Math.floor(cssH * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, cssW, cssH);

      if (!map) return;
      const { width: w, height: h, resolution: res, origin } = map.info;

      // rasterise the grid into an offscreen image (flip Y: ROS origin is bottom-left)
      const off = document.createElement("canvas");
      off.width = w;
      off.height = h;
      const octx = off.getContext("2d");
      if (!octx) return;
      const img = octx.createImageData(w, h);
      for (let my = 0; my < h; my++) {
        for (let mx = 0; mx < w; mx++) {
          const v = map.data[my * w + mx];
          const py = h - 1 - my;
          const idx = (py * w + mx) * 4;
          let r = 12, g = 18, b = 28; // unknown
          if (v === 0) {
            r = 16, g = 26, b = 40; // free space
          } else if (v >= 50) {
            r = 56, g = 130, b = 170; // occupied (cyan-tinted walls)
          }
          img.data[idx] = r;
          img.data[idx + 1] = g;
          img.data[idx + 2] = b;
          img.data[idx + 3] = 255;
        }
      }
      octx.putImageData(img, 0, 0);

      // fit the grid into the canvas while preserving aspect ratio
      const scale = Math.min(cssW / w, cssH / h);
      const drawW = w * scale;
      const drawH = h * scale;
      const offX = (cssW - drawW) / 2;
      const offY = (cssH - drawH) / 2;
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(off, offX, offY, drawW, drawH);

      // world -> canvas px
      const toPx = (wx: number, wy: number): [number, number] => {
        const gx = (wx - origin.position.x) / res;
        const gy = (wy - origin.position.y) / res;
        return [offX + gx * scale, offY + (h - gy) * scale];
      };

      if (path && path.poses.length > 1) {
        ctx.beginPath();
        path.poses.forEach((p, i) => {
          const [px, py] = toPx(p.pose.position.x, p.pose.position.y);
          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.strokeStyle = "#22d3ee";
        ctx.lineWidth = 2.5;
        ctx.lineJoin = "round";
        ctx.shadowColor = "#22d3ee";
        ctx.shadowBlur = 8;
        ctx.stroke();
        ctx.shadowBlur = 0;

        // current position marker at the path head
        const head = path.poses[path.poses.length - 1].pose.position;
        const [hx, hy] = toPx(head.x, head.y);
        ctx.beginPath();
        ctx.arc(hx, hy, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#22d3ee";
        ctx.shadowColor = "#22d3ee";
        ctx.shadowBlur = 12;
        ctx.fill();
        ctx.shadowBlur = 0;
        ctx.strokeStyle = "#eafdff";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    };

    draw();
    const ro = new ResizeObserver(draw);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [map, path]);

  return (
    <div ref={wrapRef} className="relative h-full w-full overflow-hidden rounded-xl bg-[#0a1018] ring-1 ring-white/10">
      <canvas ref={canvasRef} className="block h-full w-full" />
      {!map && (
        <div className="absolute inset-0 flex items-center justify-center text-xs text-faint">
          waiting for /global_costmap…
        </div>
      )}
    </div>
  );
}
