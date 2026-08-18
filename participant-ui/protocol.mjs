export const SESSION_EXPORT_VERSION = 1;
export const SESSION_SNAPSHOT_VERSION = 1;

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

function sameFrozenArtifact(left, right) {
  return JSON.stringify(left) === JSON.stringify(right);
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

  static restore({ config, schedule, snapshot, now = () => new Date().toISOString() }) {
    assert(snapshot?.snapshot_version === SESSION_SNAPSHOT_VERSION, "saved study state version is invalid");
    assert(snapshot.participant_id === schedule.participant_id, "saved participant ID does not match schedule");
    assert(snapshot.source_schedule_sha256 === schedule.source_schedule_sha256, "saved schedule provenance does not match");
    assert(sameFrozenArtifact(snapshot.frozen_listener_artifact, config.frozen_listener_artifact), "saved listener artifact does not match");
    assert(
      ["consent", "audio-check", "ready", "trial-ready", "playing", "rating", "complete", "technical-failure", "withdrawn"].includes(snapshot.phase),
      "saved study phase is invalid",
    );
    assert(Number.isInteger(snapshot.current_trial_index), "saved trial index is invalid");
    assert(snapshot.current_trial_index >= 0 && snapshot.current_trial_index <= schedule.trials.length, "saved trial index escapes schedule");
    assert(Array.isArray(snapshot.responses), "saved responses are invalid");
    assert(snapshot.responses.length === snapshot.current_trial_index, "saved response count does not match trial index");

    for (let index = 0; index < snapshot.responses.length; index += 1) {
      const response = snapshot.responses[index];
      const trial = schedule.trials[index];
      assert(response.participant_id === schedule.participant_id, "saved response participant drifted");
      assert(response.trial === trial.trial, "saved response trial number drifted");
      assert(response.stimulus_id === trial.stimulus_id, "saved response stimulus order drifted");
      for (const field of RATING_FIELDS) {
        assert(Number.isInteger(response[field]) && response[field] >= 0 && response[field] <= 100, `saved ${field} is invalid`);
      }
    }

    if (snapshot.phase === "complete") {
      assert(snapshot.current_trial_index === schedule.trials.length, "completed saved state has incomplete trials");
    }
    if (snapshot.phase === "playing" || snapshot.phase === "rating") {
      const trial = schedule.trials[snapshot.current_trial_index];
      assert(trial, "saved active trial is missing");
      assert(snapshot.playback?.stimulus_id === trial.stimulus_id, "saved playback stimulus drifted");
    }

    const session = new StudySession({ config, schedule, now });
    session.phase = snapshot.phase;
    session.consent = snapshot.consent ?? null;
    session.metadata = snapshot.metadata ?? null;
    session.audioCheckCompletedAt = snapshot.audio_check_completed_at_utc ?? null;
    session.enrolledAt = snapshot.enrolled_at_utc ?? null;
    session.currentTrialIndex = snapshot.current_trial_index;
    session.playback = snapshot.playback ? { ...snapshot.playback } : null;
    session.responses = snapshot.responses.map((row) => ({ ...row }));
    session.audit = Array.isArray(snapshot.audit) ? snapshot.audit.map((item) => ({ ...item })) : [];
    session.playbackFailure = snapshot.playback_failure === true;
    session.withdrawn = snapshot.withdrawn === true;
    session.completedAt = snapshot.completed_at_utc ?? null;
    return session;
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
    assert(this.phase === "ready", "consent and audio check must complete before the main block is armed");
    const at = this.now();
    this.phase = "trial-ready";
    this.audit.push({ event: "main_block_armed", at, trial: 1 });
  }

  startPlayback(stimulusId, verifiedSha256) {
    assert(this.phase === "trial-ready", "playback can start only once for the current trial");
    const trial = this.currentTrial;
    assert(trial && stimulusId === trial.stimulus_id, "stimulus does not match frozen schedule");
    assert(verifiedSha256 === trial.wav_sha256, "stimulus bytes do not match frozen SHA-256");
    const at = this.now();
    if (this.currentTrialIndex === 0 && this.enrolledAt === null) {
      this.enrolledAt = at;
      this.audit.push({ event: "main_block_started", at, trial: 1 });
    }
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

  snapshotObject() {
    return {
      snapshot_version: SESSION_SNAPSHOT_VERSION,
      participant_id: this.participantId,
      frozen_listener_artifact: this.config.frozen_listener_artifact,
      source_schedule_sha256: this.schedule.source_schedule_sha256,
      phase: this.phase,
      consent: this.consent,
      metadata: this.metadata,
      audio_check_completed_at_utc: this.audioCheckCompletedAt,
      enrolled_at_utc: this.enrolledAt,
      current_trial_index: this.currentTrialIndex,
      playback: this.playback,
      responses: this.responses,
      audit: this.audit,
      playback_failure: this.playbackFailure,
      withdrawn: this.withdrawn,
      completed_at_utc: this.completedAt,
    };
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
