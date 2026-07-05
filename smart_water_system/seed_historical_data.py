"""
Seed 300 historical readings with a realistic 24-hour daily demand pattern.

Pattern shape (flow):
  - Night  00:00–06:00  low baseline (~8 L/min)
  - Morning 06:00–09:00 ramp up to peak (~22 L/min)
  - Midday  09:00–17:00 moderate plateau (~15 L/min)
  - Evening 17:00–21:00 second peak (~20 L/min)
  - Night   21:00–24:00 taper back to baseline

Pressure, pH, turbidity and temperature follow correlated patterns
with Gaussian noise to look realistic.
"""

import requests
import numpy as np
import time
import sys

API_URL = "http://localhost:8000/api/sensor-data"
NUM_READINGS = 300          # well above the 100-sample minimum
INTERVAL_SECONDS = 5        # mirrors the real simulator interval

# ── helpers ──────────────────────────────────────────────────────────────────

def demand_factor(step: int, total: int) -> float:
    """Return a 0-1 demand factor that maps `step` onto a full daily cycle."""
    # Map step to hour-of-day (0–24)
    hour = (step / total) * 24.0
    # Piece-wise curve
    if hour < 6:          # deep night
        return 0.35 + 0.05 * np.sin(np.pi * hour / 6)
    elif hour < 9:        # morning ramp
        return 0.35 + 0.65 * ((hour - 6) / 3)
    elif hour < 12:       # late-morning plateau
        return 0.90 + 0.10 * np.sin(np.pi * (hour - 9) / 3)
    elif hour < 17:       # midday moderate
        return 0.70 + 0.10 * np.sin(np.pi * (hour - 12) / 5)
    elif hour < 20:       # evening peak
        return 0.75 + 0.25 * np.sin(np.pi * (hour - 17) / 3)
    elif hour < 22:       # evening taper
        return 0.75 - 0.40 * ((hour - 20) / 2)
    else:                 # late night
        return 0.35 + 0.05 * np.cos(np.pi * (hour - 22) / 2)


def generate_reading(step: int, total: int) -> dict:
    rng = np.random.default_rng(step)          # reproducible per step
    d = demand_factor(step, total)

    # Flow: 5–25 L/min range shaped by demand factor
    base_flow = 5.0 + d * 20.0
    flow = max(0.1, base_flow + rng.normal(0, 0.6))

    # Pressure: inversely correlated with flow (higher demand → slightly lower pressure)
    base_pressure = 2.8 - d * 0.6
    pressure = max(0.5, base_pressure + rng.normal(0, 0.08))

    # pH: slow drift around 7.5, tighter at high demand (more treatment)
    ph = np.clip(7.5 + rng.normal(0, 0.15 if d > 0.7 else 0.25), 6.5, 8.5)

    # Turbidity: slightly higher at peak demand (sediment disturbance)
    turbidity = max(0.1, 1.5 + d * 1.2 + rng.normal(0, 0.3))

    # Temperature: gentle daily cycle 22–27 °C
    hour = (step / total) * 24.0
    temp = 24.5 + 1.5 * np.sin(np.pi * (hour - 6) / 12) + rng.normal(0, 0.3)

    return {
        "flow":        round(float(flow), 3),
        "pressure":    round(float(pressure), 3),
        "ph":          round(float(ph), 3),
        "turbidity":   round(float(turbidity), 3),
        "temperature": round(float(temp), 3),
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"💧 Seeding {NUM_READINGS} historical readings with daily demand pattern…")
    print(f"   Target API: {API_URL}\n")

    ok = 0
    fail = 0
    for i in range(NUM_READINGS):
        payload = generate_reading(i, NUM_READINGS)
        try:
            r = requests.post(API_URL, json=payload, timeout=5)
            if r.status_code == 200:
                ok += 1
            else:
                fail += 1
                print(f"  ✗ step {i}: HTTP {r.status_code} — {r.text[:80]}")
        except requests.RequestException as e:
            fail += 1
            print(f"  ✗ step {i}: {e}")

        # Progress tick every 50 readings
        if (i + 1) % 50 == 0:
            print(f"  ✓ {i + 1}/{NUM_READINGS} sent  ({fail} errors so far)")

    print(f"\n{'='*45}")
    print(f"  Done — {ok} readings inserted, {fail} failed.")

    # Show updated total
    try:
        stats = requests.get("http://localhost:8000/api/stats", timeout=5).json()
        print(f"  Total records in DB: {stats.get('total_records', '?')}")
    except Exception:
        pass
    print(f"{'='*45}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
