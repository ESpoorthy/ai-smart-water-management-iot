"""
Decision Intelligence - Root Cause Classifier
==============================================
Given a set of sensor readings from a flagged anomaly, classifies the
most likely root cause into one of four categories:

    LEAK               – pipe burst, joint failure, valve malfunction
    CONTAMINATION      – chemical/biological intrusion, sediment, backflow
    UNUSUAL_USAGE      – demand spike, illegal withdrawal, irrigator left on
    SENSOR_FAULT       – sensor drift, wiring issue, out-of-range hardware error

Design notes
------------
* Rule-based; no model retraining required.
* All thresholds are overridable at construction time.
* Accepts the same multi-sensor fields that the existing DB stores
  (flow, pressure, ph, turbidity, temperature) plus optional
  conductivity — degrades gracefully if any field is None/missing.
* Returns a structured dict that is safe to return from FastAPI or
  render in Streamlit.
* Zero edits to existing files.

Quick usage
-----------
    from ai_models.root_cause_classifier import AnomalyRootCauseClassifier

    clf = AnomalyRootCauseClassifier()

    result = clf.classify(
        flow=5.8, pressure=1.1, ph=7.3,
        turbidity=3.2, temperature=26.5
    )
    print(result["root_cause"])          # "LEAK"
    print(result["confidence"])          # "HIGH"
    print(result["explanation"])
    print(result["supporting_evidence"]) # list of triggered rule strings

    # Batch – pass a list of dicts (e.g. from detect_anomalies_batch)
    results = clf.classify_batch(anomaly_list)

Classification logic summary
-----------------------------
LEAK
    Primary:   flow < low_thresh  AND  pressure < low_thresh
    Secondary: flow drop severe (< 50% baseline) even without pressure data

CONTAMINATION
    Primary:   turbidity > high_thresh
    Secondary: ph outside safe band  AND  turbidity elevated
    Secondary: conductivity > high_thresh (if available)

SENSOR_FAULT
    Primary:   any value outside physically plausible hard limits
    Secondary: impossible combination (e.g. negative flow, pressure=0 with
               high flow, pH = 0 or 14)

UNUSUAL_USAGE
    Primary:   flow > high_thresh  AND  pressure normal
    Secondary: flow elevated but all quality indicators normal

When multiple categories are triggered the one with the highest evidence
score wins; ties are broken by the order above.  The `supporting_evidence`
list always contains every triggered rule so the caller has full visibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------
_DEFAULTS = dict(
    # Flow (L/min)
    flow_baseline=15.0,
    flow_low_pct=0.50,          # below 50 % of baseline → severe drop
    flow_low_threshold=8.0,     # below this L/min → possible leak
    flow_high_threshold=22.0,   # above this L/min → possible high usage

    # Pressure (bar)
    pressure_baseline=2.5,
    pressure_low_threshold=1.5,
    pressure_high_threshold=3.5,

    # pH
    ph_low_threshold=6.5,
    ph_high_threshold=8.5,

    # Turbidity (NTU)
    turbidity_baseline=2.0,
    turbidity_moderate=4.0,     # elevated but not alarming
    turbidity_high=5.0,         # clear contamination signal

    # Temperature (°C)
    temperature_high=35.0,

    # Conductivity (µS/cm) — optional sensor
    conductivity_high=800.0,

    # Hard physical limits (sensor fault detection)
    flow_min_physical=-0.1,     # negative flow is impossible
    flow_max_physical=100.0,    # >100 L/min on a residential line → suspect
    pressure_min_physical=0.0,
    pressure_max_physical=10.0,
    ph_min_physical=0.0,
    ph_max_physical=14.0,
    turbidity_min_physical=0.0,
    turbidity_max_physical=3000.0,
    temperature_min_physical=-5.0,
    temperature_max_physical=80.0,
)

# Score weights for each category – higher = stronger signal
_SCORE_WEIGHTS = {
    "LEAK": {
        "flow_low_pressure_low": 3,      # strongest leak signal
        "severe_flow_drop": 2,
        "pressure_low_alone": 1,
    },
    "CONTAMINATION": {
        "turbidity_high": 3,
        "ph_out_of_band_turbidity_elevated": 2,
        "conductivity_high": 2,
        "ph_out_of_band_alone": 1,
    },
    "SENSOR_FAULT": {
        "value_out_of_physical_range": 4,  # strongest fault signal
        "impossible_combination": 3,
    },
    "UNUSUAL_USAGE": {
        "flow_high_pressure_normal": 3,
        "flow_elevated_quality_normal": 1,
    },
}

# Human-readable labels
_LABELS = {
    "LEAK": "Pipe Leak / Valve Malfunction",
    "CONTAMINATION": "Water Contamination / Quality Issue",
    "UNUSUAL_USAGE": "Unusual Demand / Unauthorised Usage",
    "SENSOR_FAULT": "Sensor Fault / Instrument Error",
}


@dataclass
class _Evidence:
    rule_id: str
    category: str
    description: str
    score: int = 1


class AnomalyRootCauseClassifier:
    """
    Rule-based root cause classifier for water network anomalies.

    Parameters
    ----------
    **threshold_overrides
        Any key from _DEFAULTS can be overridden at construction time.
    """

    def __init__(self, **threshold_overrides) -> None:
        self.cfg = {**_DEFAULTS, **threshold_overrides}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def classify(
        self,
        flow: Optional[float] = None,
        pressure: Optional[float] = None,
        ph: Optional[float] = None,
        turbidity: Optional[float] = None,
        temperature: Optional[float] = None,
        conductivity: Optional[float] = None,
        anomaly_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Classify a single anomalous reading.

        All sensor parameters are optional – the classifier degrades
        gracefully when fields are None (rules requiring that field are
        simply skipped).

        Returns
        -------
        dict with keys:
            root_cause          : str  – LEAK | CONTAMINATION | UNUSUAL_USAGE | SENSOR_FAULT
            label               : str  – human-readable category name
            confidence          : str  – HIGH | MEDIUM | LOW
            explanation         : str  – one-sentence plain-English summary
            recommended_action  : str
            supporting_evidence : list[str]  – each triggered rule
            scores              : dict[str, int]  – raw scores per category
            sensor_values       : dict  – sanitised input values
            classified_at       : str  – ISO timestamp
        """
        sensors = dict(
            flow=flow, pressure=pressure, ph=ph,
            turbidity=turbidity, temperature=temperature,
            conductivity=conductivity,
        )

        evidence: List[_Evidence] = []

        # Run all rule groups
        evidence += self._rules_sensor_fault(sensors)
        evidence += self._rules_leak(sensors)
        evidence += self._rules_contamination(sensors)
        evidence += self._rules_unusual_usage(sensors)

        return self._build_result(sensors, evidence, anomaly_score)

    def classify_batch(
        self,
        anomaly_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Classify a list of anomaly dicts.

        Accepts the format returned by LeakDetector.detect_anomalies_batch()
        (keys: index, flow, pressure, score) plus any extra sensor fields
        that happen to be present.
        """
        results = []
        for item in anomaly_list:
            result = self.classify(
                flow=item.get("flow"),
                pressure=item.get("pressure"),
                ph=item.get("ph"),
                turbidity=item.get("turbidity"),
                temperature=item.get("temperature"),
                conductivity=item.get("conductivity"),
                anomaly_score=item.get("score"),
            )
            result["source_index"] = item.get("index")
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Rule groups
    # ------------------------------------------------------------------

    def _rules_sensor_fault(self, s: Dict) -> List[_Evidence]:
        evidence = []
        cfg = self.cfg
        checks = [
            ("flow",        cfg["flow_min_physical"],        cfg["flow_max_physical"]),
            ("pressure",    cfg["pressure_min_physical"],    cfg["pressure_max_physical"]),
            ("ph",          cfg["ph_min_physical"],          cfg["ph_max_physical"]),
            ("turbidity",   cfg["turbidity_min_physical"],   cfg["turbidity_max_physical"]),
            ("temperature", cfg["temperature_min_physical"], cfg["temperature_max_physical"]),
        ]

        for param, lo, hi in checks:
            val = s.get(param)
            if val is not None and (val < lo or val > hi):
                evidence.append(_Evidence(
                    rule_id="value_out_of_physical_range",
                    category="SENSOR_FAULT",
                    description=(
                        f"{param}={val:.3g} is outside the physically plausible "
                        f"range [{lo}, {hi}] — likely sensor malfunction or wiring fault."
                    ),
                    score=_SCORE_WEIGHTS["SENSOR_FAULT"]["value_out_of_physical_range"],
                ))

        # Impossible combination: flow is very high but pressure is zero
        flow = s.get("flow")
        pressure = s.get("pressure")
        if (
            flow is not None and pressure is not None
            and flow > cfg["flow_low_threshold"]
            and pressure <= 0.01
        ):
            evidence.append(_Evidence(
                rule_id="impossible_combination",
                category="SENSOR_FAULT",
                description=(
                    f"Impossible reading: flow={flow:.1f} L/min but pressure≈0 bar. "
                    "At least one sensor is likely faulty."
                ),
                score=_SCORE_WEIGHTS["SENSOR_FAULT"]["impossible_combination"],
            ))

        return evidence

    def _rules_leak(self, s: Dict) -> List[_Evidence]:
        evidence = []
        cfg = self.cfg
        flow = s.get("flow")
        pressure = s.get("pressure")

        # Strongest signal: both flow AND pressure are low
        if (
            flow is not None and pressure is not None
            and flow < cfg["flow_low_threshold"]
            and pressure < cfg["pressure_low_threshold"]
        ):
            evidence.append(_Evidence(
                rule_id="flow_low_pressure_low",
                category="LEAK",
                description=(
                    f"Flow={flow:.1f} L/min AND Pressure={pressure:.2f} bar are both "
                    "below threshold — classic dual-drop signature of a pipe leak."
                ),
                score=_SCORE_WEIGHTS["LEAK"]["flow_low_pressure_low"],
            ))

        # Severe flow drop alone (pressure data unavailable or borderline)
        if flow is not None and flow < cfg["flow_baseline"] * cfg["flow_low_pct"]:
            evidence.append(_Evidence(
                rule_id="severe_flow_drop",
                category="LEAK",
                description=(
                    f"Flow={flow:.1f} L/min — more than 50% below baseline "
                    f"({cfg['flow_baseline']} L/min). Severe supply loss detected."
                ),
                score=_SCORE_WEIGHTS["LEAK"]["severe_flow_drop"],
            ))

        # Pressure low alone (flow may not be instrumented everywhere)
        if (
            pressure is not None
            and pressure < cfg["pressure_low_threshold"]
            and (flow is None or flow >= cfg["flow_low_threshold"])
        ):
            evidence.append(_Evidence(
                rule_id="pressure_low_alone",
                category="LEAK",
                description=(
                    f"Pressure={pressure:.2f} bar below threshold "
                    f"({cfg['pressure_low_threshold']} bar) with flow not severely low — "
                    "possible small leak or partially-open valve."
                ),
                score=_SCORE_WEIGHTS["LEAK"]["pressure_low_alone"],
            ))

        return evidence

    def _rules_contamination(self, s: Dict) -> List[_Evidence]:
        evidence = []
        cfg = self.cfg
        ph = s.get("ph")
        turbidity = s.get("turbidity")
        conductivity = s.get("conductivity")

        # Turbidity high — strongest contamination signal
        if turbidity is not None and turbidity > cfg["turbidity_high"]:
            evidence.append(_Evidence(
                rule_id="turbidity_high",
                category="CONTAMINATION",
                description=(
                    f"Turbidity={turbidity:.1f} NTU exceeds WHO guideline "
                    f"({cfg['turbidity_high']} NTU) — sediment intrusion, backflow, "
                    "or biological contamination suspected."
                ),
                score=_SCORE_WEIGHTS["CONTAMINATION"]["turbidity_high"],
            ))

        # pH out of safe band + elevated turbidity
        ph_out = ph is not None and (ph < cfg["ph_low_threshold"] or ph > cfg["ph_high_threshold"])
        turbidity_elevated = turbidity is not None and turbidity > cfg["turbidity_moderate"]

        if ph_out and turbidity_elevated:
            direction = "acidic" if ph < cfg["ph_low_threshold"] else "alkaline"
            evidence.append(_Evidence(
                rule_id="ph_out_of_band_turbidity_elevated",
                category="CONTAMINATION",
                description=(
                    f"pH={ph:.2f} ({direction}) combined with elevated turbidity="
                    f"{turbidity:.1f} NTU — chemical contamination or backflow event likely."
                ),
                score=_SCORE_WEIGHTS["CONTAMINATION"]["ph_out_of_band_turbidity_elevated"],
            ))
        elif ph_out:
            direction = "acidic" if ph < cfg["ph_low_threshold"] else "alkaline"
            evidence.append(_Evidence(
                rule_id="ph_out_of_band_alone",
                category="CONTAMINATION",
                description=(
                    f"pH={ph:.2f} ({direction}) — outside safe range "
                    f"[{cfg['ph_low_threshold']}, {cfg['ph_high_threshold']}]. "
                    "May indicate chemical dosing error or source contamination."
                ),
                score=_SCORE_WEIGHTS["CONTAMINATION"]["ph_out_of_band_alone"],
            ))

        # Conductivity spike (optional sensor)
        if conductivity is not None and conductivity > cfg["conductivity_high"]:
            evidence.append(_Evidence(
                rule_id="conductivity_high",
                category="CONTAMINATION",
                description=(
                    f"Conductivity={conductivity:.0f} µS/cm exceeds threshold "
                    f"({cfg['conductivity_high']} µS/cm) — dissolved solids or "
                    "ionic contamination detected."
                ),
                score=_SCORE_WEIGHTS["CONTAMINATION"]["conductivity_high"],
            ))

        return evidence

    def _rules_unusual_usage(self, s: Dict) -> List[_Evidence]:
        evidence = []
        cfg = self.cfg
        flow = s.get("flow")
        pressure = s.get("pressure")
        ph = s.get("ph")
        turbidity = s.get("turbidity")

        # Flow high but pressure is in normal range
        pressure_normal = (
            pressure is None
            or cfg["pressure_low_threshold"] <= pressure <= cfg["pressure_high_threshold"]
        )

        if flow is not None and flow > cfg["flow_high_threshold"] and pressure_normal:
            evidence.append(_Evidence(
                rule_id="flow_high_pressure_normal",
                category="UNUSUAL_USAGE",
                description=(
                    f"Flow={flow:.1f} L/min above high threshold "
                    f"({cfg['flow_high_threshold']} L/min) with normal pressure — "
                    "demand spike, irrigation system left on, or unauthorised withdrawal."
                ),
                score=_SCORE_WEIGHTS["UNUSUAL_USAGE"]["flow_high_pressure_normal"],
            ))

        # Elevated flow but quality indicators are all fine
        quality_normal = (
            (ph is None or cfg["ph_low_threshold"] <= ph <= cfg["ph_high_threshold"])
            and (turbidity is None or turbidity <= cfg["turbidity_moderate"])
        )
        if (
            flow is not None
            and cfg["flow_low_threshold"] <= flow <= cfg["flow_high_threshold"]
            and quality_normal
            and not any(e.category == "LEAK" for e in evidence)
        ):
            # Only fire this weak rule if flow is slightly elevated and everything else
            # looks normal — distinguishes from borderline leak cases
            if flow > cfg["flow_baseline"] * 1.1:
                evidence.append(_Evidence(
                    rule_id="flow_elevated_quality_normal",
                    category="UNUSUAL_USAGE",
                    description=(
                        f"Flow={flow:.1f} L/min slightly above baseline with no quality "
                        "issues — pattern consistent with above-average consumption."
                    ),
                    score=_SCORE_WEIGHTS["UNUSUAL_USAGE"]["flow_elevated_quality_normal"],
                ))

        return evidence

    # ------------------------------------------------------------------
    # Result builder
    # ------------------------------------------------------------------

    def _build_result(
        self,
        sensors: Dict,
        evidence: List[_Evidence],
        anomaly_score: Optional[float],
    ) -> Dict[str, Any]:
        # Tally scores per category
        scores: Dict[str, int] = {
            "LEAK": 0, "CONTAMINATION": 0,
            "UNUSUAL_USAGE": 0, "SENSOR_FAULT": 0,
        }
        for ev in evidence:
            scores[ev.category] += ev.score

        # Winner
        max_score = max(scores.values())

        if max_score == 0:
            # Nothing triggered — report as UNUSUAL_USAGE at LOW confidence
            root_cause = "UNUSUAL_USAGE"
            confidence = "LOW"
        else:
            # Break ties: SENSOR_FAULT > LEAK > CONTAMINATION > UNUSUAL_USAGE
            tie_break = ["SENSOR_FAULT", "LEAK", "CONTAMINATION", "UNUSUAL_USAGE"]
            candidates = [c for c in tie_break if scores[c] == max_score]
            root_cause = candidates[0]

            total_evidence = sum(scores.values())
            winning_share = max_score / total_evidence if total_evidence else 0
            if winning_share >= 0.75 or max_score >= 4:
                confidence = "HIGH"
            elif winning_share >= 0.50 or max_score >= 2:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"

        explanation, action = _EXPLANATIONS.get(
            root_cause, ("Anomaly detected.", "Investigate sensor readings.")
        )

        return {
            "root_cause": root_cause,
            "label": _LABELS[root_cause],
            "confidence": confidence,
            "explanation": explanation,
            "recommended_action": action,
            "supporting_evidence": [ev.description for ev in evidence],
            "scores": scores,
            "anomaly_score": round(anomaly_score, 4) if anomaly_score is not None else None,
            "sensor_values": {
                k: round(v, 3) for k, v in sensors.items() if v is not None
            },
            "classified_at": datetime.now().isoformat(),
        }


# ---------------------------------------------------------------------------
# Canned explanations and recommended actions per root cause
# ---------------------------------------------------------------------------
_EXPLANATIONS: Dict[str, tuple] = {
    "LEAK": (
        "Simultaneous drop in flow and/or pressure indicates a likely pipe leak "
        "or valve malfunction in this zone.",
        "Dispatch field team to inspect pipeline joints, pressure relief valves, "
        "and meter connections. Isolate the affected segment if loss exceeds 30%.",
    ),
    "CONTAMINATION": (
        "Elevated turbidity and/or abnormal pH indicates water quality degradation — "
        "possible sediment intrusion, backflow, or chemical contamination.",
        "Issue a precautionary do-not-drink advisory. Flush the affected main, "
        "collect a water sample for lab testing, and check upstream dosing systems.",
    ),
    "UNUSUAL_USAGE": (
        "Flow is significantly above normal while pressure and quality remain stable — "
        "consistent with a demand spike, irrigation system fault, or unauthorised withdrawal.",
        "Cross-check consumption records for this zone. Inspect irrigation controllers "
        "and fire hydrant logs. Notify the zone supervisor.",
    ),
    "SENSOR_FAULT": (
        "One or more sensor readings are outside physically plausible ranges, "
        "suggesting instrument malfunction, wiring fault, or calibration drift.",
        "Run a sensor self-test and check field wiring. Replace or recalibrate the "
        "suspect instrument before acting on the anomaly signal.",
    ),
}


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    clf = AnomalyRootCauseClassifier()

    scenarios = [
        {
            "label": "Pipe leak",
            "flow": 5.8, "pressure": 1.1, "ph": 7.3,
            "turbidity": 3.0, "temperature": 26.0,
        },
        {
            "label": "Contamination",
            "flow": 14.5, "pressure": 2.4, "ph": 9.1,
            "turbidity": 8.7, "temperature": 25.5,
        },
        {
            "label": "Unusual usage",
            "flow": 28.0, "pressure": 2.6, "ph": 7.2,
            "turbidity": 2.1, "temperature": 25.0,
        },
        {
            "label": "Sensor fault",
            "flow": -3.0, "pressure": 2.5, "ph": 7.1,
            "turbidity": 2.0, "temperature": 25.0,
        },
        {
            "label": "Contamination (conductivity)",
            "flow": 15.0, "pressure": 2.5, "ph": 7.8,
            "turbidity": 6.2, "temperature": 25.0,
            "conductivity": 950.0,
        },
    ]

    for s in scenarios:
        label = s.pop("label")
        result = clf.classify(**s)
        print(f"\n{'='*60}")
        print(f"Scenario : {label}")
        print(f"Root cause: {result['root_cause']} ({result['confidence']})")
        print(f"Explanation: {result['explanation']}")
        print(f"Action: {result['recommended_action']}")
        print(f"Evidence ({len(result['supporting_evidence'])} rules triggered):")
        for ev in result["supporting_evidence"]:
            print(f"  • {ev}")
