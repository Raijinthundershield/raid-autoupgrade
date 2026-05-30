export type Rect = { x: number; y: number; w: number; h: number };
export type Size = { w: number; h: number };

export function displayRectToImageRect(
  rect: Rect,
  displaySize: Size,
  imageSize: Size
): Rect {
  const scaleX = imageSize.w / displaySize.w;
  const scaleY = imageSize.h / displaySize.h;
  return {
    x: Math.round(rect.x * scaleX),
    y: Math.round(rect.y * scaleY),
    w: Math.round(rect.w * scaleX),
    h: Math.round(rect.h * scaleY),
  };
}
