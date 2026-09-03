# ICC Tournament NRR Calculator — Web App

A web application that calculates ICC Net Run Rate (NRR) standings for a cricket tournament from match results entered through a browser form. No terminal or code editing required after setup — just fill out the form and view standings.

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

3. **Start the server**:

   ```bash
   python app.py
   ```

4. **Open your browser** and go to:

   ```
   http://127.0.0.1:5000
   ```

That's it — no database setup, no build steps, no configuration files to edit.

## Project Structure

```
NRR/
├── nrr_cal.py          # Core TournamentNRRCalculator class (NRR math engine)
├── app.py              # Flask web app: routes, session storage, validation
├── requirements.txt    # Python dependencies (Flask)
├── README.md           # This file
├── templates/
│   ├── base.html       # Shared layout: header, nav, flash messages, footer
│   ├── index.html      # Setup page: choose tournament format (T20I / ODI)
│   ├── add_match.html  # Match entry form: team names, runs, overs, DLS fields
│   └── standings.html  # Interactive standings table (desktop + mobile views)
└── static/
    ├── style.css       # Custom CSS on top of Tailwind
    └── app.js          # Alpine.js components: form validation, DLS toggle
```

## Limitations

- **In-memory only**: Tournament data is stored in the server's memory (keyed by session). It resets when the server restarts or the session expires. There is no database or file persistence in v1.
- **Single-user sessions**: Each browser session maintains its own tournament independently. There is no shared state between users.
