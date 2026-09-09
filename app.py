import random
import datetime
from itertools import count

from flask import Flask, request, jsonify, Response

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

app = Flask(__name__)

MODES = {
    "car":       {"label": "Car (Petrol)",   "icon": "🚗", "color": "#334155", "ef": 192, "cost_km": 9.0,  "speed": 28, "overhead_min": 3, "max_km": None},
    "car_ev":    {"label": "Car (Electric)", "icon": "🔋", "color": "#0ea5a3", "ef": 53,  "cost_km": 3.2,  "speed": 28, "overhead_min": 3, "max_km": None},
    "motorbike": {"label": "Motorbike",      "icon": "🏍️", "color": "#f4a261", "ef": 103, "cost_km": 2.8,  "speed": 32, "overhead_min": 2, "max_km": None},
    "carpool":   {"label": "Carpool",        "icon": "🚙", "color": "#8ecae6", "ef": 96,  "cost_km": 4.5,  "speed": 28, "overhead_min": 5, "max_km": None},
    "rideshare": {"label": "Rideshare/Taxi", "icon": "🚕", "color": "#ffb703", "ef": 150, "cost_km": 14.0, "speed": 26, "overhead_min": 6, "max_km": None},
    "bus":       {"label": "Bus",            "icon": "🚌", "color": "#3a86ff", "ef": 82,  "cost_km": 1.5,  "speed": 18, "overhead_min": 9, "max_km": None},
    "metro":     {"label": "Metro/Train",    "icon": "🚇", "color": "#06d6a0", "ef": 41,  "cost_km": 2.0,  "speed": 34, "overhead_min": 7, "max_km": None},
    "bike":      {"label": "Bicycle",        "icon": "🚲", "color": "#2a9d8f", "ef": 0,   "cost_km": 0.0,  "speed": 15, "overhead_min": 1, "max_km": 14},
    "walk":      {"label": "Walking",        "icon": "🚶", "color": "#588157", "ef": 0,   "cost_km": 0.0,  "speed": 5,  "overhead_min": 0, "max_km": 4.5},
}

PURPOSES = ["Commute", "Work", "Errand", "Shopping", "Leisure", "Social", "Fitness", "Travel", "Other"]

CURRENCY = "₹"

KG_CO2_PER_LITRE_PETROL = 2.31     
KG_CO2_ABSORBED_PER_TREE_YEAR = 21  

DEFAULT_LIMITS = {
    "max_extra_time_min": 15,
    "max_extra_cost": 30,
    "min_co2_reduction_pct": 15,
}

_id_counter = count(1)


def next_id():
    return next(_id_counter)


def calc_co2_kg(mode: str, distance_km: float) -> float:
    return round(distance_km * MODES[mode]["ef"] / 1000.0, 3)


def calc_cost(mode: str, distance_km: float) -> float:
    return round(distance_km * MODES[mode]["cost_km"], 2)


def calc_time_min(mode: str, distance_km: float) -> float:
    m = MODES[mode]
    moving = (distance_km / m["speed"]) * 60.0
    return round(moving + m["overhead_min"], 1)


def is_realistic(mode: str, distance_km: float) -> bool:
    cap = MODES[mode]["max_km"]
    return cap is None or distance_km <= cap


TRIPS = []        
LIMITS = dict(DEFAULT_LIMITS)
BEHAVIOR_CHANGE_DATE = None 


def add_trip_record(date_str, origin, destination, purpose, mode,
                     distance_km, time_min=None, cost=None):
    distance_km = float(distance_km)
    if time_min is None:
        time_min = calc_time_min(mode, distance_km)
    if cost is None:
        cost = calc_cost(mode, distance_km)
    trip = {
        "id": next_id(),
        "date": date_str,
        "origin": origin,
        "destination": destination,
        "purpose": purpose,
        "mode": mode,
        "distance_km": round(float(distance_km), 2),
        "time_min": round(float(time_min), 1),
        "cost": round(float(cost), 2),
        "co2_kg": calc_co2_kg(mode, distance_km),
    }
    TRIPS.append(trip)
    return trip


def seed_demo_data():
    global BEHAVIOR_CHANGE_DATE
    rnd = random.Random(42)
    today = datetime.date.today()
    span_days = 70
    change_date = today - datetime.timedelta(days=33)
    BEHAVIOR_CHANGE_DATE = change_date.isoformat()

    for i in range(span_days, -1, -1):
        d = today - datetime.timedelta(days=i)
        weekday = d.weekday() 

        if weekday < 5:  
            base_dist = 9.4 + rnd.uniform(-0.6, 0.6)
            if d < change_date:
                mode = rnd.choices(["car", "motorbike"], weights=[80, 20])[0]
            else:
                mode = rnd.choices(
                    ["metro", "bus", "car", "carpool"],
                    weights=[48, 20, 20, 12],
                )[0]
            add_trip_record(d.isoformat(), "Home", "Office", "Commute", mode, base_dist)
            add_trip_record(d.isoformat(), "Office", "Home", "Commute", mode, base_dist + rnd.uniform(-0.3, 0.5))

        if weekday < 5 and rnd.random() < 0.18:
            dist = rnd.uniform(2, 6)
            mode = rnd.choices(["car", "bike", "walk", "motorbike"], weights=[45, 20, 15, 20])[0]
            add_trip_record(d.isoformat(), "Office", "Market", "Errand", mode, dist)
            add_trip_record(d.isoformat(), "Market", "Home", "Errand", mode, dist * 1.1)

       
        if weekday >= 5 and rnd.random() < 0.55:
            purpose = rnd.choice(["Leisure", "Social", "Shopping", "Fitness"])
            dist = rnd.uniform(3, 16)
            mode = rnd.choices(
                ["car", "rideshare", "bike", "walk", "metro", "carpool"],
                weights=[30, 20, 15, 10, 15, 10],
            )[0]
            add_trip_record(d.isoformat(), "Home", purpose + " spot", purpose, mode, dist)
            add_trip_record(d.isoformat(), purpose + " spot", "Home", purpose, mode, dist * 1.05)

    for i, days_ago in enumerate([61, 40, 19, 6]):
        d = today - datetime.timedelta(days=days_ago)
        dist = rnd.uniform(70, 160)
        mode = rnd.choice(["car", "rideshare"])
        add_trip_record(d.isoformat(), "Home", "Out-of-town", "Travel", mode, dist)

    TRIPS.sort(key=lambda t: t["date"])


seed_demo_data()

def week_span(trips):
    if not trips:
        return 1.0
    dates = [datetime.date.fromisoformat(t["date"]) for t in trips]
    span = (max(dates) - min(dates)).days
    return max(span / 7.0, 1.0)


def compute_summary():
    trips = TRIPS
    total_co2 = round(sum(t["co2_kg"] for t in trips), 2)
    total_distance = round(sum(t["distance_km"] for t in trips), 1)
    total_cost = round(sum(t["cost"] for t in trips), 2)
    total_time = round(sum(t["time_min"] for t in trips), 1)

    monthly = {}
    for t in trips:
        mk = t["date"][:7]
        monthly.setdefault(mk, {"co2_kg": 0.0, "distance_km": 0.0, "cost": 0.0, "trips": 0})
        monthly[mk]["co2_kg"] += t["co2_kg"]
        monthly[mk]["distance_km"] += t["distance_km"]
        monthly[mk]["cost"] += t["cost"]
        monthly[mk]["trips"] += 1
    monthly_trend = [
        {"month": mk, **{k: round(v, 2) if isinstance(v, float) else v for k, v in vals.items()}}
        for mk, vals in sorted(monthly.items())
    ]

    by_mode = {}
    for t in trips:
        by_mode.setdefault(t["mode"], {"co2_kg": 0.0, "trips": 0, "distance_km": 0.0})
        by_mode[t["mode"]]["co2_kg"] += t["co2_kg"]
        by_mode[t["mode"]]["trips"] += 1
        by_mode[t["mode"]]["distance_km"] += t["distance_km"]
    by_mode_out = [
        {"mode": m, "label": MODES[m]["label"], "icon": MODES[m]["icon"], "color": MODES[m]["color"],
         "co2_kg": round(v["co2_kg"], 2), "trips": v["trips"], "distance_km": round(v["distance_km"], 1)}
        for m, v in sorted(by_mode.items(), key=lambda kv: -kv[1]["co2_kg"])
    ]

    by_purpose = {}
    for t in trips:
        by_purpose.setdefault(t["purpose"], {"co2_kg": 0.0, "trips": 0})
        by_purpose[t["purpose"]]["co2_kg"] += t["co2_kg"]
        by_purpose[t["purpose"]]["trips"] += 1
    by_purpose_out = [
        {"purpose": p, "co2_kg": round(v["co2_kg"], 2), "trips": v["trips"]}
        for p, v in sorted(by_purpose.items(), key=lambda kv: -kv[1]["co2_kg"])
    ]

    high_carbon = sorted(trips, key=lambda t: -t["co2_kg"])[:6]

    return {
        "total_co2_kg": total_co2,
        "total_distance_km": total_distance,
        "total_cost": total_cost,
        "total_time_min": total_time,
        "trip_count": len(trips),
        "monthly_trend": monthly_trend,
        "by_mode": by_mode_out,
        "by_purpose": by_purpose_out,
        "high_carbon_trips": high_carbon,
    }


def compute_patterns():
    """Group recurring journeys so recommendations act on habits, not one-off trips."""
    groups = {}
    for t in TRIPS:
        key = (t["origin"], t["destination"], t["purpose"])
        groups.setdefault(key, []).append(t)

    weeks = week_span(TRIPS)
    patterns = []
    for (origin, dest, purpose), trips in groups.items():
        modes = {}
        for t in trips:
            modes[t["mode"]] = modes.get(t["mode"], 0) + 1
        dominant_mode = max(modes, key=modes.get)
        avg_distance = sum(t["distance_km"] for t in trips) / len(trips)
        avg_time = sum(t["time_min"] for t in trips) / len(trips)
        avg_cost = sum(t["cost"] for t in trips) / len(trips)
        total_co2 = sum(t["co2_kg"] for t in trips)
        weekly_freq = len(trips) / weeks
        patterns.append({
            "key": f"{origin}→{dest} ({purpose})",
            "origin": origin,
            "destination": dest,
            "purpose": purpose,
            "trip_count": len(trips),
            "weekly_frequency": round(weekly_freq, 2),
            "dominant_mode": dominant_mode,
            "mode_counts": modes,
            "avg_distance_km": round(avg_distance, 2),
            "avg_time_min": round(avg_time, 1),
            "avg_cost": round(avg_cost, 2),
            "total_co2_kg": round(total_co2, 2),
        })
    patterns.sort(key=lambda p: -p["total_co2_kg"])
    return patterns


def compare_for(mode, distance_km, time_min, cost):
    """Return every realistic alternative mode compared against a reference journey."""
    options = []
    for alt_mode, meta in MODES.items():
        if alt_mode == mode:
            continue
        if not is_realistic(alt_mode, distance_km):
            continue
        alt_co2 = calc_co2_kg(alt_mode, distance_km)
        alt_cost = calc_cost(alt_mode, distance_km)
        alt_time = calc_time_min(alt_mode, distance_km)
        base_co2 = calc_co2_kg(mode, distance_km)
        co2_reduction = round(base_co2 - alt_co2, 3)
        co2_reduction_pct = round((co2_reduction / base_co2 * 100), 1) if base_co2 > 0 else (100.0 if co2_reduction > 0 else 0.0)
        options.append({
            "mode": alt_mode,
            "label": meta["label"],
            "icon": meta["icon"],
            "color": meta["color"],
            "co2_kg": alt_co2,
            "cost": alt_cost,
            "time_min": alt_time,
            "extra_time_min": round(alt_time - time_min, 1),
            "extra_cost": round(alt_cost - cost, 2),
            "co2_reduction_kg": co2_reduction,
            "co2_reduction_pct": co2_reduction_pct,
            "money_saved": round(cost - alt_cost, 2),
        })
    options.sort(key=lambda o: -o["co2_reduction_kg"])
    return options


def qualifies(option, limits):
    return (
        option["extra_time_min"] <= limits["max_extra_time_min"]
        and option["extra_cost"] <= limits["max_extra_cost"]
        and option["co2_reduction_pct"] >= limits["min_co2_reduction_pct"]
    )


def build_recommendations(limits):
    """Best Realistic Change + Minimum Change, Maximum Impact, computed over habits."""
    patterns = compute_patterns()
    candidates = []
    for p in patterns:
        options = compare_for(p["dominant_mode"], p["avg_distance_km"], p["avg_time_min"], p["avg_cost"])
        for opt in options:
            qualifying = qualifies(opt, limits)
            weekly_co2_saved = round(opt["co2_reduction_kg"] * p["weekly_frequency"], 2)
            weekly_money_saved = round(opt["money_saved"] * p["weekly_frequency"], 2)
            candidates.append({
                "pattern": p,
                "from_mode": p["dominant_mode"],
                "option": opt,
                "qualifying": qualifying,
                "weekly_co2_saved_kg": weekly_co2_saved,
                "weekly_money_saved": weekly_money_saved,
                "monthly_co2_saved_kg": round(weekly_co2_saved * 4.345, 2),
                "yearly_co2_saved_kg": round(weekly_co2_saved * 52, 2),
                "monthly_money_saved": round(weekly_money_saved * 4.345, 2),
                "yearly_money_saved": round(weekly_money_saved * 52, 2),
            })

    qualifying_candidates = [c for c in candidates if c["qualifying"] and c["weekly_co2_saved_kg"] > 0]

    best_realistic = None
    if qualifying_candidates:
        best_realistic = max(qualifying_candidates, key=lambda c: c["weekly_co2_saved_kg"])
        reasons = []
        reasons.append(
            f"Cuts {best_realistic['option']['co2_reduction_pct']}% of CO2 on this journey "
            f"({best_realistic['weekly_co2_saved_kg']} kg saved every week)."
        )
        if best_realistic["option"]["extra_time_min"] <= 0:
            reasons.append("It's actually the same speed or faster than your current mode.")
        else:
            reasons.append(
                f"Only +{best_realistic['option']['extra_time_min']} min extra travel time — "
                f"within your {limits['max_extra_time_min']}-min comfort zone."
            )
        if best_realistic["option"]["extra_cost"] <= 0:
            reasons.append(f"It also costs {CURRENCY}{abs(best_realistic['option']['extra_cost'])} less per trip.")
        else:
            reasons.append(
                f"Extra cost is just {CURRENCY}{best_realistic['option']['extra_cost']} per trip — "
                f"within your {CURRENCY}{limits['max_extra_cost']} limit."
            )
        reasons.append(f"You already make this trip ~{best_realistic['pattern']['weekly_frequency']}x/week, so the impact compounds fast.")
        best_realistic["reasons"] = reasons
   
 minimum_change = None
    if qualifying_candidates:
        minimum_change = min(
            qualifying_candidates,
            key=lambda c: (c["option"]["extra_time_min"], c["option"]["extra_cost"], -c["weekly_co2_saved_kg"]),
        )

    return {
        "best_realistic_change": best_realistic,
        "minimum_change_maximum_impact": minimum_change,
        "all_candidates_considered": len(candidates),
        "qualifying_count": len(qualifying_candidates),
    }


def compute_whatif(counts_per_week, avg_distance_km):
    """counts_per_week: {mode: trips_per_week}. Returns weekly/monthly/yearly projection."""
    weekly_co2 = 0.0
    weekly_cost = 0.0
    weekly_time = 0.0
    weekly_distance = 0.0
    for mode, n in counts_per_week.items():
        if mode not in MODES or n <= 0:
            continue
        weekly_co2 += calc_co2_kg(mode, avg_distance_km) * n
        weekly_cost += calc_cost(mode, avg_distance_km) * n
        weekly_time += calc_time_min(mode, avg_distance_km) * n
        weekly_distance += avg_distance_km * n

    return {
        "weekly_co2_kg": round(weekly_co2, 2),
        "weekly_cost": round(weekly_cost, 2),
        "weekly_time_min": round(weekly_time, 1),
        "weekly_distance_km": round(weekly_distance, 1),
        "monthly_co2_kg": round(weekly_co2 * 4.345, 2),
        "monthly_cost": round(weekly_cost * 4.345, 2),
        "monthly_time_min": round(weekly_time * 4.345, 1),
        "yearly_co2_kg": round(weekly_co2 * 52, 2),
        "yearly_cost": round(weekly_cost * 52, 2),
        "yearly_time_min": round(weekly_time * 52, 1),
    }


def current_weekly_baseline():
    """Derive the user's actual current weekly averages, for What-If comparison."""
    weeks = week_span(TRIPS)
    return {
        "weekly_co2_kg": round(sum(t["co2_kg"] for t in TRIPS) / weeks, 2),
        "weekly_cost": round(sum(t["cost"] for t in TRIPS) / weeks, 2),
        "weekly_time_min": round(sum(t["time_min"] for t in TRIPS) / weeks, 1),
        "avg_distance_km": round(sum(t["distance_km"] for t in TRIPS) / max(len(TRIPS), 1), 2),
        "mode_counts_per_week": _mode_counts_per_week(),
    }


def _mode_counts_per_week():
    weeks = week_span(TRIPS)
    counts = {}
    for t in TRIPS:
        counts[t["mode"]] = counts.get(t["mode"], 0) + 1
    return {m: round(c / weeks, 2) for m, c in counts.items()}


def compute_progress(change_date_str):
    change_date = datetime.date.fromisoformat(change_date_str)
    before = [t for t in TRIPS if datetime.date.fromisoformat(t["date"]) < change_date]
    after = [t for t in TRIPS if datetime.date.fromisoformat(t["date"]) >= change_date]

    def stats(trips):
        weeks = week_span(trips) if trips else 1.0
        car_like = sum(1 for t in trips if t["mode"] in ("car", "rideshare", "motorbike"))
        return {
            "weekly_co2_kg": round(sum(t["co2_kg"] for t in trips) / weeks, 2) if trips else 0.0,
            "weekly_cost": round(sum(t["cost"] for t in trips) / weeks, 2) if trips else 0.0,
            "car_trip_share_pct": round(car_like / len(trips) * 100, 1) if trips else 0.0,
            "trip_count": len(trips),
        }

    b, a = stats(before), stats(after)
    co2_avoided_weekly = round(b["weekly_co2_kg"] - a["weekly_co2_kg"], 2)
    money_saved_weekly = round(b["weekly_cost"] - a["weekly_cost"], 2)
    pct_improvement = round((co2_avoided_weekly / b["weekly_co2_kg"] * 100), 1) if b["weekly_co2_kg"] > 0 else 0.0

    return {
        "change_date": change_date_str,
        "before": b,
        "after": a,
        "co2_avoided_weekly_kg": co2_avoided_weekly,
        "co2_avoided_monthly_kg": round(co2_avoided_weekly * 4.345, 2),
        "money_saved_weekly": money_saved_weekly,
        "money_saved_monthly": round(money_saved_weekly * 4.345, 2),
        "car_share_change_pct": round(a["car_trip_share_pct"] - b["car_trip_share_pct"], 1),
        "pct_improvement": pct_improvement,
    }


def compute_alerts():
    alerts = []
    today = datetime.date.fromisoformat(TRIPS[-1]["date"]) if TRIPS else datetime.date.today()

 
    last7 = [t for t in TRIPS if (today - datetime.date.fromisoformat(t["date"])).days < 7]
    prior_weeks = [t for t in TRIPS if 7 <= (today - datetime.date.fromisoformat(t["date"])).days < 35]
    last7_co2 = sum(t["co2_kg"] for t in last7)
    prior_avg_weekly = sum(t["co2_kg"] for t in prior_weeks) / 4 if prior_weeks else 0
    if prior_avg_weekly > 0 and last7_co2 > prior_avg_weekly * 1.25:
        top_trip = max(last7, key=lambda t: t["co2_kg"]) if last7 else None
        alerts.append({
            "type": "carbon_spike",
            "icon": "📈",
            "severity": "warning",
            "title": "Carbon Spike",
            "detect": f"This week's footprint is {last7_co2:.1f} kg CO2 — about {(last7_co2/prior_avg_weekly-1)*100:.0f}% above your recent weekly average of {prior_avg_weekly:.1f} kg.",
            "explain": (f"The biggest contributor was your {top_trip['origin']}→{top_trip['destination']} "
                        f"{top_trip['mode']} trip on {top_trip['date']} ({top_trip['co2_kg']} kg)."
                        if top_trip else "A few longer trips pushed the weekly total up."),
            "suggest": "No need to overhaul everything — just check Compare Options for that one journey next time.",
        })


    last30 = [t for t in TRIPS if (today - datetime.date.fromisoformat(t["date"])).days < 30]
    prev30 = [t for t in TRIPS if 30 <= (today - datetime.date.fromisoformat(t["date"])).days < 60]

    def car_share(trips):
        if not trips:
            return None
        car_n = sum(1 for t in trips if t["mode"] in ("car", "rideshare", "motorbike"))
        return car_n / len(trips) * 100

    cs_now, cs_prev = car_share(last30), car_share(prev30)
    if cs_now is not None and cs_prev is not None:
        delta = cs_now - cs_prev
        if delta <= -8:
            alerts.append({
                "type": "habit_change",
                "icon": "🌱",
                "severity": "positive",
                "title": "Habit Change — Great Progress",
                "detect": f"Your car/rideshare/motorbike share of trips dropped from {cs_prev:.0f}% to {cs_now:.0f}% over the last 30 days.",
                "explain": "You're consistently choosing lower-carbon options more often than before.",
                "suggest": "Keep it up — check Track My Progress to see exactly how much CO2 and money that's saving.",
            })
        elif delta >= 8:
            alerts.append({
                "type": "habit_change",
                "icon": "🔄",
                "severity": "info",
                "title": "Habit Change Detected",
                "detect": f"Car/rideshare/motorbike share of trips rose from {cs_prev:.0f}% to {cs_now:.0f}% over the last 30 days.",
                "explain": "This might be due to weather, schedule changes, or a shift in routine — totally normal.",
                "suggest": "When you're ready, Best Realistic Change can point to the easiest single swap to bring it back down.",
            })

    patterns = compute_patterns()
    limits = LIMITS
    opportunity = None
    for p in patterns:
        if p["dominant_mode"] in ("bike", "walk", "metro"):
            continue
        options = compare_for(p["dominant_mode"], p["avg_distance_km"], p["avg_time_min"], p["avg_cost"])
        qualifying_opts = [o for o in options if qualifies(o, limits)]
        if qualifying_opts:
            opportunity = (p, qualifying_opts[0])
            break
    if opportunity:
        p, opt = opportunity
        alerts.append({
            "type": "opportunity",
            "icon": "💡",
            "severity": "info",
            "title": "Opportunity Alert",
            "detect": f"Your {p['key']} trip ({p['weekly_frequency']}x/week by {MODES[p['dominant_mode']]['label']}) has an unused greener option.",
            "explain": f"Switching to {MODES[opt['mode']]['label']} would cut {opt['co2_reduction_pct']}% CO2 for just +{max(opt['extra_time_min'],0)} min — inside your own limits.",
            "suggest": "See it in full detail under Best Realistic Change.",
        })

    return alerts


def compute_contribution():
    green_modes = ("bike", "walk", "bus", "metro", "carpool", "car_ev")
    green_trips = [t for t in TRIPS if t["mode"] in green_modes]
    avoided_co2 = 0.0
    avoided_km_driven = 0.0
    for t in green_trips:
        counterfactual_co2 = calc_co2_kg("car", t["distance_km"])
        avoided_co2 += max(counterfactual_co2 - t["co2_kg"], 0)
        avoided_km_driven += t["distance_km"]

    fuel_saved_l = avoided_co2 / KG_CO2_PER_LITRE_PETROL
    trees_equivalent = avoided_co2 / KG_CO2_ABSORBED_PER_TREE_YEAR

    return {
        "co2_avoided_kg": round(avoided_co2, 1),
        "fuel_saved_litres": round(fuel_saved_l, 1),
        "vehicle_trips_avoided": len(green_trips),
        "vehicle_km_reduced": round(avoided_km_driven, 1),
        "trees_equivalent_per_year": round(trees_equivalent, 1),
        "note": "These are estimated indicators based on your own travel behavior "
                "(compared with a same-distance car trip) — not direct measurements "
                "of local air quality or traffic.",
    }


def build_ai_context():
    summary = compute_summary()
    recs = build_recommendations(LIMITS)
    lines = [
        f"Total logged CO2: {summary['total_co2_kg']} kg over {summary['trip_count']} trips.",
        f"User's Acceptable Change Zone: max +{LIMITS['max_extra_time_min']} min extra time, "
        f"max +{CURRENCY}{LIMITS['max_extra_cost']} extra cost, min {LIMITS['min_co2_reduction_pct']}% CO2 reduction required.",
    ]
    if recs["best_realistic_change"]:
        b = recs["best_realistic_change"]
        lines.append(
            f"Current top recommendation (Best Realistic Change): switch '{b['pattern']['key']}' "
            f"from {b['from_mode']} to {b['option']['mode']}, saving {b['weekly_co2_saved_kg']} kg CO2/week "
            f"for +{b['option']['extra_time_min']} min and {CURRENCY}{b['option']['extra_cost']} extra cost."
        )
    top_modes = ", ".join(f"{m['label']} ({m['co2_kg']}kg)" for m in summary["by_mode"][:3])
    lines.append(f"Top CO2 contributors by mode: {top_modes}.")
    return "\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """You are the "AI Travel Coach" inside Personal Travel Carbon Intelligence, a \
premium personal analytics app. Your philosophy: small realistic changes lead \
to meaningful carbon reduction and lasting behavior change. NEVER shame the \
user, never tell them to completely give up their car, and never demand \
drastic lifestyle changes. Always ground advice in the smallest realistic \
change with the biggest benefit, respecting the user's own stated limits for \
extra time and cost. Be warm, concise, and specific — use the real numbers \
given below when relevant.

Here is the user's current travel & carbon context:
{context}
"""


@app.route("/api/chat", methods=["POST"])
def api_chat():
    if requests is None:
        return jsonify({"error": "The 'requests' package is not installed on the server."}), 500

    data = request.get_json(force=True) or {}
    api_key = (data.get("api_key") or "").strip()
    message = (data.get("message") or "").strip()
    model = data.get("model") or "openai/gpt-4o-mini"
    history = data.get("history") or []

    if not api_key:
        return jsonify({"error": "Please add your OpenRouter API key in the chat settings (⚙) first."}), 400
    if not message:
        return jsonify({"error": "Message was empty."}), 400

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=build_ai_context())
    messages = [{"role": "system", "content": system_prompt}]
    for h in history[-8:]:
        if h.get("role") in ("user", "assistant") and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost",
                "X-Title": "Personal Travel Carbon Intelligence",
            },
            json={"model": model, "messages": messages, "max_tokens": 700},
            timeout=45,
        )
    except Exception as e:  
        return jsonify({"error": f"Could not reach OpenRouter: {e}"}), 502

    if resp.status_code != 200:
        try:
            err = resp.json()
            err_msg = err.get("error", {}).get("message", resp.text)
        except Exception:
            err_msg = resp.text
        return jsonify({"error": f"OpenRouter error ({resp.status_code}): {err_msg}"}), 502

    payload = resp.json()
    try:
        reply = payload["choices"][0]["message"]["content"]
    except Exception:
        return jsonify({"error": "Unexpected response from OpenRouter."}), 502

    return jsonify({"reply": reply})



@app.route("/api/modes")
def api_modes():
    return jsonify({"modes": MODES, "purposes": PURPOSES, "currency": CURRENCY})


@app.route("/api/trips", methods=["GET", "POST"])
def api_trips():
    if request.method == "POST":
        d = request.get_json(force=True)
        try:
            trip = add_trip_record(
                d["date"], d["origin"], d["destination"], d["purpose"], d["mode"],
                d["distance_km"], d.get("time_min"), d.get("cost"),
            )
        except (KeyError, ValueError) as e:
            return jsonify({"error": f"Invalid trip data: {e}"}), 400
        TRIPS.sort(key=lambda t: t["date"])
        return jsonify(trip), 201
    return jsonify(sorted(TRIPS, key=lambda t: t["date"], reverse=True))


@app.route("/api/trips/<int:trip_id>", methods=["DELETE"])
def api_delete_trip(trip_id):
    global TRIPS
    before = len(TRIPS)
    TRIPS = [t for t in TRIPS if t["id"] != trip_id]
    if len(TRIPS) == before:
        return jsonify({"error": "Trip not found"}), 404
    return jsonify({"deleted": trip_id})


@app.route("/api/summary")
def api_summary():
    return jsonify(compute_summary())


@app.route("/api/patterns")
def api_patterns():
    return jsonify(compute_patterns())


@app.route("/api/compare/<int:trip_id>")
def api_compare(trip_id):
    trip = next((t for t in TRIPS if t["id"] == trip_id), None)
    if not trip:
        return jsonify({"error": "Trip not found"}), 404
    options = compare_for(trip["mode"], trip["distance_km"], trip["time_min"], trip["cost"])
    for o in options:
        o["qualifying"] = qualifies(o, LIMITS)
    return jsonify({"trip": trip, "options": options, "limits": LIMITS})


@app.route("/api/limits", methods=["GET", "POST"])
def api_limits():
    global LIMITS
    if request.method == "POST":
        d = request.get_json(force=True) or {}
        for k in ("max_extra_time_min", "max_extra_cost", "min_co2_reduction_pct"):
            if k in d:
                LIMITS[k] = float(d[k])
        return jsonify(LIMITS)
    return jsonify(LIMITS)


@app.route("/api/recommendation")
def api_recommendation():
    return jsonify(build_recommendations(LIMITS))


@app.route("/api/whatif", methods=["POST"])
def api_whatif():
    d = request.get_json(force=True) or {}
    counts = d.get("counts_per_week", {})
    avg_distance = float(d.get("avg_distance_km") or current_weekly_baseline()["avg_distance_km"])
    projection = compute_whatif(counts, avg_distance)
    baseline = current_weekly_baseline()
    projection["baseline"] = baseline
    projection["co2_saved_weekly_kg"] = round(baseline["weekly_co2_kg"] - projection["weekly_co2_kg"], 2)
    projection["co2_saved_monthly_kg"] = round(projection["co2_saved_weekly_kg"] * 4.345, 2)
    projection["co2_saved_yearly_kg"] = round(projection["co2_saved_weekly_kg"] * 52, 2)
    projection["money_saved_weekly"] = round(baseline["weekly_cost"] - projection["weekly_cost"], 2)
    projection["money_saved_yearly"] = round(projection["money_saved_weekly"] * 52, 2)
    projection["extra_time_weekly_min"] = round(projection["weekly_time_min"] - baseline["weekly_time_min"], 1)
    return jsonify(projection)


@app.route("/api/progress", methods=["GET"])
def api_progress():
    change_date = request.args.get("change_date") or BEHAVIOR_CHANGE_DATE
    return jsonify(compute_progress(change_date))


@app.route("/api/alerts")
def api_alerts():
    return jsonify(compute_alerts())


@app.route("/api/contribution")
def api_contribution():
    return jsonify(compute_contribution())


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Personal Travel Carbon Intelligence</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Manrope:wght@600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root{
  --bg:#f5f7fa; --card:#ffffff; --navy:#0b1f3a; --navy-soft:#3d4f6b;
  --teal:#0ea5a3; --teal-deep:#0b8280; --green:#22c55e; --amber:#f59e0b; --red:#ef4444;
  --border:#e6ebf1; --shadow:0 10px 30px rgba(11,31,58,0.07), 0 2px 8px rgba(11,31,58,0.04);
  --radius:18px; --radius-sm:12px;
}
*{box-sizing:border-box;}
html,body{margin:0;padding:0;}
body{
  font-family:'Inter',system-ui,sans-serif; background:var(--bg); color:var(--navy);
  -webkit-font-smoothing:antialiased;
}
h1,h2,h3,.brand{font-family:'Manrope',system-ui,sans-serif;}
a{text-decoration:none;color:inherit;}
button{font-family:inherit;cursor:pointer;}

/* ---------- layout ---------- */
.app{display:flex;min-height:100vh;}
.sidebar{
  width:264px; flex-shrink:0; background:linear-gradient(180deg,#0b1f3a,#122a4d);
  color:#e7edf6; padding:26px 18px; position:sticky; top:0; height:100vh; overflow-y:auto;
}
.brand{display:flex; align-items:center; gap:10px; font-weight:800; font-size:19px; padding:0 6px 22px;}
.brand span.mark{font-size:24px;}
.brand small{display:block; font-weight:500; font-size:11px; color:#9fb3cf; letter-spacing:.4px;}
.nav-group{margin-top:10px;}
.nav-item{
  display:flex; align-items:center; gap:11px; padding:11px 14px; border-radius:12px;
  font-size:14.5px; font-weight:600; color:#c7d4e6; margin-bottom:4px; transition:.15s;
}
.nav-item .num{
  width:22px;height:22px;border-radius:7px;background:rgba(255,255,255,.08);
  display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#8fa6c7;flex-shrink:0;
}
.nav-item:hover{background:rgba(255,255,255,.06); color:#fff;}
.nav-item.active{background:linear-gradient(90deg,#0ea5a3,#0b8280); color:#fff; box-shadow:0 6px 16px rgba(14,165,163,.35);}
.nav-item.active .num{background:rgba(255,255,255,.25); color:#fff;}
.sidebar-foot{margin-top:22px; padding:14px; border-radius:14px; background:rgba(255,255,255,.06); font-size:12px; color:#9fb3cf; line-height:1.5;}

.main{flex:1; min-width:0; padding:28px 34px 80px;}
.topbar{display:flex; justify-content:space-between; align-items:flex-start; gap:20px; margin-bottom:26px; flex-wrap:wrap;}
.topbar h1{margin:0; font-size:25px; font-weight:800;}
.topbar p{margin:4px 0 0; color:var(--navy-soft); font-size:14px;}
.btn{
  border:none; border-radius:12px; padding:11px 18px; font-weight:700; font-size:13.5px;
  display:inline-flex; align-items:center; gap:8px; transition:.15s;
}
.btn-primary{background:linear-gradient(90deg,#0ea5a3,#0b8280); color:#fff; box-shadow:0 8px 18px rgba(14,165,163,.3);}
.btn-primary:hover{transform:translateY(-1px); box-shadow:0 10px 22px rgba(14,165,163,.4);}
.btn-ghost{background:#fff; color:var(--navy); border:1px solid var(--border);}
.btn-ghost:hover{border-color:var(--teal); color:var(--teal-deep);}
.btn-sm{padding:7px 12px; font-size:12.5px; border-radius:9px;}

.section{display:none;}
.section.active{display:block; animation:fade .25s ease;}
@keyframes fade{from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;}}

.grid{display:grid; gap:18px;}
.grid-4{grid-template-columns:repeat(4,1fr);}
.grid-3{grid-template-columns:repeat(3,1fr);}
.grid-2{grid-template-columns:repeat(2,1fr);}
@media(max-width:1100px){.grid-4{grid-template-columns:repeat(2,1fr);} .grid-3{grid-template-columns:repeat(2,1fr);}}
@media(max-width:720px){.grid-4,.grid-3,.grid-2{grid-template-columns:1fr;} .app{flex-direction:column;} .sidebar{width:100%; height:auto; position:relative;}}

.card{
  background:var(--card); border-radius:var(--radius); padding:20px 22px; box-shadow:var(--shadow);
  border:1px solid var(--border);
}
.card h3{margin:0 0 4px; font-size:14px; color:var(--navy-soft); font-weight:600;}
.stat-value{font-size:26px; font-weight:800; margin:2px 0 2px; font-family:'Manrope',sans-serif;}
.stat-sub{font-size:12.5px; color:#7c8aa0;}
.stat-icon{width:38px;height:38px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:18px;margin-bottom:10px;}

.section-title{display:flex; align-items:center; gap:10px; margin:34px 0 14px;}
.section-title h2{margin:0; font-size:18px; font-weight:800;}
.section-title .pill{background:#e8f7f6; color:var(--teal-deep); font-size:11px; font-weight:700; padding:4px 10px; border-radius:99px;}

.chart-card{background:var(--card); border-radius:var(--radius); padding:20px 22px; box-shadow:var(--shadow); border:1px solid var(--border);}
.chart-card h3{margin:0 0 14px; font-size:14.5px; font-weight:700; color:var(--navy);}
canvas{max-height:280px;}

table{width:100%; border-collapse:collapse; font-size:13.5px;}
th{text-align:left; color:#7c8aa0; font-weight:600; padding:9px 10px; border-bottom:1px solid var(--border); font-size:12px; text-transform:uppercase; letter-spacing:.3px;}
td{padding:11px 10px; border-bottom:1px solid #f0f3f7;}
tr:last-child td{border-bottom:none;}
.tag{display:inline-flex; align-items:center; gap:5px; background:#f1f5f9; padding:3px 9px; border-radius:99px; font-size:12px; font-weight:600;}

.badge-ok{background:#e7f9ee; color:#15803d;}
.badge-no{background:#fdeceb; color:#b91c1c;}

/* Trip form modal */
.modal-backdrop{position:fixed; inset:0; background:rgba(11,20,38,.45); display:none; align-items:center; justify-content:center; z-index:60; backdrop-filter:blur(2px);}
.modal-backdrop.show{display:flex;}
.modal{background:#fff; border-radius:20px; width:min(560px,92vw); padding:26px 26px 22px; box-shadow:0 30px 60px rgba(0,0,0,.25); max-height:88vh; overflow-y:auto;}
.modal h3{margin:0 0 16px; font-size:18px;}
.field{margin-bottom:13px;}
.field label{display:block; font-size:12.5px; font-weight:700; color:var(--navy-soft); margin-bottom:5px;}
.field input, .field select{
  width:100%; padding:10px 12px; border-radius:10px; border:1.5px solid var(--border);
  font-size:16px; font-family:inherit; background:#fbfcfe; min-height:44px; -webkit-appearance:none; appearance:none;
}
.field select{
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='6'><path d='M0 0l5 6 5-6z' fill='%233d4f6b'/></svg>");
  background-repeat:no-repeat; background-position:right 14px center; padding-right:32px;
}
.field input:focus, .field select:focus{outline:none; border-color:var(--teal);}
.field.invalid input, .field.invalid select{border-color:#ef4444; background:#fff6f6;}
.row2{display:grid; grid-template-columns:1fr 1fr; gap:12px;}
.modal-actions{display:flex; justify-content:flex-end; gap:10px; margin-top:18px;}
@media(max-width:480px){.row2{grid-template-columns:1fr;}}

/* Compare */
.compare-select{margin-bottom:18px;}
.compare-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px;}
.opt-card{border:1.5px solid var(--border); border-radius:16px; padding:16px; position:relative; transition:.15s; background:#fff;}
.opt-card.qualifies{border-color:#bfe9c9; background:linear-gradient(180deg,#f4fdf6,#ffffff);}
.opt-card .mode-row{display:flex; align-items:center; gap:9px; margin-bottom:10px;}
.opt-card .mode-icon{font-size:22px;}
.opt-card .mode-name{font-weight:700; font-size:14.5px;}
.opt-card .metric{display:flex; justify-content:space-between; font-size:12.5px; padding:4px 0; color:var(--navy-soft);}
.opt-card .metric b{color:var(--navy);}
.status-chip{position:absolute; top:14px; right:14px; font-size:10.5px; font-weight:700; padding:3px 8px; border-radius:99px;}

/* Limits */
.limit-card{padding:22px;}
.limit-card label{font-weight:700; font-size:13.5px; display:flex; justify-content:space-between;}
.limit-card input[type=range]{width:100%; margin-top:10px; accent-color:#0ea5a3;}
.limit-value{color:var(--teal-deep); font-weight:800;}

/* Recommendation hero */
.hero-rec{
  background:linear-gradient(135deg,#0b1f3a,#123258 55%,#0b8280); color:#fff; border-radius:24px;
  padding:32px 34px; position:relative; overflow:hidden; box-shadow:0 20px 44px rgba(11,31,58,.3);
}
.hero-rec::after{content:""; position:absolute; right:-60px; top:-60px; width:220px; height:220px; border-radius:50%; background:radial-gradient(circle,rgba(14,165,163,.35),transparent 70%);}
.hero-rec .trophy{font-size:15px; font-weight:800; letter-spacing:.4px; background:rgba(255,255,255,.14); display:inline-flex; padding:6px 14px; border-radius:99px; margin-bottom:16px;}
.hero-rec h2{margin:0 0 8px; font-size:26px; font-weight:800;}
.hero-rec .sub{color:#cfe3f4; font-size:14.5px; margin-bottom:22px; max-width:560px;}
.hero-stats{display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:20px;}
.hero-stat{background:rgba(255,255,255,.08); border-radius:14px; padding:14px 16px;}
.hero-stat .lbl{font-size:11.5px; color:#bcd4ea; text-transform:uppercase; letter-spacing:.4px;}
.hero-stat .val{font-size:21px; font-weight:800; margin-top:3px;}
.hero-reasons{background:rgba(255,255,255,.08); border-radius:14px; padding:16px 18px; font-size:13.5px; line-height:1.7;}
.hero-reasons b{color:#8dfff2;}
@media(max-width:900px){.hero-stats{grid-template-columns:repeat(2,1fr);}}

.mini-rec{background:#fff; border:1.5px solid var(--border); border-radius:18px; padding:22px; margin-top:16px;}
.mini-rec h3{margin:0 0 4px; font-size:15px;}
.mini-rec .flow{display:flex; align-items:center; gap:10px; font-size:15px; font-weight:700; margin:10px 0;}
.mini-rec .arrow{color:var(--teal);}

/* What if lab */
.slider-row{display:flex; align-items:center; gap:14px; margin-bottom:16px;}
.slider-row .mlabel{width:150px; font-weight:700; font-size:13.5px; display:flex; align-items:center; gap:8px;}
.slider-row input[type=range]{flex:1; accent-color:#0ea5a3;}
.slider-row .count{width:34px; text-align:center; font-weight:800; color:var(--teal-deep);}

/* alerts */
.alert{display:flex; gap:14px; padding:16px 18px; border-radius:16px; border:1.5px solid var(--border); margin-bottom:12px; background:#fff;}
.alert .icon{font-size:22px;}
.alert.warning{border-color:#fde3c0; background:#fffaf1;}
.alert.positive{border-color:#bfe9c9; background:#f5fdf7;}
.alert.info{border-color:#c8e3ff; background:#f3f9ff;}
.alert h4{margin:0 0 4px; font-size:14px;}
.alert p{margin:2px 0; font-size:13px; color:var(--navy-soft); line-height:1.5;}
.alert p b{color:var(--navy);}

.empty{color:#8fa0b8; font-size:13.5px; padding:14px 0;}

/* contribution */
.contrib-card{text-align:center; padding:26px 18px;}
.contrib-card .big{font-size:30px; font-weight:800; font-family:'Manrope',sans-serif; color:var(--teal-deep);}
.contrib-card .lbl{font-size:12.5px; color:var(--navy-soft); margin-top:6px; font-weight:600;}
.contrib-note{background:#fff8e6; border:1px solid #ffe8ad; border-radius:14px; padding:14px 18px; font-size:12.5px; color:#8a6d1c; margin-top:16px; line-height:1.6;}

/* chat widget */
.chat-fab{
  position:fixed; bottom:26px; right:26px; width:58px; height:58px; border-radius:50%;
  background:linear-gradient(135deg,#0ea5a3,#0b8280); color:#fff; border:none; font-size:24px;
  box-shadow:0 14px 30px rgba(14,165,163,.4); z-index:70; display:flex; align-items:center; justify-content:center;
}
.chat-panel{
  position:fixed; bottom:96px; right:26px; width:370px; max-width:92vw; height:520px; max-height:75vh;
  background:#fff; border-radius:20px; box-shadow:0 24px 60px rgba(0,0,0,.25); display:none; flex-direction:column; overflow:hidden; z-index:70;
  border:1px solid var(--border);
}
.chat-panel.show{display:flex;}
.chat-head{background:linear-gradient(135deg,#0b1f3a,#0b8280); color:#fff; padding:14px 16px; display:flex; justify-content:space-between; align-items:center;}
.chat-head b{font-size:14px;}
.chat-head .sub{font-size:11px; color:#cfe3f4;}
.chat-settings{padding:12px 14px; border-bottom:1px solid var(--border); display:none; gap:8px; flex-direction:column; background:#f8fafc;}
.chat-settings.show{display:flex;}
.chat-settings input, .chat-settings select{padding:8px 10px; border-radius:9px; border:1.5px solid var(--border); font-size:12.5px;}
.chat-body{flex:1; overflow-y:auto; padding:14px; display:flex; flex-direction:column; gap:10px; background:#fafcfe;}
.msg{max-width:85%; padding:10px 13px; border-radius:14px; font-size:13px; line-height:1.5;}
.msg.user{align-self:flex-end; background:linear-gradient(135deg,#0ea5a3,#0b8280); color:#fff; border-bottom-right-radius:4px;}
.msg.bot{align-self:flex-start; background:#eef2f7; color:var(--navy); border-bottom-left-radius:4px; white-space:pre-wrap;}
.msg.error{align-self:flex-start; background:#fdeceb; color:#b91c1c;}
.chat-input{display:flex; gap:8px; padding:12px; border-top:1px solid var(--border); background:#fff;}
.chat-input input{flex:1; padding:10px 12px; border-radius:12px; border:1.5px solid var(--border); font-size:13px;}
.chat-input button{background:var(--teal); color:#fff; border:none; border-radius:12px; width:40px; font-size:16px;}
.icon-btn{background:rgba(255,255,255,.15); border:none; color:#fff; border-radius:8px; width:28px;height:28px; font-size:13px;}
</style>
</head>
<body>
<div class="app">
  <div class="sidebar">
    <div class="brand"><span class="mark">🌍</span><div>Travel Carbon IQ<small>Personal Intelligence</small></div></div>
    <div class="nav-group" id="nav"></div>
    <div class="sidebar-foot">Small realistic changes → meaningful carbon reduction → long-term habit change. No shame, no ultimatums — just your smartest next move.</div>
  </div>

  <div class="main">
    <div class="topbar">
      <div>
        <h1 id="page-title">My Travel</h1>
        <p id="page-sub">Every trip you've logged, in one place.</p>
      </div>
      <button class="btn btn-primary" onclick="openTripModal()">+ Add Trip</button>
    </div>

    <!-- 1. MY TRAVEL -->
    <div class="section active" id="sec-travel">
      <div class="grid grid-4" id="travel-stats"></div>
      <div class="section-title"><h2>Trip Log</h2><span class="pill" id="trip-count-pill"></span></div>
      <div class="card" style="padding:0;overflow-x:auto;">
        <table id="trip-table"><thead><tr>
          <th>Date</th><th>Route</th><th>Purpose</th><th>Mode</th><th>Distance</th><th>Time</th><th>Cost</th><th>CO2</th><th></th>
        </tr></thead><tbody></tbody></table>
      </div>
    </div>

    <!-- 2. MY CARBON -->
    <div class="section" id="sec-carbon">
      <div class="grid grid-4" id="carbon-stats"></div>
      <div class="grid grid-2" style="margin-top:18px;">
        <div class="chart-card"><h3>Monthly CO2 Trend</h3><canvas id="chartTrend"></canvas></div>
        <div class="chart-card"><h3>Emissions by Transport Mode</h3><canvas id="chartMode"></canvas></div>
      </div>
      <div class="grid grid-2" style="margin-top:18px;">
        <div class="chart-card"><h3>Emissions by Trip Purpose</h3><canvas id="chartPurpose"></canvas></div>
        <div class="chart-card">
          <h3>Highest-Carbon Trips</h3>
          <table id="high-carbon-table"><thead><tr><th>Route</th><th>Mode</th><th>CO2</th></tr></thead><tbody></tbody></table>
        </div>
      </div>
    </div>

    <!-- 3. MY PATTERNS -->
    <div class="section" id="sec-patterns">
      <div class="section-title"><h2>Recurring Journeys</h2><span class="pill">Habits, not one-off trips</span></div>
      <div class="card" style="padding:0;overflow-x:auto;">
        <table id="pattern-table"><thead><tr>
          <th>Journey</th><th>Purpose</th><th>Freq/week</th><th>Usual Mode</th><th>Avg Distance</th><th>Total CO2</th><th></th>
        </tr></thead><tbody></tbody></table>
      </div>
      <div class="section-title"><h2>Smart Alerts</h2><span class="pill">Detect → Explain → Suggest</span></div>
      <div id="alerts-wrap"></div>
    </div>

    <!-- 4. COMPARE OPTIONS -->
    <div class="section" id="sec-compare">
      <div class="card compare-select">
        <label style="font-weight:700;font-size:13px;">Choose a trip to compare alternatives for</label>
        <select id="compare-trip-select" style="margin-top:8px;width:100%;padding:11px;border-radius:10px;border:1.5px solid var(--border);font-size:13.5px;"></select>
      </div>
      <div id="compare-results"></div>
    </div>

    <!-- 5. SET MY LIMITS -->
    <div class="section" id="sec-limits">
      <div class="grid grid-3">
        <div class="card limit-card">
          <label>⏱ Max extra travel time <span class="limit-value" id="lbl-time">15 min</span></label>
          <input type="range" id="range-time" min="0" max="45" value="15">
          <p class="stat-sub" style="margin-top:10px;">How much longer are you willing to travel for a greener option?</p>
        </div>
        <div class="card limit-card">
          <label>💰 Max additional cost <span class="limit-value" id="lbl-cost">₹30</span></label>
          <input type="range" id="range-cost" min="0" max="150" value="30">
          <p class="stat-sub" style="margin-top:10px;">The most extra you'd spend per trip for a lower-carbon option.</p>
        </div>
        <div class="card limit-card">
          <label>🌿 Min CO2 reduction required <span class="limit-value" id="lbl-co2">15%</span></label>
          <input type="range" id="range-co2" min="0" max="80" value="15">
          <p class="stat-sub" style="margin-top:10px;">Below this, a switch isn't worth the hassle.</p>
        </div>
      </div>
      <button class="btn btn-primary" style="margin-top:18px;" onclick="saveLimits()">Save My Acceptable Change Zone</button>
      <span id="limits-saved-msg" style="margin-left:12px;color:#15803d;font-weight:700;font-size:13px;display:none;">✓ Saved</span>
    </div>

    <!-- 6. BEST REALISTIC CHANGE -->
    <div class="section" id="sec-recommendation">
      <div id="hero-rec-wrap"></div>
      <div id="min-change-wrap"></div>
    </div>

    <!-- 7. WHAT IF -->
    <div class="section" id="sec-whatif">
      <div class="grid grid-2">
        <div class="card">
          <h3 style="font-size:15px;margin-bottom:16px;">Adjust your weekly trips</h3>
          <div id="whatif-sliders"></div>
          <p class="stat-sub">Assumes an average trip distance of <b id="whatif-dist"></b> km, based on your logged trips.</p>
        </div>
        <div class="chart-card"><h3>Projected Weekly CO2 by Mode</h3><canvas id="chartWhatif"></canvas></div>
      </div>
      <div class="grid grid-4" style="margin-top:18px;" id="whatif-stats"></div>
    </div>

    <!-- 8. TRACK MY PROGRESS -->
    <div class="section" id="sec-progress">
      <div class="card" style="margin-bottom:18px;">
        <label style="font-weight:700;font-size:13px;">Behavior-change date</label>
        <p class="stat-sub" style="margin:4px 0 10px;">We compare your habits before and after this date.</p>
        <input type="date" id="change-date-input" style="padding:9px 12px;border-radius:10px;border:1.5px solid var(--border);font-size:13.5px;">
        <button class="btn btn-ghost btn-sm" style="margin-left:8px;" onclick="reloadProgress()">Update</button>
      </div>
      <div class="grid grid-4" id="progress-stats"></div>
      <div class="chart-card" style="margin-top:18px;"><h3>Before vs After — Weekly CO2</h3><canvas id="chartProgress"></canvas></div>
    </div>

    <!-- 9. MY CONTRIBUTION -->
    <div class="section" id="sec-contribution">
      <div class="grid grid-4" id="contribution-stats"></div>
      <div class="contrib-note" id="contribution-note"></div>
    </div>

  </div>
</div>

<!-- Trip modal -->
<div class="modal-backdrop" id="trip-modal-backdrop">
  <div class="modal">
    <h3>Add a trip</h3>
    <div class="row2">
      <div class="field" id="fld-date"><label>Date *</label><input type="date" id="f-date" autocomplete="off"></div>
      <div class="field" id="fld-purpose"><label>Purpose *</label><select id="f-purpose" autocomplete="off"><option value="">Select a purpose…</option></select></div>
    </div>
    <div class="row2">
      <div class="field" id="fld-origin"><label>Origin (starting point) *</label><input id="f-origin" name="trip-origin-field" placeholder="e.g. Home, Office, Gym" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"></div>
      <div class="field" id="fld-dest"><label>Destination *</label><input id="f-dest" name="trip-destination-field" placeholder="e.g. Office, Market, Airport" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"></div>
    </div>
    <div class="row2">
      <div class="field" id="fld-mode"><label>Transport mode *</label><select id="f-mode" autocomplete="off"><option value="">Select a mode…</option></select></div>
      <div class="field" id="fld-distance"><label>Distance (km) *</label><input type="number" step="0.1" min="0" id="f-distance" placeholder="e.g. 9.5" autocomplete="off"></div>
    </div>
    <div class="row2">
      <div class="field"><label>Travel time (min) <a href="#" onclick="autoFillTime(event)" style="font-weight:600;color:var(--teal-deep);float:right;">auto</a></label><input type="number" step="1" min="0" id="f-time" placeholder="auto-filled from mode" autocomplete="off"></div>
      <div class="field"><label>Cost (₹) <a href="#" onclick="autoFillCost(event)" style="font-weight:600;color:var(--teal-deep);float:right;">auto</a></label><input type="number" step="1" min="0" id="f-cost" placeholder="auto-filled from mode" autocomplete="off"></div>
    </div>
    <div id="f-error" style="display:none;color:#b91c1c;background:#fdeceb;border-radius:10px;padding:9px 12px;font-size:12.5px;font-weight:600;margin-top:4px;"></div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeTripModal()">Cancel</button>
      <button class="btn btn-primary" onclick="submitTrip()">Save Trip</button>
    </div>
  </div>
</div>

<!-- Chat widget -->
<button class="chat-fab" onclick="toggleChat()">💬</button>
<div class="chat-panel" id="chat-panel">
  <div class="chat-head">
    <div><b>AI Travel Coach</b><div class="sub">Powered by your OpenRouter key</div></div>
    <button class="icon-btn" onclick="toggleChatSettings()">⚙</button>
  </div>
  <div class="chat-settings" id="chat-settings">
    <input id="chat-api-key" placeholder="Paste your OpenRouter API key (sk-or-v1-...)" type="password">
    <select id="chat-model">
      <option value="openai/gpt-4o-mini">openai/gpt-4o-mini</option>
      <option value="anthropic/claude-3.5-sonnet">anthropic/claude-3.5-sonnet</option>
      <option value="meta-llama/llama-3.1-8b-instruct">meta-llama/llama-3.1-8b-instruct</option>
      <option value="google/gemini-flash-1.5">google/gemini-flash-1.5</option>
    </select>
    <button class="btn btn-primary btn-sm" onclick="saveChatSettings()">Save key locally</button>
    <span class="stat-sub">Stored only in your browser (localStorage). Never sent anywhere except OpenRouter.</span>
  </div>
  <div class="chat-body" id="chat-body">
    <div class="msg bot">Hi! I'm your Travel Coach 🌱 Ask me things like "what's my easiest win this month?" — add your OpenRouter key in ⚙ settings first.</div>
  </div>
  <div class="chat-input">
    <input id="chat-input" placeholder="Ask about your travel & carbon..." onkeydown="if(event.key==='Enter')sendChat()">
    <button onclick="sendChat()">➤</button>
  </div>
</div>

<script>
const NAV = [
  {id:'travel', num:1, label:'My Travel', icon:'🧭', sub:"Every trip you've logged, in one place."},
  {id:'carbon', num:2, label:'My Carbon', icon:'🌡️', sub:'Your total footprint, broken down.'},
  {id:'patterns', num:3, label:'My Patterns', icon:'🔁', sub:'The recurring journeys behind your footprint.'},
  {id:'compare', num:4, label:'Compare Options', icon:'⚖️', sub:'Same journey, every mode, side by side.'},
  {id:'limits', num:5, label:'Set My Limits', icon:'🎚️', sub:'Your Acceptable Change Zone.'},
  {id:'recommendation', num:6, label:'Best Realistic Change', icon:'🏆', sub:'The smallest change, the biggest benefit.'},
  {id:'whatif', num:7, label:'What If?', icon:'🧪', sub:'Play with your weekly mix and see the impact instantly.'},
  {id:'progress', num:8, label:'Track My Progress', icon:'📊', sub:'Before vs after — are you actually changing?'},
  {id:'contribution', num:9, label:'My Contribution', icon:'🌍', sub:'Your estimated contribution to a cleaner society.'},
];
let MODES = {}, PURPOSES = [], CURRENCY = '₹';
let charts = {};

function $(id){return document.getElementById(id);}

function buildNav(){
  const nav = $('nav');
  nav.innerHTML = NAV.map(n => `<a class="nav-item" data-id="${n.id}" onclick="showSection('${n.id}')"><span class="num">${n.num}</span><span>${n.icon} ${n.label}</span></a>`).join('');
}

function showSection(id){
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  $('sec-'+id).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active', n.dataset.id===id));
  const meta = NAV.find(n=>n.id===id);
  $('page-title').textContent = meta.label;
  $('page-sub').textContent = meta.sub;
  refreshSection(id);
}

function refreshSection(id){
  if(id==='travel') loadTravel();
  if(id==='carbon') loadCarbon();
  if(id==='patterns') loadPatterns();
  if(id==='compare') loadCompareList();
  if(id==='limits') loadLimits();
  if(id==='recommendation') loadRecommendation();
  if(id==='whatif') loadWhatif();
  if(id==='progress') reloadProgress();
  if(id==='contribution') loadContribution();
}

function fmt(n, d=1){ return Number(n).toLocaleString(undefined,{maximumFractionDigits:d, minimumFractionDigits:0}); }

/* ---------------- MY TRAVEL ---------------- */
async function loadTravel(){
  const [summary, trips] = await Promise.all([fetch('/api/summary').then(r=>r.json()), fetch('/api/trips').then(r=>r.json())]);
  $('travel-stats').innerHTML = `
    ${statCard('🧾','Total Trips', summary.trip_count, 'logged so far')}
    ${statCard('📏','Total Distance', fmt(summary.total_distance_km)+' km', 'across all trips')}
    ${statCard('💸','Total Spent', CURRENCY+fmt(summary.total_cost), 'on travel')}
    ${statCard('⏳','Time Traveled', Math.round(summary.total_time_min/60)+' hrs', 'in transit')}
  `;
  $('trip-count-pill').textContent = summary.trip_count + ' trips';
  const tbody = document.querySelector('#trip-table tbody');
  tbody.innerHTML = trips.slice(0,40).map(t => `<tr>
    <td>${t.date}</td>
    <td>${t.origin} → ${t.destination}</td>
    <td>${t.purpose}</td>
    <td><span class="tag">${MODES[t.mode]?.icon||''} ${MODES[t.mode]?.label||t.mode}</span></td>
    <td>${fmt(t.distance_km)} km</td>
    <td>${fmt(t.time_min,0)} min</td>
    <td>${CURRENCY}${fmt(t.cost)}</td>
    <td><b>${fmt(t.co2_kg,2)} kg</b></td>
    <td><a href="#" onclick="deleteTrip(${t.id});return false;" style="color:#ef4444;">✕</a></td>
  </tr>`).join('');
}

function statCard(icon,label,value,sub,bg='#e8f7f6',fg='#0b8280'){
  return `<div class="card"><div class="stat-icon" style="background:${bg};color:${fg};">${icon}</div>
  <h3>${label}</h3><div class="stat-value">${value}</div><div class="stat-sub">${sub}</div></div>`;
}

async function deleteTrip(id){
  await fetch('/api/trips/'+id, {method:'DELETE'});
  loadTravel();
}

/* ---------------- MY CARBON ---------------- */
async function loadCarbon(){
  const s = await fetch('/api/summary').then(r=>r.json());
  $('carbon-stats').innerHTML = `
    ${statCard('🌫️','Total CO2 Footprint', fmt(s.total_co2_kg,1)+' kg', 'since you started tracking', '#fdeceb','#c0392b')}
    ${statCard('📅','Avg per Month', fmt(s.monthly_trend.length? s.total_co2_kg/s.monthly_trend.length:0,1)+' kg', 'monthly average')}
    ${statCard('🚗','Top Mode', s.by_mode[0]? s.by_mode[0].label:'—', s.by_mode[0]? fmt(s.by_mode[0].co2_kg,1)+' kg from this mode':'')}
    ${statCard('🎯','Top Purpose', s.by_purpose[0]? s.by_purpose[0].purpose:'—', s.by_purpose[0]? fmt(s.by_purpose[0].co2_kg,1)+' kg from this purpose':'')}
  `;

  destroyChart('chartTrend');
  charts.chartTrend = new Chart($('chartTrend'), {
    type:'line',
    data:{ labels: s.monthly_trend.map(m=>m.month),
      datasets:[{label:'CO2 (kg)', data:s.monthly_trend.map(m=>m.co2_kg), borderColor:'#0ea5a3', backgroundColor:'rgba(14,165,163,.12)', fill:true, tension:.35, pointRadius:3}]},
    options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}}}
  });

  destroyChart('chartMode');
  charts.chartMode = new Chart($('chartMode'), {
    type:'doughnut',
    data:{ labels: s.by_mode.map(m=>m.label), datasets:[{data:s.by_mode.map(m=>m.co2_kg), backgroundColor:s.by_mode.map(m=>m.color)}] },
    options:{plugins:{legend:{position:'bottom', labels:{boxWidth:10,font:{size:11}}}}}
  });

  destroyChart('chartPurpose');
  charts.chartPurpose = new Chart($('chartPurpose'), {
    type:'bar',
    data:{ labels: s.by_purpose.map(p=>p.purpose), datasets:[{label:'CO2 (kg)', data:s.by_purpose.map(p=>p.co2_kg), backgroundColor:'#3a86ff', borderRadius:6}] },
    options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}}}
  });

  const hb = document.querySelector('#high-carbon-table tbody');
  hb.innerHTML = s.high_carbon_trips.map(t=>`<tr><td>${t.origin} → ${t.destination}</td><td>${MODES[t.mode]?.icon} ${MODES[t.mode]?.label}</td><td><b>${fmt(t.co2_kg,2)} kg</b></td></tr>`).join('');
}

function destroyChart(key){ if(charts[key]){ charts[key].destroy(); delete charts[key]; } }

/* ---------------- MY PATTERNS ---------------- */
async function loadPatterns(){
  const [patterns, alerts] = await Promise.all([fetch('/api/patterns').then(r=>r.json()), fetch('/api/alerts').then(r=>r.json())]);
  const tb = document.querySelector('#pattern-table tbody');
  tb.innerHTML = patterns.map(p => `<tr>
    <td><b>${p.origin} → ${p.destination}</b></td>
    <td>${p.purpose}</td>
    <td>${p.weekly_frequency}x</td>
    <td><span class="tag">${MODES[p.dominant_mode]?.icon} ${MODES[p.dominant_mode]?.label}</span></td>
    <td>${fmt(p.avg_distance_km)} km</td>
    <td><b>${fmt(p.total_co2_kg,1)} kg</b></td>
    <td><a href="#" onclick="jumpToCompare('${p.origin}','${p.destination}');return false;" style="color:#0b8280;font-weight:700;">Compare →</a></td>
  </tr>`).join('');

  const wrap = $('alerts-wrap');
  if(!alerts.length){ wrap.innerHTML = '<div class="empty">No alerts right now — your travel patterns look steady.</div>'; return; }
  wrap.innerHTML = alerts.map(a => `<div class="alert ${a.severity}">
    <div class="icon">${a.icon}</div>
    <div>
      <h4>${a.title}</h4>
      <p><b>Detected:</b> ${a.detect}</p>
      <p><b>Why:</b> ${a.explain}</p>
      <p><b>Suggestion:</b> ${a.suggest}</p>
    </div>
  </div>`).join('');
}

function jumpToCompare(origin,dest){
  showSection('compare');
  setTimeout(()=>{
    const sel = $('compare-trip-select');
    for(const opt of sel.options){ if(opt.dataset.o===origin && opt.dataset.d===dest){ sel.value = opt.value; break; } }
    renderCompare(sel.value);
  }, 200);
}

/* ---------------- COMPARE OPTIONS ---------------- */
async function loadCompareList(){
  const trips = await fetch('/api/trips').then(r=>r.json());
  const sel = $('compare-trip-select');
  sel.innerHTML = trips.map(t=>`<option value="${t.id}" data-o="${t.origin}" data-d="${t.destination}">${t.date} · ${t.origin} → ${t.destination} · ${MODES[t.mode]?.label} (${fmt(t.distance_km)} km)</option>`).join('');
  sel.onchange = ()=>renderCompare(sel.value);
  if(trips.length) renderCompare(trips[0].id);
}

async function renderCompare(tripId){
  const data = await fetch('/api/compare/'+tripId).then(r=>r.json());
  const t = data.trip;
  const html = `
    <div class="card" style="margin-bottom:16px;">
      <h3 style="margin-bottom:8px;">Current: ${MODES[t.mode]?.icon} ${MODES[t.mode]?.label} — ${t.origin} → ${t.destination}</h3>
      <div class="stat-sub">${fmt(t.distance_km)} km · ${fmt(t.time_min,0)} min · ${CURRENCY}${fmt(t.cost)} · <b>${fmt(t.co2_kg,2)} kg CO2</b></div>
    </div>
    <div class="compare-grid">
    ${data.options.map(o => `
      <div class="opt-card ${o.qualifying?'qualifies':''}">
        <span class="status-chip ${o.qualifying?'badge-ok':'badge-no'}">${o.qualifying?'✓ Within your limits':'Exceeds limits'}</span>
        <div class="mode-row"><span class="mode-icon">${o.icon}</span><span class="mode-name">${o.label}</span></div>
        <div class="metric"><span>CO2</span><b>${fmt(o.co2_kg,2)} kg</b></div>
        <div class="metric"><span>CO2 reduction</span><b style="color:${o.co2_reduction_kg>0?'#15803d':'#c0392b'}">${o.co2_reduction_kg>0?'-':'+'}${fmt(Math.abs(o.co2_reduction_kg),2)} kg (${o.co2_reduction_pct}%)</b></div>
        <div class="metric"><span>Cost</span><b>${CURRENCY}${fmt(o.cost)}</b></div>
        <div class="metric"><span>Money saved</span><b style="color:${o.money_saved>0?'#15803d':'#c0392b'}">${o.money_saved>0?'+':''}${CURRENCY}${fmt(o.money_saved)}</b></div>
        <div class="metric"><span>Travel time</span><b>${fmt(o.time_min,0)} min</b></div>
        <div class="metric"><span>Extra time vs now</span><b style="color:${o.extra_time_min<=0?'#15803d':'#b45309'}">${o.extra_time_min>0?'+':''}${fmt(o.extra_time_min,0)} min</b></div>
      </div>`).join('')}
    </div>`;
  $('compare-results').innerHTML = html;
}

/* ---------------- SET MY LIMITS ---------------- */
async function loadLimits(){
  const l = await fetch('/api/limits').then(r=>r.json());
  $('range-time').value = l.max_extra_time_min; $('lbl-time').textContent = l.max_extra_time_min+' min';
  $('range-cost').value = l.max_extra_cost; $('lbl-cost').textContent = CURRENCY+l.max_extra_cost;
  $('range-co2').value = l.min_co2_reduction_pct; $('lbl-co2').textContent = l.min_co2_reduction_pct+'%';
}
window.addEventListener('DOMContentLoaded', ()=>{
  $('range-time').addEventListener('input', e=>$('lbl-time').textContent = e.target.value+' min');
  $('range-cost').addEventListener('input', e=>$('lbl-cost').textContent = CURRENCY+e.target.value);
  $('range-co2').addEventListener('input', e=>$('lbl-co2').textContent = e.target.value+'%');
});

async function saveLimits(){
  const body = {
    max_extra_time_min: Number($('range-time').value),
    max_extra_cost: Number($('range-cost').value),
    min_co2_reduction_pct: Number($('range-co2').value),
  };
  await fetch('/api/limits', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  $('limits-saved-msg').style.display='inline';
  setTimeout(()=>$('limits-saved-msg').style.display='none', 2000);
}

/* ---------------- BEST REALISTIC CHANGE ---------------- */
async function loadRecommendation(){
  const r = await fetch('/api/recommendation').then(r=>r.json());
  const b = r.best_realistic_change;
  if(!b){
    $('hero-rec-wrap').innerHTML = `<div class="hero-rec"><div class="trophy">🏆 BEST REALISTIC CHANGE</div>
      <h2>No qualifying swap yet</h2><p class="sub">None of your journeys have an alternative within your current Acceptable Change Zone. Try loosening your limits a little in Set My Limits.</p></div>`;
    $('min-change-wrap').innerHTML = '';
    return;
  }
  $('hero-rec-wrap').innerHTML = `
    <div class="hero-rec">
      <div class="trophy">🏆 BEST REALISTIC CHANGE</div>
      <h2>${b.pattern.origin} → ${b.pattern.destination}: switch ${MODES[b.from_mode]?.label} → ${MODES[b.option.mode]?.label}</h2>
      <p class="sub">${MODES[b.from_mode]?.icon} ${MODES[b.from_mode]?.label} <span style="opacity:.6">(currently ${b.pattern.weekly_frequency}x/week)</span> → ${MODES[b.option.mode]?.icon} ${MODES[b.option.mode]?.label}</p>
      <div class="hero-stats">
        <div class="hero-stat"><div class="lbl">CO2 reduction</div><div class="val">${fmt(b.option.co2_reduction_pct,0)}%</div></div>
        <div class="hero-stat"><div class="lbl">CO2 saved / month</div><div class="val">${fmt(b.monthly_co2_saved_kg,1)} kg</div></div>
        <div class="hero-stat"><div class="lbl">Money saved / month</div><div class="val">${CURRENCY}${fmt(b.monthly_money_saved,0)}</div></div>
        <div class="hero-stat"><div class="lbl">Extra time / trip</div><div class="val">${b.option.extra_time_min>0?'+':''}${fmt(b.option.extra_time_min,0)} min</div></div>
      </div>
      <div class="hero-reasons"><b>Why this was chosen:</b><br>${b.reasons.map(r=>'• '+r).join('<br>')}</div>
    </div>`;

  const m = r.minimum_change_maximum_impact;
  if(m){
    $('min-change-wrap').innerHTML = `<div class="mini-rec">
      <h3>🎯 Minimum Change, Maximum Impact</h3>
      <p class="stat-sub">The smallest possible adjustment that still crosses your minimum CO2 reduction threshold.</p>
      <div class="flow"><span>${MODES[m.from_mode]?.icon} ${MODES[m.from_mode]?.label}</span><span class="arrow">→</span><span>${MODES[m.option.mode]?.icon} ${MODES[m.option.mode]?.label}</span></div>
      <div class="stat-sub">${m.pattern.origin} → ${m.pattern.destination} · +${fmt(m.option.extra_time_min,0)} min · ${CURRENCY}${m.option.extra_cost>0?'+':''}${fmt(m.option.extra_cost)} · cuts ${fmt(m.option.co2_reduction_pct,0)}% CO2 (${fmt(m.weekly_co2_saved_kg,2)} kg/week)</div>
    </div>`;
  } else { $('min-change-wrap').innerHTML=''; }
}

/* ---------------- WHAT IF ---------------- */
let whatifBaseline = null;
async function loadWhatif(){
  const trips = await fetch('/api/trips').then(r=>r.json());
  const avgDist = trips.length ? (trips.reduce((a,t)=>a+t.distance_km,0)/trips.length) : 8;
  $('whatif-dist').textContent = fmt(avgDist,1);

  const focusModes = ['car','metro','bus','bike','walk','carpool'];
  const baseCounts = {};
  focusModes.forEach(m=>{ baseCounts[m] = 0; });
  // seed sliders with a rough current split (rounded) for a sensible starting point
  const patternResp = await fetch('/api/patterns').then(r=>r.json());
  patternResp.forEach(p=>{ if(focusModes.includes(p.dominant_mode)) baseCounts[p.dominant_mode] += p.weekly_frequency; });
  focusModes.forEach(m=> baseCounts[m] = Math.round(baseCounts[m]||0));

  $('whatif-sliders').innerHTML = focusModes.map(m=>`
    <div class="slider-row">
      <div class="mlabel">${MODES[m].icon} ${MODES[m].label}</div>
      <input type="range" min="0" max="20" value="${baseCounts[m]}" id="wi-${m}" oninput="updateWhatif()">
      <div class="count" id="wi-${m}-val">${baseCounts[m]}</div>
    </div>`).join('');

  whatifBaseline = avgDist;
  updateWhatif();
}

async function updateWhatif(){
  const focusModes = ['car','metro','bus','bike','walk','carpool'];
  const counts = {};
  focusModes.forEach(m=>{ const v = Number($('wi-'+m).value); counts[m]=v; $('wi-'+m+'-val').textContent = v; });
  const resp = await fetch('/api/whatif', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({counts_per_week: counts, avg_distance_km: whatifBaseline})}).then(r=>r.json());

  $('whatif-stats').innerHTML = `
    ${statCard('🌫️','Projected Monthly CO2', fmt(resp.monthly_co2_kg,1)+' kg', 'at this weekly mix')}
    ${statCard('✅','CO2 Avoided / Month', fmt(resp.co2_saved_monthly_kg,1)+' kg', 'vs your current baseline', '#e7f9ee','#15803d')}
    ${statCard('💰','Money Saved / Year', CURRENCY+fmt(resp.money_saved_yearly,0), 'projected annual saving')}
    ${statCard('⏳','Extra Time / Week', (resp.extra_time_weekly_min>0?'+':'')+fmt(resp.extra_time_weekly_min,0)+' min', 'vs your current routine')}
  `;

  destroyChart('chartWhatif');
  charts.chartWhatif = new Chart($('chartWhatif'), {
    type:'bar',
    data:{ labels: focusModes.map(m=>MODES[m].label),
      datasets:[{label:'Weekly CO2 (kg)', data: focusModes.map(m=>calcClientCo2(m, counts[m])), backgroundColor: focusModes.map(m=>MODES[m].color), borderRadius:6}] },
    options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}}}
  });
}
function calcClientCo2(mode, n){ return (MODES[mode].ef/1000)*whatifBaseline*n; }

/* ---------------- TRACK MY PROGRESS ---------------- */
async function reloadProgress(){
  const dateInput = $('change-date-input');
  let url = '/api/progress';
  if(dateInput.value) url += '?change_date='+dateInput.value;
  const p = await fetch(url).then(r=>r.json());
  if(!dateInput.value) dateInput.value = p.change_date;

  $('progress-stats').innerHTML = `
    ${statCard('✅','CO2 Avoided / Month', fmt(p.co2_avoided_monthly_kg,1)+' kg', p.co2_avoided_monthly_kg>=0?'improvement since change':'trending up', '#e7f9ee','#15803d')}
    ${statCard('💰','Money Saved / Month', CURRENCY+fmt(p.money_saved_monthly,0), 'compared with before')}
    ${statCard('🚗','Car-type Trip Share', p.after.car_trip_share_pct+'%', (p.car_share_change_pct<=0?'':'+')+p.car_share_change_pct+' pts vs before')}
    ${statCard('📈','Overall Improvement', fmt(p.pct_improvement,0)+'%', 'reduction in weekly CO2')}
  `;

  destroyChart('chartProgress');
  charts.chartProgress = new Chart($('chartProgress'), {
    type:'bar',
    data:{ labels:['Before', 'After'], datasets:[{label:'Weekly CO2 (kg)', data:[p.before.weekly_co2_kg, p.after.weekly_co2_kg], backgroundColor:['#94a3b8','#0ea5a3'], borderRadius:8}] },
    options:{plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true}}}
  });
}

/* ---------------- MY CONTRIBUTION ---------------- */
async function loadContribution(){
  const c = await fetch('/api/contribution').then(r=>r.json());
  $('contribution-stats').innerHTML = `
    <div class="card contrib-card"><div class="big">${fmt(c.co2_avoided_kg,0)} kg</div><div class="lbl">🌫️ CO2 Avoided</div></div>
    <div class="card contrib-card"><div class="big">${fmt(c.fuel_saved_litres,0)} L</div><div class="lbl">⛽ Fuel Saved</div></div>
    <div class="card contrib-card"><div class="big">${c.vehicle_trips_avoided}</div><div class="lbl">🚙 Vehicle Trips Avoided</div></div>
    <div class="card contrib-card"><div class="big">${fmt(c.vehicle_km_reduced,0)} km</div><div class="lbl">🛣️ Vehicle-km Reduced</div></div>
  `;
  $('contribution-note').innerHTML = `<b>ℹ️ ${c.note}</b><br><br>Roughly equivalent to the annual absorption of <b>${fmt(c.trees_equivalent_per_year,0)} mature trees</b> — a fun, illustrative comparison, not a scientific offset claim.`;
}

/* ---------------- ADD TRIP MODAL ---------------- */
function openTripModal(){
  // reset the form fresh each time it's opened, and clear any previous error state
  $('f-date').value = new Date().toISOString().slice(0,10);
  $('f-purpose').value = '';
  $('f-origin').value = '';
  $('f-dest').value = '';
  $('f-mode').value = '';
  $('f-distance').value = '';
  $('f-time').value = '';
  $('f-cost').value = '';
  clearFieldErrors();
  $('trip-modal-backdrop').classList.add('show');
}
function closeTripModal(){ $('trip-modal-backdrop').classList.remove('show'); }
function autoFillTime(e){ e.preventDefault(); const m=$('f-mode').value, d=Number($('f-distance').value||0); if(!m||!d)return; const speed=MODES[m].speed, oh=MODES[m].overhead_min; $('f-time').value = Math.round((d/speed*60+oh)*10)/10; }
function autoFillCost(e){ e.preventDefault(); const m=$('f-mode').value, d=Number($('f-distance').value||0); if(!m||!d)return; $('f-cost').value = Math.round(d*MODES[m].cost_km*100)/100; }

function clearFieldErrors(){
  $('f-error').style.display='none'; $('f-error').textContent='';
  ['fld-date','fld-purpose','fld-origin','fld-dest','fld-mode','fld-distance'].forEach(id=>$(id).classList.remove('invalid'));
}

function showFieldError(msg, invalidIds){
  $('f-error').textContent = msg;
  $('f-error').style.display = 'block';
  invalidIds.forEach(id=>$(id).classList.add('invalid'));
}

async function submitTrip(){
  clearFieldErrors();
  const missing = [];
  if(!$('f-date').value) missing.push('fld-date');
  if(!$('f-purpose').value) missing.push('fld-purpose');
  if(!$('f-origin').value.trim()) missing.push('fld-origin');
  if(!$('f-dest').value.trim()) missing.push('fld-dest');
  if(!$('f-mode').value) missing.push('fld-mode');
  if(!Number($('f-distance').value)) missing.push('fld-distance');
  if(missing.length){
    showFieldError('Please fill in every required field (marked *) before saving.', missing);
    return;
  }
  const body = {
    date: $('f-date').value, origin: $('f-origin').value.trim(), destination: $('f-dest').value.trim(),
    purpose: $('f-purpose').value, mode: $('f-mode').value, distance_km: Number($('f-distance').value),
    time_min: $('f-time').value? Number($('f-time').value): null, cost: $('f-cost').value? Number($('f-cost').value): null,
  };
  const r = await fetch('/api/trips', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  if(r.ok){ closeTripModal(); loadTravel(); } else { const e = await r.json(); showFieldError(e.error||'Could not save trip', []); }
}

/* ---------------- CHAT ---------------- */
let chatHistory = [];
function toggleChat(){ $('chat-panel').classList.toggle('show'); }
function toggleChatSettings(){ $('chat-settings').classList.toggle('show'); }
function saveChatSettings(){
  localStorage.setItem('ptci_api_key', $('chat-api-key').value.trim());
  localStorage.setItem('ptci_model', $('chat-model').value);
  toggleChatSettings();
}
function loadChatSettings(){
  const k = localStorage.getItem('ptci_api_key'); const m = localStorage.getItem('ptci_model');
  if(k) $('chat-api-key').value = k;
  if(m) $('chat-model').value = m;
  if(!k) toggleChatSettings();
}
async function sendChat(){
  const input = $('chat-input'); const text = input.value.trim();
  if(!text) return;
  input.value='';
  appendMsg('user', text);
  chatHistory.push({role:'user', content:text});
  const api_key = localStorage.getItem('ptci_api_key') || '';
  const model = localStorage.getItem('ptci_model') || 'openai/gpt-4o-mini';
  const thinking = appendMsg('bot', 'Thinking...');
  try{
    const r = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:text, api_key, model, history:chatHistory})});
    const data = await r.json();
    thinking.remove();
    if(!r.ok){ appendMsg('error', data.error || 'Something went wrong.'); return; }
    appendMsg('bot', data.reply);
    chatHistory.push({role:'assistant', content:data.reply});
  }catch(e){ thinking.remove(); appendMsg('error', 'Network error contacting the server.'); }
}
function appendMsg(cls, text){
  const div = document.createElement('div'); div.className='msg '+cls; div.textContent = text;
  $('chat-body').appendChild(div); $('chat-body').scrollTop = $('chat-body').scrollHeight;
  return div;
}

/* ---------------- INIT ---------------- */
async function init(){
  const modeData = await fetch('/api/modes').then(r=>r.json());
  MODES = modeData.modes; PURPOSES = modeData.purposes; CURRENCY = modeData.currency;
  buildNav();
  $('f-purpose').innerHTML = '<option value="">Select a purpose…</option>' + PURPOSES.map(p=>`<option value="${p}">${p}</option>`).join('');
  $('f-mode').innerHTML = '<option value="">Select a mode…</option>' + Object.entries(MODES).map(([k,v])=>`<option value="${k}">${v.icon} ${v.label}</option>`).join('');
  loadChatSettings();
  showSection('travel');
}
init();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return Response(HTML_PAGE, mimetype="text/html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
