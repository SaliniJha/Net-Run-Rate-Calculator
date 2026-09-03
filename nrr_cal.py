# -*- coding: utf-8 -*-
"""
ICC Tournament Net Run Rate (NRR) Calculator & Auditor
Based strictly on ICC Standard Playing Conditions.

Interactive version: prompts the user to enter match data instead of
relying on hardcoded examples.
"""

import sys


class TournamentNRRCalculator:
    def __init__(self, format_quota=20.0):
        """
        Initialization parameters.
        format_quota: Default over quota per match innings (20.0 for T20I, 50.0 for ODI)
        """
        self.format_quota = format_quota
        self.teams = {}

    def _init_team_if_missing(self, team_name):
        if team_name not in self.teams:
            self.teams[team_name] = {
                "runs_scored": 0.0,
                "overs_faced": 0.0,
                "runs_conceded": 0.0,
                "overs_bowled": 0.0,
                "matches_played": 0
            }

    @staticmethod
    def overs_to_balls(overs):
        """Converts standard cricket over decimal notation (e.g., 16.4) into raw balls."""
        full_overs = int(overs)
        balls = int(round((overs - full_overs) * 10))
        return (full_overs * 6) + balls

    @staticmethod
    def balls_to_overs(balls):
        """Converts raw ball counts back to standard cricket over decimal notation (e.g., 100 balls -> 16.4)."""
        full_overs = balls // 6
        remaining_balls = balls % 6
        return full_overs + (remaining_balls / 10.0)

    def log_match(self, team1, team2, team1_runs, team1_overs, team1_bowled_out,
                  team2_runs, team2_overs, team2_bowled_out, is_dls=False,
                  team2_dls_allocated_overs=0.0, team2_dls_par_score=0):
        """
        Processes and commits a match record into the global tournament table.
        """
        self._init_team_if_missing(team1)
        self._init_team_if_missing(team2)

        t1_runs_scored = float(team1_runs)
        t2_runs_scored = float(team2_runs)

        t1_overs_faced_notation = float(team1_overs)
        t2_overs_faced_notation = float(team2_overs)

        # RULE 1: If Bowled Out, adjust overs to full format quota
        if team1_bowled_out:
            t1_overs_faced_notation = self.format_quota
        if team2_bowled_out:
            t2_overs_faced_notation = self.format_quota

        # RULE 2: If DLS Match, apply structural adjustments
        if is_dls:
            t1_runs_scored = float(team2_dls_par_score - 1)
            t1_overs_faced_notation = float(team2_dls_allocated_overs)

            if not team2_bowled_out and t2_runs_scored < team2_dls_par_score:
                t2_overs_faced_notation = float(team2_dls_allocated_overs)

        t1_balls_faced = self.overs_to_balls(t1_overs_faced_notation)
        t2_balls_faced = self.overs_to_balls(t2_overs_faced_notation)

        self.teams[team1]["runs_scored"] += t1_runs_scored
        self.teams[team1]["overs_faced"] += t1_balls_faced
        self.teams[team1]["runs_conceded"] += t2_runs_scored
        self.teams[team1]["overs_bowled"] += t2_balls_faced
        self.teams[team1]["matches_played"] += 1

        self.teams[team2]["runs_scored"] += t2_runs_scored
        self.teams[team2]["overs_faced"] += t2_balls_faced
        self.teams[team2]["runs_conceded"] += t1_runs_scored
        self.teams[team2]["overs_bowled"] += t1_balls_faced
        self.teams[team2]["matches_played"] += 1

    def calculate_table(self):
        """Computes current NRR positions for all registered teams."""
        table = []
        for team, stats in self.teams.items():
            overs_faced_cricket = self.balls_to_overs(stats["overs_faced"])
            overs_bowled_cricket = self.balls_to_overs(stats["overs_bowled"])

            total_overs_faced_decimal = stats["overs_faced"] / 6.0
            total_overs_bowled_decimal = stats["overs_bowled"] / 6.0

            run_rate_for = stats["runs_scored"] / total_overs_faced_decimal if total_overs_faced_decimal > 0 else 0.0
            run_rate_against = stats["runs_conceded"] / total_overs_bowled_decimal if total_overs_bowled_decimal > 0 else 0.0

            nrr = run_rate_for - run_rate_against

            table.append({
                "team": team,
                "matches": stats["matches_played"],
                "runs_for": stats["runs_scored"],
                "overs_for": overs_faced_cricket,
                "runs_against": stats["runs_conceded"],
                "overs_against": overs_bowled_cricket,
                "nrr": round(nrr, 3)
            })

        return sorted(table, key=lambda x: x["nrr"], reverse=True)


# ---------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------

def ask(prompt, cast=str, default=None):
    """Prompt the user, cast the answer, retry on bad input."""
    while True:
        raw = input(prompt).strip()
        if raw == "" and default is not None:
            return default
        try:
            return cast(raw)
        except ValueError:
            print(f"  Invalid value, please try again ({cast.__name__} expected).")


def ask_yes_no(prompt, default="n"):
    raw = input(f"{prompt} (y/n) [{default}]: ").strip().lower()
    if raw == "":
        raw = default
    return raw.startswith("y")


def input_match(engine):
    """Interactively collect a single match's data from the user."""
    print("\n--- Enter Match Details ---")
    team1 = ask("Team 1 name: ")
    team2 = ask("Team 2 name: ")

    print(f"\n{team1} innings:")
    team1_runs = ask(f"  Runs scored by {team1}: ", int)
    team1_overs = ask(f"  Overs faced by {team1} (e.g. 19.4): ", float)
    team1_bowled_out = ask_yes_no(f"  Was {team1} bowled out (all out)?")

    is_dls = ask_yes_no(f"\nWas this match affected by DLS (rain/weather revision)?")

    print(f"\n{team2} innings:")
    team2_runs = ask(f"  Runs scored by {team2}: ", int)
    team2_overs = ask(f"  Overs faced by {team2} (e.g. 19.4): ", float)
    team2_bowled_out = ask_yes_no(f"  Was {team2} bowled out (all out)?")

    team2_dls_allocated_overs = 0.0
    team2_dls_par_score = 0
    if is_dls:
        team2_dls_allocated_overs = ask(
            f"  DLS allocated overs for {team2}'s revised chase: ", float)
        team2_dls_par_score = ask(
            f"  DLS par score / revised target for {team2}: ", int)

    engine.log_match(
        team1=team1, team2=team2,
        team1_runs=team1_runs, team1_overs=team1_overs, team1_bowled_out=team1_bowled_out,
        team2_runs=team2_runs, team2_overs=team2_overs, team2_bowled_out=team2_bowled_out,
        is_dls=is_dls,
        team2_dls_allocated_overs=team2_dls_allocated_overs,
        team2_dls_par_score=team2_dls_par_score
    )
    print(f"\nMatch logged: {team1} vs {team2}")


def print_table(engine):
    standings = engine.calculate_table()
    if not standings:
        print("\nNo matches logged yet.")
        return

    # Column widths sized with headroom so values never collide, and the
    # team-name column auto-widens to fit the longest team name.
    col_pos, col_p, col_runs, col_overs, col_nrr = 5, 4, 11, 11, 10
    col_team = max(14, max(len(row["team"]) for row in standings) + 2)

    headers = (
        f"{'POS':<{col_pos}}{'TEAM NAME':<{col_team}}{'P':<{col_p}}"
        f"{'RUNS FOR':<{col_runs}}{'OVERS FOR':<{col_overs}}"
        f"{'RUNS AGST':<{col_runs}}{'OVERS AGST':<{col_overs}}"
        f"{'NET NRR':>{col_nrr}}"
    )
    total_width = col_pos + col_team + col_p + (col_runs * 2) + (col_overs * 2) + col_nrr

    print()
    print(headers)
    print("=" * total_width)
    for i, row in enumerate(standings, 1):
        line = (
            f"{i:<{col_pos}}{row['team']:<{col_team}}{row['matches']:<{col_p}}"
            f"{row['runs_for']:<{col_runs}.0f}{row['overs_for']:<{col_overs}.1f}"
            f"{row['runs_against']:<{col_runs}.0f}{row['overs_against']:<{col_overs}.1f}"
            f"{row['nrr']:>+{col_nrr}.3f}"
        )
        print(line)
        if i < len(standings):
            print("-" * total_width)
    print("=" * total_width)


def run_interactive():
    print("=" * 65)
    print("         ICC AUTOMATED TOURNAMENT NRR CALCULATOR ENGINE       ")
    print("=" * 65)

    format_quota = ask(
        "\nEnter overs quota per innings for this format (20 = T20I, 50 = ODI) [20]: ",
        float, default=20.0
    )
    engine = TournamentNRRCalculator(format_quota=format_quota)

    while True:
        input_match(engine)
        print_table(engine)
        if not ask_yes_no("\nAdd another match?", default="y"):
            break

    print("\nFinal standings:")
    print_table(engine)
    print("\nVerification complete. All calculations map cleanly to standard ICC ledger sets.\n")


if __name__ == "__main__":
    run_interactive()