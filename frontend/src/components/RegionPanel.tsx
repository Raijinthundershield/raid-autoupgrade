import { useEffect, useRef, useState } from "react";
import { displayRectToImageRect, type Rect } from "../utils/coordMath";
import { Button } from "@/components/ui/button";

type RegionKey = "upgrade_bar" | "upgrade_button";

interface CachedRegions {
  upgrade_bar: [number, number, number, number];
  upgrade_button: [number, number, number, number];
}

interface RegionsResponse {
  regions: CachedRegions | null;
  window_size_mismatch: boolean;
}

const REGION_COLORS: Record<RegionKey, string> = {
  upgrade_bar: "#22c55e",
  upgrade_button: "#3b82f6",
};

const REGION_LABELS: Record<RegionKey, string> = {
  upgrade_bar: "Upgrade Bar",
  upgrade_button: "Upgrade Button",
};

function normalizeRect(a: { x: number; y: number }, b: { x: number; y: number }): Rect {
  return {
    x: Math.round(Math.min(a.x, b.x)),
    y: Math.round(Math.min(a.y, b.y)),
    w: Math.round(Math.abs(b.x - a.x)),
    h: Math.round(Math.abs(b.y - a.y)),
  };
}

export function RegionPanel() {
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [screenshotError, setScreenshotError] = useState(false);
  const [imageSize, setImageSize] = useState<{ w: number; h: number } | null>(null);
  const [cachedRegions, setCachedRegions] = useState<CachedRegions | null>(null);
  const [windowSizeMismatch, setWindowSizeMismatch] = useState(false);
  const [drawn, setDrawn] = useState<Partial<Record<RegionKey, Rect>>>({});
  const [activeKey, setActiveKey] = useState<RegionKey | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null);
  const [dragCurrent, setDragCurrent] = useState<{ x: number; y: number } | null>(null);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [capturing, setCapturing] = useState(false);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  useEffect(() => {
    fetch("/api/regions")
      .then(async (r) => {
        if (!r.ok) return;
        const data: RegionsResponse = await r.json();
        setWindowSizeMismatch(data.window_size_mismatch);
        if (data.regions) setCachedRegions(data.regions);
      })
      .catch(() => {});
  }, []);

  async function captureScreenshot() {
    setCapturing(true);
    setScreenshotError(false);
    try {
      const r = await fetch("/api/screenshot");
      if (!r.ok) { setScreenshotError(true); return; }
      const blob = await r.blob();
      setScreenshotUrl(URL.createObjectURL(blob));
    } catch {
      setScreenshotError(true);
    } finally {
      setCapturing(false);
    }
  }

  useEffect(() => {
    const canvas = canvasRef.current;
    const img = imgRef.current;
    if (!canvas || !img || !img.complete || !imageSize) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const displaySize = { w: canvas.width, h: canvas.height };

    function drawRect(rect: Rect, key: RegionKey, dashed = false) {
      ctx!.strokeStyle = REGION_COLORS[key];
      ctx!.lineWidth = 2;
      if (dashed) ctx!.setLineDash([6, 3]);
      ctx!.strokeRect(rect.x, rect.y, rect.w, rect.h);
      ctx!.setLineDash([]);
      ctx!.fillStyle = REGION_COLORS[key];
      ctx!.font = "bold 11px 'IBM Plex Mono', monospace";
      ctx!.fillText(REGION_LABELS[key], rect.x + 4, rect.y + 14);
    }

    if (cachedRegions) {
      for (const key of ["upgrade_bar", "upgrade_button"] as RegionKey[]) {
        if (key in drawn) continue;
        const r = cachedRegions[key];
        if (!r) continue;
        const [ix, iy, iw, ih] = r;
        drawRect(
          {
            x: Math.round((ix / imageSize.w) * displaySize.w),
            y: Math.round((iy / imageSize.h) * displaySize.h),
            w: Math.round((iw / imageSize.w) * displaySize.w),
            h: Math.round((ih / imageSize.h) * displaySize.h),
          },
          key,
          windowSizeMismatch
        );
      }
    }

    for (const [k, rect] of Object.entries(drawn) as [RegionKey, Rect][]) {
      drawRect(rect, k);
    }

    if (dragStart && dragCurrent && activeKey) {
      drawRect(normalizeRect(dragStart, dragCurrent), activeKey, true);
    }
  }, [screenshotUrl, imageSize, cachedRegions, windowSizeMismatch, drawn, dragStart, dragCurrent, activeKey]);

  function handleImageLoad() {
    const img = imgRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;
    const containerW = canvas.parentElement?.clientWidth ?? 800;
    const ratio = img.naturalHeight / img.naturalWidth;
    canvas.width = containerW;
    canvas.height = Math.round(containerW * ratio);
    setImageSize({ w: img.naturalWidth, h: img.naturalHeight });
  }

  function canvasPoint(e: React.MouseEvent<HTMLCanvasElement>) {
    const canvas = canvasRef.current!;
    const r = canvas.getBoundingClientRect();
    const sx = canvas.width / r.width;
    const sy = canvas.height / r.height;
    return { x: (e.clientX - r.left) * sx, y: (e.clientY - r.top) * sy };
  }

  function handleMouseDown(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!activeKey) return;
    const p = canvasPoint(e);
    setDragStart(p);
    setDragCurrent(p);
  }

  function handleMouseMove(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!dragStart || !activeKey) return;
    setDragCurrent(canvasPoint(e));
  }

  function handleMouseUp(e: React.MouseEvent<HTMLCanvasElement>) {
    if (!dragStart || !activeKey) return;
    const rect = normalizeRect(dragStart, canvasPoint(e));
    if (rect.w > 4 && rect.h > 4) {
      setDrawn((prev) => ({ ...prev, [activeKey]: rect }));
    }
    setDragStart(null);
    setDragCurrent(null);
    setActiveKey(null);
  }

  async function handleSave() {
    const canvas = canvasRef.current;
    if (!imageSize || !canvas) return;
    const displaySize = { w: canvas.width, h: canvas.height };

    function resolveRegion(key: RegionKey): [number, number, number, number] | null {
      const d = drawn[key];
      if (d) {
        const ir = displayRectToImageRect(d, displaySize, imageSize!);
        return [ir.x, ir.y, ir.w, ir.h];
      }
      const c = cachedRegions?.[key];
      return c ?? null;
    }

    const bar = resolveRegion("upgrade_bar");
    const btn = resolveRegion("upgrade_button");
    if (!bar || !btn) return;

    setSaveState("saving");
    try {
      const res = await fetch("/api/regions", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ upgrade_bar: bar, upgrade_button: btn }),
      });
      if (!res.ok) throw new Error("save failed");
      setSaveState("saved");
      setCachedRegions({ upgrade_bar: bar, upgrade_button: btn });
      setWindowSizeMismatch(false);
      setDrawn({});
    } catch {
      setSaveState("error");
    }
  }

  const hasValidCached = cachedRegions !== null && !windowSizeMismatch;
  const hasBothDrawn = drawn.upgrade_bar !== undefined && drawn.upgrade_button !== undefined;
  const canSaveFinal = hasBothDrawn || (hasValidCached && Object.keys(drawn).length > 0);

  return (
    <section className="space-y-3">
      {windowSizeMismatch && (
        <div className="conflict-badge" style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: "0.82rem" }}>
          Window size changed — cached regions invalid. Redraw both regions before saving.
        </div>
      )}

      {screenshotUrl && (
        <img
          ref={imgRef}
          src={screenshotUrl}
          style={{ display: "none" }}
          onLoad={handleImageLoad}
          alt=""
        />
      )}

      <div className="canvas-area">
        <canvas
          ref={canvasRef}
          style={{ width: "100%", display: "block" }}
          className={activeKey ? "cursor-crosshair" : "cursor-default"}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
        />
        {!screenshotUrl && !screenshotError && !capturing && (
          <div className="canvas-placeholder">
            Navigate to the upgrade screen in Raid, then click Capture Screenshot.
          </div>
        )}
        {capturing && (
          <div className="canvas-placeholder">Capturing…</div>
        )}
        {screenshotError && (
          <div
            className="canvas-placeholder"
            style={{ color: "oklch(0.78 0.18 27)" }}
          >
            Raid window not detected.
          </div>
        )}
      </div>

      <div className="flex gap-2 flex-wrap items-center">
        <Button
          variant="outline"
          size="sm"
          onClick={captureScreenshot}
          disabled={capturing}
        >
          {capturing ? "Capturing…" : screenshotUrl ? "Recapture" : "Capture Screenshot"}
        </Button>

        {(["upgrade_bar", "upgrade_button"] as RegionKey[]).map((key) => (
          <Button
            key={key}
            variant="outline"
            size="sm"
            onClick={() => setActiveKey((prev) => (prev === key ? null : key))}
            disabled={!screenshotUrl}
            style={{
              borderColor: activeKey === key ? undefined : `${REGION_COLORS[key]}60`,
              background: activeKey === key ? REGION_COLORS[key] : undefined,
              color: activeKey === key ? "#fff" : undefined,
            }}
          >
            {drawn[key] !== undefined ? `Redraw ${REGION_LABELS[key]}` : `Draw ${REGION_LABELS[key]}`}
          </Button>
        ))}

        <Button
          size="sm"
          onClick={handleSave}
          disabled={!canSaveFinal || saveState === "saving"}
        >
          {saveState === "saving" ? "Saving…"
            : saveState === "saved" ? "Saved ✓"
            : saveState === "error" ? "Error — retry"
            : "Save Regions"}
        </Button>
      </div>
    </section>
  );
}
