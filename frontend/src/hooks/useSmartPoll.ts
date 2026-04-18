import { useCallback, useEffect, useRef } from "react";

export interface SmartPollOptions {
  /**
   * Delay between successful polls in milliseconds.
   * @default 5000
   */
  interval?: number;
  /**
   * Maximum back-off delay in milliseconds after repeated errors.
   * @default 30000
   */
  maxBackoff?: number;
  /**
   * When this callback returns `true` polling stops permanently.
   * Checked before each scheduled tick.
   */
  isTerminal?: () => boolean;
  /**
   * Pause polling while the browser tab is hidden (Page Visibility API).
   * Resumes immediately when the tab becomes visible again.
   * @default true
   */
  pauseOnHidden?: boolean;
  /**
   * Master switch. Set to `false` to disable polling entirely.
   * @default true
   */
  enabled?: boolean;
}

/**
 * Resilient polling hook with three built-in safety mechanisms:
 *
 * 1. **Exponential back-off on errors** – each consecutive failure doubles
 *    the wait time up to `maxBackoff`. The counter resets on the next success.
 * 2. **Page Visibility API** – polling is suspended while the browser tab is
 *    hidden and resumes (immediately) when the tab regains focus.
 * 3. **Terminal-state guard** – once `isTerminal()` returns `true` no further
 *    ticks are scheduled, so completed / failed jobs don't keep polling.
 *
 * The first tick fires immediately on mount; all subsequent ticks use the
 * configured `interval` (or a back-off delay after an error).
 *
 * @example
 * useSmartPoll(loadData, {
 *   interval: 5000,
 *   isTerminal: () => ["completed", "failed"].includes(job?.status ?? ""),
 * });
 */
export function useSmartPoll(
  fn: () => Promise<void>,
  options: SmartPollOptions = {},
): void {
  const {
    interval = 5000,
    maxBackoff = 30000,
    isTerminal,
    pauseOnHidden = true,
    enabled = true,
  } = options;

  // Keep refs so callbacks always see the latest values without triggering
  // effect re-runs.
  const fnRef = useRef(fn);
  const isTerminalRef = useRef(isTerminal);
  fnRef.current = fn;
  isTerminalRef.current = isTerminal;

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const backoffRef = useRef(0);
  const activeRef = useRef(false);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const schedule = useCallback(
    (delay: number) => {
      clearTimer();
      timerRef.current = setTimeout(async () => {
        if (!activeRef.current) return;

        // Pause when the tab is hidden – re-check after a short while.
        if (pauseOnHidden && typeof document !== "undefined" && document.hidden) {
          schedule(1000);
          return;
        }

        // Stop permanently once a terminal state is reached.
        if (isTerminalRef.current?.()) return;

        try {
          await fnRef.current();
          backoffRef.current = 0; // reset on success
          if (activeRef.current && !isTerminalRef.current?.()) {
            schedule(interval);
          }
        } catch {
          // Double the back-off on each consecutive error, capped at maxBackoff.
          backoffRef.current =
            backoffRef.current === 0
              ? interval
              : Math.min(backoffRef.current * 2, maxBackoff);
          if (activeRef.current) {
            schedule(backoffRef.current);
          }
        }
      }, delay);
    },
    [clearTimer, interval, maxBackoff, pauseOnHidden],
  );

  useEffect(() => {
    if (!enabled) return;

    activeRef.current = true;
    backoffRef.current = 0;

    // Fire immediately on mount (delay = 0), then follow the normal schedule.
    schedule(0);

    const handleVisibilityChange = () => {
      if (
        typeof document !== "undefined" &&
        !document.hidden &&
        activeRef.current &&
        !isTerminalRef.current?.()
      ) {
        // Tab became visible again – fire immediately then resume schedule.
        clearTimer();
        void fnRef.current()
          .then(() => {
            backoffRef.current = 0; // reset back-off on success
            if (activeRef.current && !isTerminalRef.current?.()) {
              schedule(interval);
            }
          })
          .catch(() => {
            // Keep any existing back-off on failure; reschedule with it.
            const delay = backoffRef.current > 0 ? backoffRef.current : interval;
            if (activeRef.current) schedule(delay);
          });
      }
    };

    if (pauseOnHidden && typeof document !== "undefined") {
      document.addEventListener("visibilitychange", handleVisibilityChange);
    }

    return () => {
      activeRef.current = false;
      clearTimer();
      if (pauseOnHidden && typeof document !== "undefined") {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      }
    };
  }, [enabled, interval, pauseOnHidden, schedule, clearTimer]);
}
