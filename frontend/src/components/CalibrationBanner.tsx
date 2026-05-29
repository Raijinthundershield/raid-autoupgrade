import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

interface RegionsResponse {
  regions: { upgrade_bar: [number, number, number, number]; upgrade_button: [number, number, number, number] } | null;
  window_size_mismatch: boolean;
}

interface Props {
  onNavigateToCalibration: () => void;
}

export function CalibrationBanner({ onNavigateToCalibration }: Props) {
  const [show, setShow] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    fetch("/api/regions")
      .then((r) => r.json())
      .then((data: RegionsResponse) => {
        if (!data.regions || data.window_size_mismatch) setShow(true);
      })
      .catch(() => {});
  }, []);

  if (!show || dismissed) return null;

  return (
    <div role="alert" className="flex items-center gap-3 rounded border border-[var(--t-border)] bg-[var(--t-surface)] px-4 py-3 text-sm text-[var(--t-text)]">
      <span className="flex-1">
        Regions are not calibrated for the current window size. Run Calibration before counting.
      </span>
      <Button size="sm" onClick={onNavigateToCalibration}>
        Go to Calibration
      </Button>
      <Button size="sm" variant="ghost" onClick={() => setDismissed(true)} aria-label="Dismiss">
        Dismiss
      </Button>
    </div>
  );
}
