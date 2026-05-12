import copy
import random
import bisect
import math
import re
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


def build_real_data_record(raw_results: List[Dict[str, Any]], raw_report: Dict[str, Any]) -> Dict[str, Any]:
    metrics_by_name = {metric.get("name"): metric for metric in raw_report.get("metrics", [])}
    normalized_metrics = {
        _normalize_metric_name(metric.get("name")): metric
        for metric in raw_report.get("metrics", [])
        if _normalize_metric_name(metric.get("name"))
    }

    def _resolve_metric_value(alias_groups: List[str]) -> tuple:
        for alias in alias_groups:
            if alias in normalized_metrics:
                metric = normalized_metrics.get(alias, {})
                return metric.get("value"), metric.get("status", "normal")
            if metric := next(
                (
                    item
                    for key, item in normalized_metrics.items()
                    if all(word in key.split(" ") for word in alias.split(" ") if word)
                ),
                None,
            ):
                return metric.get("value"), metric.get("status", "normal")
        return None, "normal"

    heart_rate_value, heart_rate_status = _resolve_metric_value([
        "heart rate",
        "heartrate",
        "hr",
    ])
    respiratory_rate_value, respiratory_rate_status = _resolve_metric_value([
        "respiratory rate",
        "resp rate",
        "rr",
        "resp",
    ])
    blood_pressure_value, blood_pressure_status = _resolve_metric_value([
        "blood pressure",
        "sbp",
        "bp",
    ])
    spo2_value, spo2_status = _resolve_metric_value([
        "spo2",
        "spo 2",
        "oxygen saturation",
        "sp o2",
    ])
    sleep_efficiency_value, sleep_efficiency_status = _resolve_metric_value([
        "sleep efficiency",
        "sleepeff",
    ])
    cadence_value, cadence_status = _resolve_metric_value([
        "cadence",
        "step cadence",
        "step rate",
    ])

    # compatibility fallback for older mock/report formats
    if heart_rate_value is None:
        heart_rate_value = metrics_by_name.get("Heart Rate", {}).get("value", heart_rate_value)
        heart_rate_status = metrics_by_name.get("Heart Rate", {}).get("status", heart_rate_status)
    if respiratory_rate_value is None:
        respiratory_rate_value = metrics_by_name.get("Respiratory Rate", {}).get("value", respiratory_rate_value)
        respiratory_rate_status = metrics_by_name.get("Respiratory Rate", {}).get("status", respiratory_rate_status)
    if blood_pressure_value is None:
        blood_pressure_value = metrics_by_name.get("Blood Pressure", {}).get("value", blood_pressure_value)
        blood_pressure_status = metrics_by_name.get("Blood Pressure", {}).get("status", blood_pressure_status)
    if spo2_value is None:
        spo2_value = metrics_by_name.get("SpO2", {}).get("value", spo2_value)
        spo2_status = metrics_by_name.get("SpO2", {}).get("status", spo2_status)
    if sleep_efficiency_value is None:
        sleep_efficiency_value = metrics_by_name.get("Sleep Efficiency", {}).get("value", sleep_efficiency_value)
        sleep_efficiency_status = metrics_by_name.get("Sleep Efficiency", {}).get("status", sleep_efficiency_status)
    if cadence_value is None:
        cadence_value = metrics_by_name.get("Cadence", {}).get("value", cadence_value)
        cadence_status = metrics_by_name.get("Cadence", {}).get("status", cadence_status)

    charts = raw_report.get("charts", {})
    return {
        "kind": "real",
        "label": "Real Record",
        "risk_bucket": str(raw_report.get("fall_risk", {}).get("level", "moderate")).lower(),
        "overall": raw_report.get("overall", "Watch"),
        "model_outputs": copy.deepcopy(raw_results),
        "derived_metrics": {
            "fall_probability": raw_report.get("fall_risk", {}).get("probability"),
            "heart_rate": heart_rate_value,
            "heart_rate_status": heart_rate_status,
            "respiratory_rate": respiratory_rate_value,
            "respiratory_rate_status": respiratory_rate_status,
            "blood_pressure": blood_pressure_value,
            "blood_pressure_status": blood_pressure_status,
            "spo2": spo2_value,
            "spo2_status": spo2_status,
            "sleep_efficiency": sleep_efficiency_value,
            "sleep_efficiency_status": sleep_efficiency_status,
            "cadence": cadence_value,
            "cadence_status": cadence_status,
            "activity_mix": copy.deepcopy(charts.get("activity_mix", {})),
            "radar": copy.deepcopy(charts.get("radar", {})),
            "vitals": copy.deepcopy(charts.get("vitals", {})),
        },
    }


def _normalize_metric_name(name: Any) -> str:
    if not isinstance(name, str):
        return ""
    normalized = name.lower().replace("₂", "2").strip()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_number(value: Any) -> Any:
    if not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if math.isnan(parsed) or math.isinf(parsed):
        return None
    return parsed


def _sample_distribution_value(mean: float, std_dev: float, low: float, high: float, rng: random.Random) -> float:
    return round(_clamp(float(rng.gauss(mean, std_dev)), low, high), 2)


def _sample_probability_value(mean: float, std_dev: float, rng: random.Random) -> float:
    return round(_clamp(float(rng.gauss(mean, std_dev)), 0.05, 0.95), 2)


def _sample_activity_mix(rng: random.Random) -> Dict[str, Any]:
    labels = ["Walk", "Stand", "Sit", "Sleep"]
    raw = [rng.uniform(0.1, 0.4) for _ in labels]
    total = sum(raw)
    values = [round(value / total, 4) for value in raw]
    values[-1] = round(1.0 - sum(values[:-1]), 4)
    return {"labels": labels, "values": values}


def _status_for_score(score: float) -> str:
    if score >= 85:
        return "good"
    if score >= 65:
        return "normal"
    if score >= 45:
        return "attention"
    return "low"


def _status_for_probability(probability: float) -> str:
    if probability >= 0.6:
        return "elevated"
    if probability >= 0.3:
        return "moderate"
    return "low"


def _risk_bucket_for_probability(probability: float) -> str:
    if probability < 0.3:
        return "low"
    if probability < 0.6:
        return "attention"
    return "elevated"


def generate_synthetic_database(
    real_record: Dict[str, Any],
    database_size: int,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    records = []
    real_metrics = real_record.get("derived_metrics", {})
    real_outputs = real_record.get("model_outputs", [])

    fall_mean = _safe_number(real_metrics.get("fall_probability")) or 0.25
    heart_mean = _safe_number(real_metrics.get("heart_rate")) or 76
    respiratory_mean = _safe_number(real_metrics.get("respiratory_rate")) or 16
    bp_mean = _safe_number(real_metrics.get("blood_pressure")) or 125
    spo2_mean = _safe_number(real_metrics.get("spo2")) or 97
    sleep_mean = _safe_number(real_metrics.get("sleep_efficiency")) or 82
    cadence_mean = _safe_number(real_metrics.get("cadence")) or 92

    for index in range(database_size):
        fall_probability = round(
            _sample_probability_value(fall_mean, 0.12, rng),
            2,
        )
        heart_rate = _sample_distribution_value(heart_mean, 14.0, 45, 130, rng)
        respiratory_rate = round(
            _sample_distribution_value(respiratory_mean, 2.6, 8, 30, rng)
        )
        blood_pressure = round(
            _sample_distribution_value(bp_mean, 16.0, 90, 180, rng)
        )
        sleep_efficiency = round(
            _sample_distribution_value(sleep_mean, 10.0, 40, 98, rng)
        )
        cadence = round(_sample_distribution_value(cadence_mean, 10.0, 55, 130, rng))
        model_outputs = []
        for output in real_outputs:
            score = output.get("score")
            if isinstance(score, (int, float)):
                if 0 <= float(score) <= 1:
                    synthetic_score = round(_clamp(float(score) + rng.uniform(-0.12, 0.12), 0.05, 0.95), 2)
                    synthetic_status = _status_for_probability(float(synthetic_score))
                else:
                    synthetic_score = round(_clamp(float(score) + rng.uniform(-9, 9), 0, 10000), 2)
                    synthetic_status = (
                        _status_for_score(float(synthetic_score))
                        if float(synthetic_score) <= 100
                        else output.get("status", "normal")
                    )
            else:
                synthetic_score = score
                synthetic_status = output.get("status", "normal")
            model_outputs.append(
                {
                    **copy.deepcopy(output),
                    "score": synthetic_score,
                    "status": synthetic_status,
                }
            )
        records.append(
            {
                "kind": "synthetic",
                "label": f"Synthetic Record {index + 1}",
                "risk_bucket": _risk_bucket_for_probability(fall_probability),
                "overall": real_record.get("overall", "Watch"),
                "model_outputs": model_outputs,
                "derived_metrics": {
                    "fall_probability": fall_probability,
                    "heart_rate": heart_rate,
                    "respiratory_rate": respiratory_rate,
                    "blood_pressure": blood_pressure,
                    "spo2": round(_sample_distribution_value(spo2_mean, 1.2, 90, 100, rng)),
                    "sleep_efficiency": sleep_efficiency,
                    "cadence": cadence,
                    "activity_mix": _sample_activity_mix(rng),
                    "radar": copy.deepcopy(real_metrics.get("radar", {})),
                    "vitals": copy.deepcopy(real_metrics.get("vitals", {})),
                },
            }
        )
    return records


def _preview_record(record: Dict[str, Any], label: str) -> Dict[str, Any]:
    metrics = record.get("derived_metrics", {})
    outputs = record.get("model_outputs", [])
    normal_count = sum(1 for output in outputs if str(output.get("status", "")).lower() in {"normal", "good"})
    return {
        "label": label,
        "risk_bucket": record.get("risk_bucket", "attention"),
        "status_mix": "normal dominant" if normal_count >= max(1, len(outputs) // 2) else "watch mixed",
        "metric_shape": "balanced" if float(metrics.get("fall_probability") or 0.5) < 0.35 else "attention",
    }


def build_anonymous_database(
    real_record: Dict[str, Any],
    synthetic_records: List[Dict[str, Any]],
    rng: random.Random,
) -> Dict[str, Any]:
    real_token = f"real-{rng.randrange(10 ** 9)}"
    tagged_real = copy.deepcopy(real_record)
    tagged_real["_selection_token"] = real_token
    combined = [copy.deepcopy(record) for record in synthetic_records] + [tagged_real]
    rng.shuffle(combined)

    anonymous_database = []
    selected_record = None
    selected_record_index = 0
    for index, record in enumerate(combined):
        anonymous_label = f"Synthetic Record {index + 1:02d}"
        record_copy = copy.deepcopy(record)
        record_copy["_anonymous_label"] = anonymous_label
        anonymous_database.append(record_copy)
        if record_copy.get("_selection_token") == real_token:
            selected_record = record_copy
            selected_record_index = index

    if selected_record is None:
        raise ValueError("real record token was not found after shuffling")

    shuffle_order = [
        record.get("_anonymous_label", f"Synthetic Record {index + 1:02d}")
        for index, record in enumerate(anonymous_database)
    ]
    return {
        "anonymous_database": anonymous_database,
        "anonymous_database_preview": [
            _preview_record(record, record.get("_anonymous_label", f"Synthetic Record {index + 1:02d}"))
            for index, record in enumerate(anonymous_database[:6])
        ],
        "shuffle_order_preview": shuffle_order,
        "selected_record": selected_record,
        "selected_record_label": selected_record.get("_anonymous_label", "Synthetic Record"),
        "selected_record_index": selected_record_index,
    }


def _distribution_point(record: Dict[str, Any], label: str, index: int, target: bool = False) -> Dict[str, Any]:
    metrics = record.get("derived_metrics", {})
    x = _normalize_axis_value(metrics.get("__dist_x", metrics.get("fall_probability")), default=0.5)
    y = _normalize_axis_value(metrics.get("__dist_y", metrics.get("sleep_efficiency")), default=70.0 / 100.0)
    return {
        "label": label,
        "x": round(_clamp(x, 0.0, 1.0), 3),
        "y": round(_clamp(y, 0.0, 1.0), 3),
        "bucket": record.get("risk_bucket", "attention"),
        "target": target,
        "index": index,
    }


def _normalize_distributions(values: List[float]) -> List[float]:
    if not values:
        return []
    sorted_values = sorted(values)
    # remove duplicates with stable spacing to keep percentile lookup meaningful
    return sorted_values


def _normalize_axis_value(value: Any, *, default: float = 0.5) -> float:
    parsed = _safe_number(value)
    if parsed is None:
        return default
    if 0.0 <= parsed <= 1.0:
        return parsed
    if 0.0 <= parsed <= 100.0:
        return parsed / 100.0
    return default


def _percentile_position(value: float, ordered_values: List[float], index: int) -> float:
    if not ordered_values:
        return ((index * 17 + 11) % 84) / 100 + 0.08
    if len(ordered_values) == 1:
        return 0.5

    idx = bisect.bisect_left(ordered_values, value)
    idx = min(max(idx, 0), len(ordered_values) - 1)
    base = idx / (len(ordered_values) - 1)
    jitter = ((index % 7) - 3) / 100
    return _clamp(base + jitter * 0.06, 0.05, 0.95)


def build_distribution_summary(bundle: Dict[str, Any], max_points: int = 48) -> Dict[str, Any]:
    records = bundle.get("anonymous_database", [])
    selected_label = bundle.get("selected_record_label", "Synthetic Record")
    synthetic_count = sum(1 for record in records if record.get("kind") == "synthetic")
    bucket_names = ["low", "attention", "elevated"]
    bucket_counts = {bucket: 0 for bucket in bucket_names}
    for record in records:
        bucket = record.get("risk_bucket", "attention")
        if bucket not in bucket_counts:
            bucket = "attention"
        bucket_counts[bucket] += 1

    total = len(records) or 1
    fall_values = [
        float(metrics.get("fall_probability"))
        for record in records
        for metrics in [record.get("derived_metrics", {})]
        if isinstance(metrics.get("fall_probability"), (int, float))
    ]
    fall_distribution = _normalize_distributions(
        fall_values
    )
    sleep_distribution = _normalize_distributions(
        [
            float(metrics.get("sleep_efficiency"))
            for record in records
            for metrics in [record.get("derived_metrics", {})]
            if isinstance(metrics.get("sleep_efficiency"), (int, float))
        ]
    )

    scatter_points = []
    selected_record = None
    selected_index = int(bundle.get("selected_record_index", 0))
    for index, record in enumerate(records):
        label = record.get("_anonymous_label", f"Synthetic Record {index + 1:02d}")
        is_target = label == selected_label
        if is_target:
            selected_record = record
        if len(scatter_points) < max_points or is_target:
            metrics = record.get("derived_metrics", {})
            scatter_metrics = record.copy()
            scatter_metrics["derived_metrics"] = copy.deepcopy(metrics)
            base_fall = _safe_number(metrics.get("fall_probability"))
            base_sleep = _safe_number(metrics.get("sleep_efficiency"))
            x_norm = _percentile_position(base_fall if base_fall is not None else 0.5, fall_distribution, index)
            y_norm = _percentile_position(base_sleep if base_sleep is not None else 50.0, sleep_distribution, index)
            scatter_metrics["derived_metrics"]["__dist_x"] = x_norm
            scatter_metrics["derived_metrics"]["__dist_y"] = y_norm
            if is_target:
                selected_record = scatter_metrics
            scatter_points.append(_distribution_point(scatter_metrics, label, index, target=is_target))

    if selected_record is None and bundle.get("selected_record"):
        selected_record = bundle["selected_record"]
    selected_record_copy = copy.deepcopy(selected_record) if selected_record else {}
    selected_metrics = selected_record_copy.setdefault("derived_metrics", {})
    selected_metrics["__dist_x"] = _normalize_axis_value(
        selected_metrics.get("__dist_x"),
        default=_percentile_position(
            (_safe_number(selected_metrics.get("fall_probability")) or 0.5),
            fall_distribution,
            selected_index,
        ),
    )
    selected_metrics["__dist_y"] = _normalize_axis_value(
        selected_metrics.get("__dist_y"),
        default=_percentile_position(
            (_safe_number(selected_metrics.get("sleep_efficiency")) or 50.0),
            sleep_distribution,
            selected_index,
        ),
    )
    target_point = _distribution_point(
        selected_record_copy,
        selected_label,
        bundle.get("selected_record_index", 0),
        target=True,
    )

    histogram_bins = 8
    value_histogram = []
    if fall_values:
        low = min(fall_values)
        high = max(fall_values)
        if abs(high - low) < 1e-9:
            low = _clamp(low - 0.05, 0.0, 1.0)
            high = _clamp(high + 0.05, 0.0, 1.0)
        step = (high - low) / histogram_bins if high > low else 1.0 / histogram_bins
        counts = [0 for _ in range(histogram_bins)]
        for value in fall_values:
            if step <= 0:
                idx = 0
            else:
                idx = int((value - low) / step)
            idx = min(max(idx, 0), histogram_bins - 1)
            counts[idx] += 1
        for idx, count in enumerate(counts):
            start = low + step * idx
            end = low + step * (idx + 1)
            value_histogram.append(
                {
                    "start": round(_clamp(start, 0.0, 1.0), 3),
                    "end": round(_clamp(end, 0.0, 1.0), 3),
                    "count": count,
                }
            )

    return {
        "database_size": len(records),
        "synthetic_record_count": synthetic_count,
        "value_histogram": value_histogram,
        "risk_buckets": [
            {
                "bucket": bucket,
                "count": bucket_counts.get(bucket, 0),
                "ratio": round(bucket_counts.get(bucket, 0) / total, 3),
            }
            for bucket in bucket_names
        ],
        "scatter_points": scatter_points,
        "target_point": target_point,
        "axes": {
            "x": "fall_probability",
            "y": "sleep_efficiency_percentile",
            "x_source": "fall_probability",
            "y_source": "sleep_efficiency",
        },
        "token_flow": {
            "token_label": "hidden backend token",
            "generation": "H(session_seed, real_id, nonce)",
            "binding": "token bound to real homomorphic inference record",
            "lookup": "real_record = token_map[token]",
            "visibility": "backend_only",
        },
    }


def _bucket_percent(value: Any, width: int = 5) -> str:
    if not isinstance(value, (int, float)):
        return "masked bucket"
    percent = int(round(float(value) * 100))
    low = (percent // width) * width
    return f"{low}-{low + width}%"


def _bucket_number(value: Any, width: int = 5) -> str:
    if not isinstance(value, (int, float)):
        return "masked bucket"
    low = int(float(value) // width) * width
    return f"{low}-{low + width}"


def _finance_score_bucket(value: Any, width: int = 5) -> str:
    if not isinstance(value, (int, float)):
        return "masked bucket"
    score = max(0.0, min(100.0, float(value)))
    if score >= 100.0:
        low = 100 - width
    else:
        low = int(score // width) * width
    return f"{low}-{low + width}"


def _metric_bucket(name: str, value: Any, status: str = "normal") -> str:
    if not isinstance(value, (int, float)):
        status_label = str(status or "").lower()
        if status_label in {"good", "normal"}:
            return "normal range"
        if status_label in {"low", "moderate", "attention", "high", "elevated", "abnormal"}:
            return "attention"
        return "masked range"

    if name == "blood_pressure":
        if value >= 140:
            return "elevated"
        if value >= 120:
            return "slightly elevated"
        return "normal range"
    if name == "sleep_efficiency":
        if value >= 85:
            return "good"
        if value >= 70:
            return "attention"
        return "low"
    if name == "spo2":
        return "normal range" if value >= 95 else "attention"
    if name == "heart_rate":
        return "normal range" if 60 <= value <= 100 else "attention"
    if name == "respiratory_rate":
        return "normal range" if 12 <= value <= 20 else "attention"
    return "normal range"


def build_protected_llm_summary(record: Dict[str, Any]) -> Dict[str, Any]:
    metrics = record.get("derived_metrics", {})
    if record.get("domain") == "finance":
        return {
            "domain": "finance",
            "record": record.get("_anonymous_label") or record.get("label", "Synthetic Record"),
            "risk_profile": {
                "overall": record.get("overall", "Watch"),
                "financial_resilience_bucket": _bucket_percent(metrics.get("financial_resilience")),
                "risk_bucket": record.get("risk_bucket", "attention"),
            },
            "model_results": [
                {
                    "model": output.get("model"),
                    "status": output.get("status"),
                    "score_bucket": _finance_score_bucket(output.get("score")),
                }
                for output in record.get("model_outputs", [])
            ],
            "metrics": {
                "cashflow_burden": _bucket_percent(metrics.get("cashflow_burden")),
                "loan_stress": _bucket_percent(metrics.get("loan_stress")),
                "credit_standing": _bucket_number(metrics.get("credit_standing"), width=50),
                "debt_to_income": _bucket_number(metrics.get("debt_to_income"), width=1),
            },
        }

    return {
        "record": record.get("_anonymous_label", "Synthetic Record"),
        "risk_profile": {
            "overall": record.get("overall", "Watch"),
            "fall_risk": record.get("risk_bucket", "attention"),
            "fall_probability_bucket": _bucket_percent(metrics.get("fall_probability")),
        },
        "model_results": [
            {
                "task": output.get("model"),
                "input": output.get("input_modality"),
                "status": output.get("status"),
                "score_bucket": (
                    _bucket_percent(output.get("score"))
                    if isinstance(output.get("score"), (int, float)) and 0 <= float(output.get("score")) <= 1
                    else _bucket_number(output.get("score"))
                ),
            }
            for output in record.get("model_outputs", [])
        ],
        "metrics": {
            "heart_rate": _metric_bucket("heart_rate", metrics.get("heart_rate"), metrics.get("heart_rate_status", "normal")),
            "respiratory_rate": _metric_bucket("respiratory_rate", metrics.get("respiratory_rate"), metrics.get("respiratory_rate_status", "normal")),
            "blood_pressure": _metric_bucket("blood_pressure", metrics.get("blood_pressure"), metrics.get("blood_pressure_status", "normal")),
            "sleep_efficiency": _metric_bucket("sleep_efficiency", metrics.get("sleep_efficiency"), metrics.get("sleep_efficiency_status", "normal")),
            "spo2": _metric_bucket("spo2", metrics.get("spo2"), metrics.get("spo2_status", "normal")),
            "activity_mix": "bucketed distribution",
        },
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
        f"{fall_risk.get('level', 'Moderate')} health-index risk profile."
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
    if not pool:
        raise ValueError("candidate pool cannot be empty")

    shuffled = list(pool)
    rng.shuffle(shuffled)
    visible_count = min(4, len(shuffled))
    selected_order_index = rng.randrange(visible_count)
    selected = copy.deepcopy(shuffled[selected_order_index])
    selected["_source_label"] = selected.get("label", "Candidate")
    selected["_shuffle_order_preview"] = [
        candidate.get("label", "Candidate") for candidate in shuffled[:visible_count]
    ]
    selected["_selected_order_index"] = selected_order_index
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
