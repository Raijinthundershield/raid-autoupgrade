import { describe, expect, it } from "vitest";
import { displayRectToImageRect } from "./coordMath";

// ---------------------------------------------------------------------------
// Behavior 1: half-scale — display center maps to image center
// ---------------------------------------------------------------------------

describe("displayRectToImageRect", () => {
  it("maps center rect at half scale to image center", () => {
    const result = displayRectToImageRect(
      { x: 100, y: 75, w: 20, h: 15 },
      { w: 200, h: 150 },
      { w: 400, h: 300 }
    );

    expect(result).toEqual({ x: 200, y: 150, w: 40, h: 30 });
  });

  // -------------------------------------------------------------------------
  // Behavior 2: 1:1 scale → identity
  // -------------------------------------------------------------------------

  it("returns the same rect at 1:1 scale", () => {
    const rect = { x: 50, y: 30, w: 100, h: 60 };
    const size = { w: 800, h: 600 };

    expect(displayRectToImageRect(rect, size, size)).toEqual(rect);
  });

  // -------------------------------------------------------------------------
  // Behavior 3: rect dimensions scale proportionally (non-square image)
  // -------------------------------------------------------------------------

  it("scales width and height independently for non-square ratios", () => {
    // display 400×200, image 800×600 → scaleX=2, scaleY=3
    const result = displayRectToImageRect(
      { x: 10, y: 10, w: 50, h: 20 },
      { w: 400, h: 200 },
      { w: 800, h: 600 }
    );

    expect(result).toEqual({ x: 20, y: 30, w: 100, h: 60 });
  });

  // -------------------------------------------------------------------------
  // Behavior 4: fractional coords round to nearest integer
  // -------------------------------------------------------------------------

  it("rounds fractional mapped coords to integers", () => {
    // display 300×300, image 1000×1000 → scale ≈ 3.333…
    // rect x=1 → 3.333… → rounds to 3
    const result = displayRectToImageRect(
      { x: 1, y: 1, w: 1, h: 1 },
      { w: 300, h: 300 },
      { w: 1000, h: 1000 }
    );

    expect(result.x).toBe(3);
    expect(result.y).toBe(3);
  });
});
