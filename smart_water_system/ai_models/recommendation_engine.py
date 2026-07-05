"""
Decision Intelligence - Recommendation Engine
==============================================
Reads outputs from the existing LeakDetector and DemandForecaster,
applies rule-based logic, and returns structured recommendations with
estimated impact figures.

Design notes
------------
* Zero edits to existing files.  Import-only approach.
* All thresholds are overridable via the WaterRecommendationEngine
  constructor so the calling code (FastAPI route or Streamlit page) can
  tune them without touching this file.
* Degrades gracefully: if the LSTM forecast is unavailable, recommendations
  are still generated from the anomaly data alone (and vice-versa).
* Conductivity is not yet stored in the DB schema, so we accept it as an
  optional keyword argument rather than a hard dependency.

Quick usage
-----------
    from ai_models.recommendation_engine import WaterRecommendationEngine

    engine = WaterRecommendationEngine()

    # Option A – pass raw sensor values directly
    recs = engine.recommend_from_reading(
        zone="Zone-3",
        flow=6.1, pressure=1.2, ph=7.4,
        turbidity=3.1, temperature=26.0
    )

    # Option B – pass pre-computed outputs from the existing models
    anomaly_result = {"is_anomaly": True, "score": -0.42,
                      "flow": 6.1, "pressure": 1.2}
    forecast       = forecaster.predict_next_hours(hours=24)   # list[float]
    recs = engine.recommend_from_model_outputs(
        zone="Zone-3", anomaly_result=anomaly_result, forecast=forecast
    )

    # Recommendations are plain dicts – safe to return from FastAPI or
    # render in Streamlit.
    for r in recs:
        print(r["message"], "→", r["estimated_impact"])
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Thresholds (all configurable via constructor)
# ---------------------------------------------------------------------------
_DEFAULTS = dict(
    # Flow
    flow_low_threshold=8.0,        # L/min  – below this → possible leak / low supply
    flow_high_threshold=22.0,      # L/min  – above this → unusual high demand
    flow_baseline=15.0,            # L/min  – "normal" reference for impact maths

    # Pressure
    pressure_low_threshold=1.5,    # bar
    pressure_high_threshold=3.5,   # bar

    # Water quality
    ph_low_threshold=6.5,
    ph_high_threshold=8.5,
    turbidity_high_threshold=5.0,  # NTU
    temperature_high_threshold=35.0,  # °C

    # Demand forecast
    demand_surge_pct=0.12,         # 12% above rolling average → surge alert
    demand_deficit_pct=0.15,       # 15% below → possible supply shortfall

    # Impact constants
    litres_per_litre_per_min=60,   # 1 L/min × 60 min = 60 L/h
    irrigation_hours_per_day=8,    # assumed default irrigation schedule
)


class WaterRecommendationEngine:
    """
    Reads anomaly and forecast outputs; returns structured recommendations.

    Parameters
    ----------
    db_path : str
        Path to the existing SQLite database (read-only queries only).
    **threshold_overrides
        Any key from _DEFAULTS can be overridden here at construction time.
    """

    def __init__(
        self,
        db_path: str = "database/water.db",
        **threshold_overrides,
    ) -> None:
        self.db_path = db_path
        self.cfg = {**_DEFAULTS, **threshold_overrides}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend_from_reading(
        self,
        zone: str,
        flow: float,
        pressure: float,
        ph: float,
        turbidity: float,
        temperature: float,
        conductivity: Optional[float] = None,
        is_anomaly: Optional[bool] = None,
        anomaly_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations directly from sensor values.

        Returns a list of recommendation dicts (may be empty if all is normal).
        """
        sensor = dict(
            flow=flow,
            pressure=pressure,
            ph=ph,
            turbidity=turbidity,
            temperature=temperature,
            conductivity=conductivity,
        )
        recs: List[Dict[str, Any]] = []

        # --- Pressure / flow anomaly rules ---
        recs += self._check_flow_pressure(zone, sensor, is_anomaly, anomaly_score)

        # --- Water quality rules ---
        recs += self._check_quality(zone, sensor)

        # --- Temperature rules ---
        recs += self._check_temperature(zone, sensor)

        # --- Forecast-based rules (pull from DB if no forecast passed in) ---
        recs += self._check_demand_trend(zone)

        return self._finalise(recs)

    def recommend_from_model_outputs(
        self,
        zone: str,
        anomaly_result: Optional[Dict[str, Any]] = None,
        forecast: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations from pre-computed model outputs.

        Parameters
        ----------
        zone : str
        anomaly_result : dict
            Output from LeakDetector.predict() or detect_anomalies_batch().
            Expected keys (all optional, degrade gracefully):
              "is_anomaly" (bool), "score" (float),
              "flow" (float), "pressure" (float)
        forecast : list[float]
            Output from DemandForecaster.predict_next_hours().
            One float per 5-second interval (288 values = 24 hours).
        """
        recs: List[Dict[str, Any]] = []

        # --- Anomaly-based recommendations ---
        if anomaly_result:
            is_anomaly = anomaly_result.get("is_anomaly", False)
            score = anomaly_result.get("score", 0.0)
            flow = anomaly_result.get("flow")
            pressure = anomaly_result.get("pressure")
            ph = anomaly_result.get("ph")
            turbidity = anomaly_result.get("turbidity")
            temperature = anomaly_result.get("temperature")
            conductivity = anomaly_result.get("conductivity")

            sensor = dict(
                flow=flow, pressure=pressure,
                ph=ph, turbidity=turbidity,
                temperature=temperature, conductivity=conductivity,
            )
            recs += self._check_flow_pressure(zone, sensor, is_anomaly, score)
            recs += self._check_quality(zone, sensor)
            recs += self._check_temperature(zone, sensor)

        # --- Forecast-based recommendations ---
        if forecast:
            recs += self._check_forecast(zone, forecast)
        else:
            recs += self._check_demand_trend(zone)

        return self._finalise(recs)

    def get_summary(
        self,
        zones: Optional[List[str]] = None,
        limit_per_zone: int = 3,
    ) -> Dict[str, Any]:
        """
        Convenience method: pull recent data from the DB and return a
        summary dict with top recommendations per zone.

        Useful for a FastAPI /recommendations endpoint or a Streamlit
        summary card.
        """
        rows = self._load_recent(limit=200)
        if not rows:
            return {"zones": {}, "generated_at": datetime.now().isoformat(),
                    "status": "no_data"}

        zone_map: Dict[str, List[Dict]] = {}
        for row in rows:
            z = row.get("zone", "default")
            if zones and z not in zones:
                continue
            recs = self.recommend_from_reading(zone=z, **{
                k: row[k] for k in ("flow", "pressure", "ph", "turbidity", "temperature")
            })
            zone_map.setdefault(z, []).extend(recs)

        # Keep only the highest-priority items per zone
        result = {}
        for z, rec_list in zone_map.items():
            sorted_recs = sorted(
                rec_list, key=lambda r: _PRIORITY_ORDER.get(r["priority"], 99)
            )
            result[z] = sorted_recs[:limit_per_zone]

        return {
            "zones": result,
            "generated_at": datetime.now().isoformat(),
            "status": "ok",
        }

    # ------------------------------------------------------------------
    # Internal rule methods
    # ------------------------------------------------------------------

    def _check_flow_pressure(
        self,
        zone: str,
        sensor: Dict,
        is_anomaly: Optional[bool],
        score: Optional[float],
    ) -> List[Dict]:
        recs = []
        flow = sensor.get("flow")
        pressure = sensor.get("pressure")

        if flow is not None and flow < self.cfg["flow_low_threshold"]:
            flow_drop_pct = max(
                0, (self.cfg["flow_baseline"] - flow) / self.cfg["flow_baseline"]
            )
            # Estimate litres lost per day assuming continuous flow
            litres_lost = flow_drop_pct * self.cfg["flow_baseline"] * self.cfg["litres_per_litre_per_min"] * 24
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="leak_risk",
                    priority="HIGH",
                    message=(
                        f"{zone}: Flow dropped to {flow:.1f} L/min "
                        f"({flow_drop_pct * 100:.0f}% below baseline). "
                        "Likely pipe leak or valve malfunction."
                    ),
                    action="Inspect pipeline and valve actuators in this zone immediately.",
                    estimated_impact=f"Estimated unaccounted water loss: ~{litres_lost:,.0f} L/day",
                    sensor_snapshot=sensor,
                )
            )

        if pressure is not None and pressure < self.cfg["pressure_low_threshold"]:
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="pressure_low",
                    priority="HIGH",
                    message=(
                        f"{zone}: Pressure at {pressure:.2f} bar — below safe minimum "
                        f"({self.cfg['pressure_low_threshold']} bar)."
                    ),
                    action="Check pump status and downstream valve positions.",
                    estimated_impact="Low pressure may cause backflow contamination risk.",
                    sensor_snapshot=sensor,
                )
            )

        if pressure is not None and pressure > self.cfg["pressure_high_threshold"]:
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="pressure_high",
                    priority="MEDIUM",
                    message=(
                        f"{zone}: Pressure at {pressure:.2f} bar — above safe ceiling "
                        f"({self.cfg['pressure_high_threshold']} bar)."
                    ),
                    action="Reduce pump output or open pressure relief valve.",
                    estimated_impact="Sustained over-pressure accelerates pipe wear and burst risk.",
                    sensor_snapshot=sensor,
                )
            )

        # Anomaly score boost: if Isolation Forest flagged this AND flow is borderline
        if is_anomaly and flow is not None and flow >= self.cfg["flow_low_threshold"]:
            severity = "borderline anomaly" if (score or 0) > -0.3 else "strong anomaly"
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="anomaly_flagged",
                    priority="MEDIUM",
                    message=(
                        f"{zone}: Isolation Forest detected a {severity} "
                        f"(score={score:.3f}). Flow={flow:.1f} L/min, "
                        f"Pressure={pressure:.2f} bar."
                    ),
                    action="Monitor for next 5 readings; escalate if anomaly persists.",
                    estimated_impact="Early detection prevents escalation to full leak event.",
                    sensor_snapshot=sensor,
                )
            )

        return recs

    def _check_quality(self, zone: str, sensor: Dict) -> List[Dict]:
        recs = []
        ph = sensor.get("ph")
        turbidity = sensor.get("turbidity")

        if ph is not None:
            if ph < self.cfg["ph_low_threshold"]:
                recs.append(
                    self._make_rec(
                        zone=zone,
                        category="water_quality_ph_low",
                        priority="HIGH",
                        message=f"{zone}: pH={ph:.2f} — acidic water detected (below {self.cfg['ph_low_threshold']}).",
                        action="Activate dosing pump to raise pH. Notify water quality team.",
                        estimated_impact="Acidic water corrodes pipelines and is unsafe for consumption.",
                        sensor_snapshot=sensor,
                    )
                )
            elif ph > self.cfg["ph_high_threshold"]:
                recs.append(
                    self._make_rec(
                        zone=zone,
                        category="water_quality_ph_high",
                        priority="HIGH",
                        message=f"{zone}: pH={ph:.2f} — alkaline spike detected (above {self.cfg['ph_high_threshold']}).",
                        action="Check chemical dosing system for over-treatment.",
                        estimated_impact="High pH causes scaling in pipes and appliances.",
                        sensor_snapshot=sensor,
                    )
                )

        if turbidity is not None and turbidity > self.cfg["turbidity_high_threshold"]:
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="water_quality_turbidity",
                    priority="HIGH",
                    message=(
                        f"{zone}: Turbidity={turbidity:.1f} NTU — exceeds WHO guideline "
                        f"({self.cfg['turbidity_high_threshold']} NTU)."
                    ),
                    action="Increase filtration rate. Issue do-not-drink advisory for this zone.",
                    estimated_impact="High turbidity signals contamination or sediment intrusion.",
                    sensor_snapshot=sensor,
                )
            )

        return recs

    def _check_temperature(self, zone: str, sensor: Dict) -> List[Dict]:
        recs = []
        temp = sensor.get("temperature")
        if temp is not None and temp > self.cfg["temperature_high_threshold"]:
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="temperature_high",
                    priority="MEDIUM",
                    message=f"{zone}: Water temperature={temp:.1f}°C — above safe threshold.",
                    action="Check for solar heat gain on exposed pipes; consider insulation.",
                    estimated_impact="High temperature promotes bacterial growth (Legionella risk).",
                    sensor_snapshot=sensor,
                )
            )
        return recs

    def _check_forecast(self, zone: str, forecast: List[float]) -> List[Dict]:
        """
        Analyse LSTM forecast output (list of flow predictions).
        forecast[i] = predicted flow in L/min at time step i (5-second intervals).
        """
        recs = []
        if not forecast:
            return recs

        arr = np.array(forecast, dtype=float)

        # Rolling 1-hour windows (720 steps of 5 s = 1 hour)
        window = min(720, len(arr))
        current_avg = float(arr[:window].mean())
        baseline = self.cfg["flow_baseline"]

        surge_thresh = baseline * (1 + self.cfg["demand_surge_pct"])
        deficit_thresh = baseline * (1 - self.cfg["demand_deficit_pct"])

        # Look ahead up to 24 h
        hourly_means = [
            float(arr[i * 720: (i + 1) * 720].mean())
            for i in range(len(arr) // 720)
            if len(arr[i * 720: (i + 1) * 720]) > 0
        ]

        peak_hour = int(np.argmax(hourly_means)) if hourly_means else 0
        peak_flow = hourly_means[peak_hour] if hourly_means else current_avg

        if peak_flow > surge_thresh:
            excess_pct = (peak_flow - baseline) / baseline * 100
            irrigation_reduction_pct = min(40, excess_pct * 2)
            savings_l = (
                irrigation_reduction_pct / 100
                * baseline
                * self.cfg["litres_per_litre_per_min"]
                * self.cfg["irrigation_hours_per_day"]
            )
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="demand_surge",
                    priority="HIGH",
                    message=(
                        f"{zone}: LSTM forecast shows demand will peak ~{excess_pct:.0f}% above "
                        f"baseline around hour {peak_hour + 1} tomorrow."
                    ),
                    action=(
                        f"Reduce irrigation schedule by {irrigation_reduction_pct:.0f}% "
                        f"during off-peak hours."
                    ),
                    estimated_impact=f"Estimated savings: ~{savings_l:,.0f} L/day",
                    sensor_snapshot={},
                )
            )

        if current_avg < deficit_thresh:
            shortfall_pct = (baseline - current_avg) / baseline * 100
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="demand_deficit",
                    priority="MEDIUM",
                    message=(
                        f"{zone}: Forecast shows demand {shortfall_pct:.0f}% below baseline. "
                        "Possible supply interruption or unusually low usage."
                    ),
                    action="Verify zone connectivity; check for upstream valve closures.",
                    estimated_impact="Undetected supply loss may affect downstream zones.",
                    sensor_snapshot={},
                )
            )

        return recs

    def _check_demand_trend(self, zone: str) -> List[Dict]:
        """
        Fallback: compare last-hour average to prior-hour average from DB.
        Used when no LSTM forecast object is available.
        """
        recs = []
        rows = self._load_recent(limit=1440)  # ~2 hours of 5-second readings
        if len(rows) < 120:
            return recs

        flows = [r["flow"] for r in rows if r.get("flow") is not None]
        if len(flows) < 120:
            return recs

        # Split into two halves
        mid = len(flows) // 2
        recent_avg = float(np.mean(flows[mid:]))
        prior_avg = float(np.mean(flows[:mid]))

        if prior_avg == 0:
            return recs

        change_pct = (recent_avg - prior_avg) / prior_avg

        if change_pct > self.cfg["demand_surge_pct"]:
            savings_l = (
                change_pct
                * self.cfg["flow_baseline"]
                * self.cfg["litres_per_litre_per_min"]
                * self.cfg["irrigation_hours_per_day"]
            )
            recs.append(
                self._make_rec(
                    zone=zone,
                    category="demand_trend_up",
                    priority="MEDIUM",
                    message=(
                        f"{zone}: Demand has risen {change_pct * 100:.0f}% in the last hour. "
                        "Consider pre-emptive load balancing."
                    ),
                    action="Redistribute flow from low-demand zones.",
                    estimated_impact=f"Potential savings if balanced: ~{savings_l:,.0f} L",
                    sensor_snapshot={},
                )
            )

        return recs

    # ------------------------------------------------------------------
    # DB helpers (read-only)
    # ------------------------------------------------------------------

    def _load_recent(self, limit: int = 200) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT flow, pressure, ph, turbidity, temperature
                FROM sensor_data
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            print(f"[RecommendationEngine] DB read error: {e}")
            return []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_rec(
        zone: str,
        category: str,
        priority: str,
        message: str,
        action: str,
        estimated_impact: str,
        sensor_snapshot: Dict,
    ) -> Dict[str, Any]:
        return {
            "zone": zone,
            "category": category,
            "priority": priority,          # HIGH / MEDIUM / LOW
            "message": message,
            "recommended_action": action,
            "estimated_impact": estimated_impact,
            "sensor_snapshot": {
                k: round(v, 3) for k, v in sensor_snapshot.items()
                if v is not None
            },
            "generated_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _finalise(recs: List[Dict]) -> List[Dict]:
        """De-duplicate by category+zone and sort by priority."""
        seen = set()
        unique = []
        for r in recs:
            key = (r["zone"], r["category"])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return sorted(unique, key=lambda r: _PRIORITY_ORDER.get(r["priority"], 99))


# Priority sort order
_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    engine = WaterRecommendationEngine()

    print("=== Test A: direct sensor reading (simulated leak) ===")
    recs = engine.recommend_from_reading(
        zone="Zone-3",
        flow=5.8,
        pressure=1.1,
        ph=7.3,
        turbidity=3.5,
        temperature=26.0,
        is_anomaly=True,
        anomaly_score=-0.45,
    )
    for r in recs:
        print(f"  [{r['priority']}] {r['message']}")
        print(f"       → {r['recommended_action']}")
        print(f"       → {r['estimated_impact']}")

    print("\n=== Test B: forecast-driven (surge scenario) ===")
    import numpy as _np
    baseline = 15.0
    # Simulate a forecast that surges 20% for the next 24 h
    surge_forecast = list(baseline * 1.22 + _np.random.normal(0, 0.3, 288))
    recs = engine.recommend_from_model_outputs(
        zone="Zone-5",
        forecast=surge_forecast,
    )
    for r in recs:
        print(f"  [{r['priority']}] {r['message']}")
        print(f"       → {r['recommended_action']}")
        print(f"       → {r['estimated_impact']}")
