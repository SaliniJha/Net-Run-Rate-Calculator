/**
 * Alpine.js components for the ICC NRR Calculator web app.
 */

function setupForm() {
  return {
    form: {
      name: '',
      format_quota: '20',
    },
  };
}

function matchForm(initial) {
  const defaults = {
    team1: '',
    team1_runs: '',
    team1_overs: '',
    team1_bowled_out: false,
    team2: '',
    team2_runs: '',
    team2_overs: '',
    team2_bowled_out: false,
    is_dls: false,
    team2_dls_allocated_overs: '',
    team2_dls_par_score: '',
  };
  const data = initial && typeof initial === 'object' ? { ...defaults, ...initial } : defaults;
  return {
    form: {
      team1: data.team1,
      team1_runs: data.team1_runs,
      team1_overs: data.team1_overs,
      team1_bowled_out: !!data.team1_bowled_out,
      team2: data.team2,
      team2_runs: data.team2_runs,
      team2_overs: data.team2_overs,
      team2_bowled_out: !!data.team2_bowled_out,
      is_dls: !!data.is_dls,
      team2_dls_allocated_overs: data.team2_dls_allocated_overs,
      team2_dls_par_score: data.team2_dls_par_score,
    },
    errors: {},
    submitting: false,

    validate() {
      this.errors = {};
      if (!this.form.team1.trim()) this.errors.team1 = 'Team 1 name is required.';
      if (!this.form.team2.trim()) this.errors.team2 = 'Team 2 name is required.';
      if (this.form.team1_runs === '' || this.form.team1_runs === null) {
        this.errors.team1_runs = 'Runs are required.';
      }
      if (this.form.team1_overs === '' || this.form.team1_overs === null) {
        this.errors.team1_overs = 'Overs are required.';
      } else if (parseFloat(this.form.team1_overs) < 0 || parseFloat(this.form.team1_overs) > 50) {
        this.errors.team1_overs = 'Overs must be between 0 and 50.';
      }
      if (this.form.team2_runs === '' || this.form.team2_runs === null) {
        this.errors.team2_runs = 'Runs are required.';
      }
      if (this.form.team2_overs === '' || this.form.team2_overs === null) {
        this.errors.team2_overs = 'Overs are required.';
      } else if (parseFloat(this.form.team2_overs) < 0 || parseFloat(this.form.team2_overs) > 50) {
        this.errors.team2_overs = 'Overs must be between 0 and 50.';
      }
      if (this.form.is_dls) {
        if (this.form.team2_dls_allocated_overs === '' || this.form.team2_dls_allocated_overs === null) {
          this.errors.team2_dls_allocated_overs = 'DLS allocated overs are required.';
        }
        if (this.form.team2_dls_par_score === '' || this.form.team2_dls_par_score === null) {
          this.errors.team2_dls_par_score = 'DLS par score is required.';
        }
      }
      return Object.keys(this.errors).length === 0;
    },
  };
}
