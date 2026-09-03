# -*- coding: utf-8 -*-
"""
ICC Tournament NRR Calculator — Flask Web App

A simple web interface for calculating ICC Net Run Rate standings
from match results entered through a browser form.
"""

import os
import uuid
import json
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session
)
from nrr_cal import TournamentNRRCalculator

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", uuid.uuid4().hex)

# In-memory store keyed by session id so each visitor gets their own tournament.
# Each session holds {"quota": float, "matches": [ {match record}, ... ]}.
_sessions: dict[str, dict] = {}


def _ensure_session() -> str:
    if "sid" not in session:
        session["sid"] = uuid.uuid4().hex
    sid = session["sid"]
    if sid not in _sessions:
        _sessions[sid] = {"quota": 20.0, "matches": []}
    return sid


def _get_session_data() -> dict | None:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid]
    return None


def _build_engine(data: dict) -> TournamentNRRCalculator:
    """Rebuild a fresh engine from stored match records and replay them."""
    engine = TournamentNRRCalculator(format_quota=data["quota"])
    for m in data["matches"]:
        engine.log_match(
            team1=m["team1"], team2=m["team2"],
            team1_runs=m["team1_runs"], team1_overs=m["team1_overs"],
            team1_bowled_out=m["team1_bowled_out"],
            team2_runs=m["team2_runs"], team2_overs=m["team2_overs"],
            team2_bowled_out=m["team2_bowled_out"],
            is_dls=m["is_dls"],
            team2_dls_allocated_overs=m["team2_dls_allocated_overs"],
            team2_dls_par_score=m["team2_dls_par_score"],
        )
    return engine


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    _ensure_session()
    data = _get_session_data()

    if request.method == "POST":
        quota_raw = request.form.get("format_quota", "20").strip()
        try:
            quota = float(quota_raw)
            if quota not in (20.0, 50.0):
                raise ValueError
        except ValueError:
            flash("Format quota must be 20 (T20I) or 50 (ODI).", "error")
            return redirect(url_for("index"))

        data["quota"] = quota
        flash(f"Tournament started — {int(quota)}-over format.", "success")
        return redirect(url_for("standings"))

    return render_template("index.html", has_tournament=bool(data["matches"]) or data["quota"] is not None)


@app.route("/add-match", methods=["GET", "POST"])
def add_match():
    _ensure_session()
    data = _get_session_data()

    if request.method == "POST":
        # ---- Collect & validate ----------------------------------
        parsed, errors = _parse_match_form(data["quota"])

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("add_match"))

        data["matches"].append(parsed)
        flash(f"Match logged: {parsed['team1']} vs {parsed['team2']}", "success")
        return redirect(url_for("standings"))

    engine = _build_engine(data)
    return render_template("add_match.html", engine=engine)


@app.route("/edit/<int:match_index>", methods=["GET", "POST"])
def edit_match(match_index):
    _ensure_session()
    data = _get_session_data()

    if match_index < 0 or match_index >= len(data["matches"]):
        flash("Match not found.", "error")
        return redirect(url_for("standings"))

    if request.method == "POST":
        parsed, errors = _parse_match_form(data["quota"])

        if errors:
            for e in errors:
                flash(e, "error")
            return redirect(url_for("edit_match", match_index=match_index))

        data["matches"][match_index] = parsed
        flash(f"Match updated: {parsed['team1']} vs {parsed['team2']}", "success")
        return redirect(url_for("standings"))

    engine = _build_engine(data)
    record = data["matches"][match_index]
    return render_template(
        "edit_match.html",
        engine=engine,
        match_json=json.dumps(record),
        match_index=match_index,
    )


@app.route("/standings")
def standings():
    _ensure_session()
    data = _get_session_data()
    engine = _build_engine(data)
    table = engine.calculate_table()
    return render_template(
        "standings.html",
        table=table,
        matches=data["matches"],
        format_quota=int(data["quota"]),
    )


@app.route("/standings/json")
def standings_json():
    """Return standings as JSON for fetch()-based refresh."""
    _ensure_session()
    data = _get_session_data()
    engine = _build_engine(data)
    return {"table": engine.calculate_table()}, 200


@app.route("/reset", methods=["POST"])
def reset():
    _ensure_session()
    sid = session.get("sid")
    if sid and sid in _sessions:
        _sessions[sid] = {"quota": 20.0, "matches": []}
    flash("Tournament has been reset.", "success")
    return redirect(url_for("index"))


# ------------------------------------------------------------------
# Form parsing / validation helpers
# ------------------------------------------------------------------

def _parse_match_form(quota: float) -> tuple[dict, list[str]]:
    """Validate form data and return (match_record, errors)."""
    errors: list[str] = []

    team1 = request.form.get("team1", "").strip()
    team2 = request.form.get("team2", "").strip()
    if not team1:
        errors.append("Team 1 name is required.")
    if not team2:
        errors.append("Team 2 name is required.")

    def _int_field(name: str, label: str) -> int | None:
        raw = request.form.get(name, "").strip()
        if raw == "":
            errors.append(f"{label} is required.")
            return None
        try:
            return int(raw)
        except ValueError:
            errors.append(f"{label} must be a whole number.")
            return None

    def _float_field(name: str, label: str) -> float | None:
        raw = request.form.get(name, "").strip()
        if raw == "":
            errors.append(f"{label} is required.")
            return None
        try:
            return float(raw)
        except ValueError:
            errors.append(f"{label} must be a number.")
            return None

    t1_runs = _int_field("team1_runs", "Team 1 runs")
    t1_overs = _float_field("team1_overs", "Team 1 overs")
    t2_runs = _int_field("team2_runs", "Team 2 runs")
    t2_overs = _float_field("team2_overs", "Team 2 overs")

    if t1_overs is not None and (t1_overs < 0 or t1_overs > quota):
        errors.append(f"Team 1 overs must be between 0 and {int(quota)}.")
    if t2_overs is not None and (t2_overs < 0 or t2_overs > quota):
        errors.append(f"Team 2 overs must be between 0 and {int(quota)}.")

    t1_bowled_out = request.form.get("team1_bowled_out") == "on"
    t2_bowled_out = request.form.get("team2_bowled_out") == "on"
    is_dls = request.form.get("is_dls") == "on"

    team2_dls_allocated_overs = 0.0
    team2_dls_par_score = 0
    if is_dls:
        dls_overs = _float_field("team2_dls_allocated_overs", "DLS allocated overs")
        dls_par = _int_field("team2_dls_par_score", "DLS par score")
        if dls_overs is not None:
            team2_dls_allocated_overs = dls_overs
        if dls_par is not None:
            team2_dls_par_score = dls_par

    record = {
        "team1": team1, "team2": team2,
        "team1_runs": t1_runs, "team1_overs": t1_overs,
        "team1_bowled_out": t1_bowled_out,
        "team2_runs": t2_runs, "team2_overs": t2_overs,
        "team2_bowled_out": t2_bowled_out,
        "is_dls": is_dls,
        "team2_dls_allocated_overs": team2_dls_allocated_overs,
        "team2_dls_par_score": team2_dls_par_score,
    }
    return record, errors


# ------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
