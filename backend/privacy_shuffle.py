import copy
import random
from typing import Any, Dict, List


def derive_privacy_profile(raw_results: List[Dict[str, Any]], raw_report: Dict[str, Any]) -> Dict[str, Any]:
    metric_buckets = []
    for metric in raw_report.get("metrics", []):
        metric_buckets.append(
            {
                "name": metric.get("name"),
                "status": metric.get("status"),
                "unit": metric.get("unit"),
            }
        )

    return {
        "overall": raw_report.get("overall", "Watch"),
        "risk_level": raw_report.get("fall_risk", {}).get("level", "Moderate"),
        "metric_buckets": metric_buckets,
        "result_statuses": [row.get("status", "normal") for row in raw_results],
    }


def _jitter_numeric(value: Any, rng: random.Random, spread: float) -> Any:
    if not isinstance(value, (int, float)):
        return value
    return round(float(value) + rng.uniform(-spread, spread), 2)


def _mutate_results(raw_results: List[Dict[str, Any]], rng: random.Random) -> List[Dict[str, Any]]:
    mutated = copy.deepcopy(raw_results)
    for row in mutated:
        row["score"] = _jitter_numeric(row.get("score"), rng, 6.0)
    return mutated


def _mutate_metric(metric: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    metric_copy = copy.deepcopy(metric)
    metric_copy["value"] = _jitter_numeric(metric_copy.get("value"), rng, 5.0)
    return metric_copy


def _mutate_report(raw_report: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    report = copy.deepcopy(raw_report)

    report["metrics"] = [_mutate_metric(metric, rng) for metric in report.get("metrics", [])]

    fall_risk = report.get("fall_risk", {})
    if "probability" in fall_risk:
        fall_risk["probability"] = max(
            0.05,
            min(0.95, _jitter_numeric(fall_risk["probability"], rng, 0.08)),
        )

    charts = report.get("charts", {})
    activity_mix = charts.get("activity_mix", {})
    if "values" in activity_mix and isinstance(activity_mix["values"], list):
        values = [max(0.01, float(v) + rng.uniform(-0.04, 0.04)) for v in activity_mix["values"]]
        total = sum(values)
        if total > 0:
            activity_mix["values"] = [round(v / total, 4) for v in values]

    radar = charts.get("radar", {})
    if "values" in radar and isinstance(radar["values"], list):
        radar["values"] = [max(0.0, min(100.0, _jitter_numeric(v, rng, 4.0))) for v in radar["values"]]

    vitals = charts.get("vitals", {})
    if "values" in vitals and isinstance(vitals["values"], list):
        vitals["values"] = [_jitter_numeric(v, rng, 4.0) for v in vitals["values"]]

    report["narrative"] = (
        f"Protected synthetic summary: {report.get('overall', 'Watch')} status with "
        f"{fall_risk.get('level', 'Moderate')} fall-risk profile."
    )
    report["disclaimer"] = "Privacy-protected synthetic report for demo use only — not for medical use."
    return report


def generate_synthetic_candidate_pool(
    profile: Dict[str, Any],
    raw_results: List[Dict[str, Any]],
    raw_report: Dict[str, Any],
    pool_size: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    pool = []
    for idx in range(pool_size):
        pool.append(
            {
                "label": f"Candidate {idx + 1}",
                "profile": copy.deepcopy(profile),
                "results": _mutate_results(raw_results, rng),
                "report": _mutate_report(raw_report, rng),
            }
        )
    return pool


def select_protected_candidate(pool: List[Dict[str, Any]], rng: random.Random) -> Dict[str, Any]:
    shuffled = list(pool)
    rng.shuffle(shuffled)
    selected = copy.deepcopy(shuffled[0])
    selected["label"] = "Protected Output"
    return selected


def build_display_candidates(pool: List[Dict[str, Any]], limit: int = 4) -> List[Dict[str, Any]]:
    cards = []
    for candidate in pool[:limit]:
        report = candidate.get("report", {})
        fall_risk = report.get("fall_risk", {})
        metric_summary = []
        for metric in report.get("metrics", []):
            status = str(metric.get("status", "")).lower()
            if status in {"low", "elevated", "high", "moderate"}:
                metric_summary.append(f"{metric.get('name')} {status}")
            if len(metric_summary) == 3:
                break
        cards.append(
            {
                "label": candidate.get("label", "Candidate"),
                "overall": report.get("overall", "Watch"),
                "risk_level": fall_risk.get("level", "Moderate"),
                "metric_summary": metric_summary or ["Protected summary"],
            }
        )
    return cards
