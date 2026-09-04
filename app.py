# -*- coding: utf-8 -*-
"""
ICC Tournament NRR Calculator — Flask Web App (multi-tournament + PostgreSQL)

Supports managing several tournaments at once, each with its own matches and
NRR standings. Data is persisted to a PostgreSQL database (e.g. Neon).
"""

import os
import json
import uuid
from datetime import datetime

from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session
)
from sqlalchemy import (
    create_engine, Column, Integer, Float, String, Boolean, DateTime,
    ForeignKey, orm
)
from sqlalchemy.orm import declarative_base, sessionmaker

from nrr_cal import TournamentNRRCalculator

# ------------------------------------------------------------------
# Config / DB setup
# ------------------------------------------------------------------

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", uuid.uuid4().hex)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Tournament(Base):
    __tablename__ = "tournaments"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    format_quota = Column(Float, nullable=False, default=20.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    matches = orm.relationship(
        "Match", back_populates="tournament",
        cascade="all, delete-orphan", order_by="Match.id",
    )


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    tournament_id = Column(Integer, ForeignKey("tournaments.id"), nullable=False)

    team1 = Column(String(200), nullable=False)
    team2 = Column(String(200), nullable=False)
    team1_runs = Column(Integer, nullable=False)
    team1_overs = Column(Float, nullable=False)
    team1_bowled_out = Column(Boolean, nullable=False, default=False)
    team2_runs = Column(Integer, nullable=False)
    team2_overs = Column(Float, nullable=False)
    team2_bowled_out = Column(Boolean, nullable=False, default=False)
    is_dls = Column(Boolean, nullable=False, default=False)
    team2_dls_allocated_overs = Column(Float, nullable=False, default=0.0)
    team2_dls_par_score = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    tournament = orm.relationship("Tournament", back_populates="matches")


Base.metadata.create_all(engine)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _get_session():
    return SessionLocal()


def _build_engine(tournament: Tournament) -> TournamentNRRCalculator:
    """Build an NRR engine and replay all of a tournament's matches."""
    calc = TournamentNRRCalculator(format_quota=tournament.format_quota)
    for m in tournament.matches:
        calc.log_match(
            team1=m.team1, team2=m.team2,
            team1_runs=m.team1_runs, team1_overs=m.team1_overs,
            team1_bowled_out=m.team1_bowled_out,
            team2_runs=m.team2_runs, team2_overs=m.team2_overs,
            team2_bowled_out=m.team2_bowled_out,
            is_dls=m.is_dls,
            team2_dls_allocated_overs=m.team2_dls_allocated_overs,
            team2_dls_par_score=m.team2_dls_par_score,
        )
    return calc


def _match_to_record(m: Match) -> dict:
    return {
        "team1": m.team1, "team2": m.team2,
        "team1_runs": m.team1_runs, "team1_overs": m.team1_overs,
        "team1_bowled_out": m.team1_bowled_out,
        "team2_runs": m.team2_runs, "team2_overs": m.team2_overs,
        "team2_bowled_out": m.team2_bowled_out,
        "is_dls": m.is_dls,
        "team2_dls_allocated_overs": m.team2_dls_allocated_overs,
        "team2_dls_par_score": m.team2_dls_par_score,
    }


def _apply_record_to_match(record: dict, m: Match) -> None:
    m.team1 = record["team1"]
    m.team2 = record["team2"]
    m.team1_runs = record["team1_runs"]
    m.team1_overs = record["team1_overs"]
    m.team1_bowled_out = record["team1_bowled_out"]
    m.team2_runs = record["team2_runs"]
    m.team2_overs = record["team2_overs"]
    m.team2_bowled_out = record["team2_bowled_out"]
    m.is_dls = record["is_dls"]
    m.team2_dls_allocated_overs = record["team2_dls_allocated_overs"]
    m.team2_dls_par_score = record["team2_dls_par_score"]


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


def _get_tournament(db, tournament_id: int) -> Tournament | None:
    return db.get(Tournament, tournament_id)


# ------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def index():
    """Setup / home page: list tournaments and create new ones."""
    db = _get_session()
    tournaments = db.query(Tournament).order_by(Tournament.created_at.desc()).all()
    rendered = render_template("index.html", tournaments=tournaments)
    db.close()
    return rendered


@app.route("/tournament/new", methods=["POST"])
def create_tournament():
    name = request.form.get("name", "").strip()
    quota_raw = request.form.get("format_quota", "20").strip()
    try:
        quota = float(quota_raw)
        if quota not in (20.0, 50.0):
            raise ValueError
    except ValueError:
        flash("Format quota must be 20 (T20I) or 50 (ODI).", "error")
        return redirect(url_for("index"))

    if not name:
        flash("Tournament name is required.", "error")
        return redirect(url_for("index"))

    db = _get_session()
    tournament = Tournament(name=name, format_quota=quota)
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    db.close()

    flash(f"Tournament '{name}' created.", "success")
    return redirect(url_for("add_match", tournament_id=tournament.id))


@app.route("/tournament/<int:tournament_id>")
def standings(tournament_id):
    db = _get_session()
    tournament = _get_tournament(db, tournament_id)
    if tournament is None:
        db.close()
        flash("Tournament not found.", "error")
        return redirect(url_for("index"))

    engine = _build_engine(tournament)
    table = engine.calculate_table()
    db.close()
    return render_template(
        "standings.html",
        tournament=tournament,
        table=table,
        format_quota=int(tournament.format_quota),
    )


@app.route("/tournament/<int:tournament_id>/matches")
def tournament_matches(tournament_id):
    """List a tournament's matches (to edit their details)."""
    db = _get_session()
    tournament = _get_tournament(db, tournament_id)
    if tournament is None:
        db.close()
        flash("Tournament not found.", "error")
        return redirect(url_for("index"))
    matches = tournament.matches
    rendered = render_template(
        "tournament_matches.html",
        tournament=tournament,
        matches=matches,
    )
    db.close()
    return rendered


@app.route("/tournament/<int:tournament_id>/add-match", methods=["GET", "POST"])
def add_match(tournament_id):
    db = _get_session()
    tournament = _get_tournament(db, tournament_id)
    if tournament is None:
        db.close()
        flash("Tournament not found.", "error")
        return redirect(url_for("index"))

    if request.method == "POST":
        record, errors = _parse_match_form(tournament.format_quota)
        if errors:
            db.close()
            for e in errors:
                flash(e, "error")
            return redirect(url_for("add_match", tournament_id=tournament_id))

        m = Match(tournament_id=tournament.id)
        _apply_record_to_match(record, m)
        db.add(m)
        db.commit()
        db.close()
        flash(f"Match logged: {record['team1']} vs {record['team2']}", "success")
        return redirect(url_for("standings", tournament_id=tournament_id))

    db.close()
    return render_template("add_match.html", tournament=tournament)


@app.route("/tournament/<int:tournament_id>/edit-match/<int:match_id>", methods=["GET", "POST"])
def edit_match(tournament_id, match_id):
    db = _get_session()
    tournament = _get_tournament(db, tournament_id)
    if tournament is None:
        db.close()
        flash("Tournament not found.", "error")
        return redirect(url_for("index"))

    m = db.get(Match, match_id)
    if m is None or m.tournament_id != tournament_id:
        db.close()
        flash("Match not found.", "error")
        return redirect(url_for("tournament_matches", tournament_id=tournament_id))

    if request.method == "POST":
        record, errors = _parse_match_form(tournament.format_quota)
        if errors:
            db.close()
            for e in errors:
                flash(e, "error")
            return redirect(url_for("edit_match", tournament_id=tournament_id, match_id=match_id))

        _apply_record_to_match(record, m)
        db.commit()
        db.close()
        flash(f"Match updated: {record['team1']} vs {record['team2']}", "success")
        return redirect(url_for("standings", tournament_id=tournament_id))

    record = _match_to_record(m)
    db.close()
    return render_template(
        "edit_match.html",
        tournament=tournament,
        match_json=json.dumps(record),
        match_id=match_id,
    )


@app.route("/tournament/<int:tournament_id>/delete", methods=["POST"])
def delete_tournament(tournament_id):
    db = _get_session()
    tournament = _get_tournament(db, tournament_id)
    if tournament is not None:
        db.delete(tournament)
        db.commit()
        db.close()
        flash(f"Tournament '{tournament.name}' deleted.", "success")
    else:
        db.close()
        flash("Tournament not found.", "error")
    return redirect(url_for("index"))


# ------------------------------------------------------------------

if __name__ == "__main__":
    print("Server is running")
    app.run(debug=True, host="127.0.0.1", port=5000)
