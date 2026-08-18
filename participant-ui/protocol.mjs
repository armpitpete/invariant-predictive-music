export const SESSION_EXPORT_VERSION = 1;

const RATING_FIELDS = [
  "retrospective_sense_0_100",
  "surprise_0_100",
  "coherence_0_100",
  "liking_0_100",
  "hear_again_0_100",
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function finiteNumber(value, name) {
  assert(
    value !== null && value !== undefined && String(value).trim() !== "",
    `${name} is required`,
  );
  const number = Number(value);
  assert(Number.isFinite(number), `${name} must be numeric`);
  assert(number >= 0 && number <= 100, `${name} must be between 0 and 100`);
  return number;
}

export function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

export function rowsToCsv(header, rows) {
  const lines = [header.join(",")];
  for (const row of rows) lines.push(header.map((field) => csvEscape(row[field])).join(","));
  return `${lines.join("\r\n")}\r\n`;
}

export class StudySession {
  constructor({ config, schedule, now = () => new Date().toISOString() }) {
    assert(config && schedule, "config and schedule are required");
    assert(config.participant_ids.includes(schedule.participant_id), "participant ID is not in frozen enrolment set");
    assert(schedule.trials.length === 12, "frozen schedule must contain exactly 12 trials");
    this.config = config;
    this.schedule = schedule;
    this.now = now;
    this.phase = "consent";
    this.consent = null;
    this.metadata = null;
    this.audioCheckCompletedAt = null;
    this.enrolledAt = null;
    this.currentTrialIndex = 0;
    this.playback = null;
    this.responses = [];
    this.audit = [];
    this.playbackFailure = false;
    this.withdrawn = false;
    this.completedAt = null;
  }

  get participantId() { return this.schedule.participant_id; }
  get currentTrial() { return this.schedule.trials[this.currentTrialIndex] ?? null; }

  acceptConsent({ checks, headphones, musicMakingYears, formalTrainingYears }) {
    assert(this.phase === "consent", "consent is already locked");
    for (const item of this.config.consent.checks) {
      assert(checks?.[item.id] === true, `consent item not accepted: ${item.id}`);
    }
    assert(headphones === true, "headphones/quiet-setting confirmation is required");
    const music = finiteNumber(musicMakingYears, "music-making years");
    const training = finiteNumber(formalTrainingYears, "formal training years");
    const at = this.now();
    this.consent = {
      version: this.config.consent.version,
      accepted_at_utc: at,
      checks: Object.fromEntries(this.config.consent.checks.map((item) => [item.id, true])),
      headphones_quiet_setting: true,
    };
    this.metadata = {
      music_making_years: music,
      formal_music_training_years: training,
    };
    this.phase = "audio-check";
    this.audit.push({ event: "consent_locked", at });
  }

  completeAudioCheck() {
    assert(this.phase === "audio-check", "audio check is not available now");
    const at = this.now();
    this.audioCheckCompletedAt = at;
    this.phase = "ready";
    this.audit.push({ event: "audio_check_completed", at });
  }

  beginMainBlock() {
    assert(this.phase === "ready", "consent and audio check must complete before enrolment");
    const at = this.now();
    this.enrolledAt = at;
    this.phase = "trial-ready";
    this.audit.push({ event: "main_block_started", at, trial: 1 });
  }

  startPlayback(stimulusId, verifiedSha256) {
    assert(this.phase === "trial-ready", "playback can start only once for the current trial");
    const trial = this.currentTrial;
    assert(trial && stimulusId === trial.stimulus_id, "stimulus does not match frozen schedule");
    assert(verifiedSha256 === trial.wav_sha256, "stimulus bytes do not match frozen SHA-256");
    const at = this.now();
    this.playback = { stimulus_id: stimulusId, started_at_utc: at, ended_at_utc: null };
    this.phase = "playing";
    this.audit.push({ event: "playback_started", at, trial: trial.trial, stimulus_id: stimulusId, wav_sha256: verifiedSha256 });
  }

  finishPlayback(stimulusId) {
    assert(this.phase === "playing", "ratings cannot open before playback starts");
    assert(this.playback?.stimulus_id === stimulusId, "playback end does not match current stimulus");
    const at = this.now();
    this.playback.ended_at_utc = at;
    this.phase = "rating";
    this.audit.push({ event: "playback_completed", at, trial: this.currentTrial.trial, stimulus_id: stimulusId });
  }

  submitRatings(values) {
    assert(this.phase === "rating", "ratings are accepted only after playback ends");
    const trial = this.currentTrial;
    const row = {
      participant_id: this.participantId,
      trial: trial.trial,
      stimulus_id: trial.stimulus_id,
    };
    for (const field of RATING_FIELDS) {
      const value = Number(values?.[field]);
      assert(Number.isInteger(value) && value >= 0 && value <= 100, `${field} must be an integer 0-100`);
      row[field] = value;
    }
    const at = this.now();
    this.responses.push(row);
    this.audit.push({ event: "ratings_submitted", at, trial: trial.trial, stimulus_id: trial.stimulus_id });
    this.playback = null;
    this.currentTrialIndex += 1;
    if (this.currentTrialIndex === this.schedule.trials.length) {
      this.phase = "complete";
      this.completedAt = at;
      this.audit.push({ event: "main_block_completed", at });
    } else {
      this.phase = "trial-ready";
    }
  }

  failPlayback(reason) {
    assert(this.phase === "playing" || this.phase === "trial-ready", "playback failure can only occur in the main block");
    const at = this.now();
    this.playbackFailure = true;
    this.phase = "technical-failure";
    this.audit.push({ event: "technical_playback_failure", at, trial: this.currentTrial?.trial ?? null, reason: String(reason) });
  }

  withdraw() {
    assert(!["complete", "technical-failure", "withdrawn"].includes(this.phase), "session is already terminal");
    const at = this.now();
    this.withdrawn = true;
    this.phase = "withdrawn";
    this.audit.push({ event: "participant_stopped", at, trial: this.currentTrial?.trial ?? null });
  }

  exportObject() {
    assert(this.consent, "no consent record exists");
    const completed = this.phase === "complete";
    const participantRow = {
      participant_id: this.participantId,
      counterbalance_group: this.schedule.counterbalance_group,
      music_making_years: this.metadata.music_making_years,
      formal_music_training_years: this.metadata.formal_music_training_years,
      completed_main_block: completed ? "true" : "false",
      playback_failure: this.playbackFailure ? "true" : "false",
      duplicate_participation: "",
      record_usable: "",
      exclusion_reason: "",
    };
    const responseHeader = this.config.response_schema_header.split(",");
    const participantHeader = this.config.participant_schema_header.split(",");
    return {
      export_version: SESSION_EXPORT_VERSION,
      participant_id: this.participantId,
      frozen_listener_artifact: this.config.frozen_listener_artifact,
      source_schedule_sha256: this.schedule.source_schedule_sha256,
      consent: this.consent,
      audio_check_completed_at_utc: this.audioCheckCompletedAt,
      enrolled_at_utc: this.enrolledAt,
      completed_at_utc: this.completedAt,
      terminal_state: this.phase,
      participant: participantRow,
      responses: this.responses.map((row) => ({ ...row })),
      audit: this.audit.map((item) => ({ ...item })),
      participant_csv: rowsToCsv(participantHeader, [participantRow]),
      responses_csv: rowsToCsv(responseHeader, this.responses),
    };
  }
}
