# ICC Tournament NRR Calculator — Web App

A web application that calculates ICC Net Run Rate (NRR) standings for cricket tournaments from match results entered through a browser form. You can manage **multiple tournaments** at once (each with its own format and matches), view live NRR standings, and edit match details later. No terminal or code editing required after setup — just fill out the form and view standings.

## What NRR Is and Why It Matters

Net Run Rate (NRR) is the ICC's official tiebreaker for teams level on points in a tournament. It is calculated as the **run rate scored** across all of a team's matches minus the **run rate conceded** across all of those matches. A positive NRR means a team scores faster than it concedes; a negative NRR means the opposite.

Manual NRR calculation is error-prone because cricket's over notation isn't decimal (e.g. 16.4 means 16 overs and 4 balls, not 16.40), bowled-out innings are capped at the full format quota regardless of actual balls used, and DLS-affected matches use adjusted par figures instead of the actual score.

## Rules Implemented

This tool encodes three ICC Standard Playing Conditions:

1. **Ball-level aggregation**: Overs are converted to raw ball counts internally for all arithmetic. This avoids rounding errors that arise from cricket's non-decimal over notation (e.g. 16.4 is not a valid decimal — it means 16×6+4 = 100 balls).

2. **Bowled-out rule**: When a team is bowled out (all out), their overs faced are recorded as the full format quota (20 for T20I, 50 for ODI) rather than the actual balls they used. This follows ICC regulation — a team that is all out has not "used" fewer overs; the innings simply ended early.

3. **DLS-affected matches**: In matches affected by the Duckworth-Lewis-Stern method, the team batting first has their runs set to the revised target minus one and their overs set to the DLS-allocated overs, per ICC Standard Playing Conditions for rain-affected matches.

## Who It's For

- Tournament organizers and cricket league/club administrators
- Fantasy league or local tournament scorers
- Students or hobbyists who want to verify NRR standings without spreadsheet errors

## How to Run It

The app stores tournaments and matches in a **PostgreSQL database** (e.g. a free [Neon](https://neon.tech) serverless Postgres instance). The connection string is read from the `.env` file.

1. **Create a virtual environment** (recommended):

   ```bash
   python -m venv venv
   ```

   On Windows:
   ```bash
   venv\Scripts\activate
   ```

   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the database** — create a `.env` file in the project root with your connection string:

   ```
   DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
   ```

   The tables are created automatically the first time the app starts, so no manual schema setup is needed.

4. **Start the server**:

   ```bash
   python app.py
   ```

5. **Open your browser** and go to:

   ```
   http://127.0.0.1:5000
   ```

On the home page you can create a new tournament (name + format) and see a list of existing tournaments. Click a tournament to view its standings, or its **Edit Matches** button to review and correct individual match details.

## Project Structure

```
NRR/
├── nrr_cal.py          # Core TournamentNRRCalculator class (NRR math engine, unchanged)
├── app.py              # Flask app: routes, PostgreSQL models, validation
├── requirements.txt    # Python dependencies (Flask, SQLAlchemy, psycopg2, dotenv)
├── .env                # Database connection string (DATABASE_URL) — not committed
├── README.md           # This file
├── templates/
│   ├── base.html        # Shared layout: header, nav, flash messages, footer
│   ├── index.html       # Home: create a tournament + list existing tournaments
│   ├── _match_form.html # Reusable match entry/editing form (team runs, overs, DLS)
│   ├── add_match.html   # Add a match to a specific tournament
│   ├── edit_match.html  # Edit an existing match (pre-filled form)
│   ├── standings.html   # Per-tournament NRR standings table
│   └── tournament_matches.html  # List a tournament's matches with edit links
└── static/
    ├── style.css       # Custom CSS on top of Tailwind
    └── app.js          # Alpine.js components: form validation, DLS toggle
```

## Data Model

Two tables are managed by the app:

- **tournaments** — each tournament's name and over quota (20 for T20I, 50 for ODI).
- **matches** — one row per match, linked to a tournament, holding both teams' runs, overs, bowled-out flags, and DLS fields.

Matches are robust to editing: change a match and the standings recalculate automatically.

## Limitations

- **Single Postgres database**: All tournaments share the configured database; there is no multi-tenant separation or per-user access control.
- **Live queries**: Every page render reads straight from the database (a fresh SQLAlchemy session per request). For a busy multi-user deployment you may want connection pooling and caching.
