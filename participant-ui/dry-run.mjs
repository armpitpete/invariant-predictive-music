import fs from "node:fs";
import path from "node:path";
import { StudySession } from "./protocol.mjs";

const root = path.resolve(process.argv[2] ?? "participant-web");
const config = JSON.parse(fs.readFileSync(path.join(root, "config.json"), "utf8"));
let tick = 0;
const now = () => `2026-08-18T10:${String(Math.floor(tick / 60)).padStart(2, "0")}:${String(tick++ % 60).padStart(2, "0")}Z`;

function mustThrow(fn, label) {
  let threw = false;
  try { fn(); } catch { threw = true; }
  if (!threw) throw new Error(`expected rejection: ${label}`);
}

const results = [];
let sampleExport = null;
for (const participantId of config.participant_ids) {
  const schedule = JSON.parse(fs.readFileSync(path.join(root, "schedules", `${participantId}.json`), "utf8"));
  const acceptedChecks = Object.fromEntries(config.consent.checks.map((item) => [item.id, true]));

  const rejectedStart = new StudySession({ config, schedule, now });
  rejectedStart.acceptConsent({
    checks: acceptedChecks,
    headphones: true,
    musicMakingYears: 0,
    formalTrainingYears: 0,
  });
  rejectedStart.completeAudioCheck();
  rejectedStart.beginMainBlock();
  rejectedStart.failPlayback("synthetic browser rejection before actual media start");
  if (rejectedStart.enrolledAt !== null) throw new Error(`${participantId} enrolled after rejected pre-start playback`);
  if (rejectedStart.audit.some((item) => item.event === "main_block_started" || item.event === "playback_started")) {
    throw new Error(`${participantId} logged playback start after rejected pre-start playback`);
  }

  let session = new StudySession({ config, schedule, now });
  mustThrow(() => session.beginMainBlock(), "begin before consent/audio check");
  mustThrow(() => session.acceptConsent({
    checks: acceptedChecks,
    headphones: true,
    musicMakingYears: "",
    formalTrainingYears: "",
  }), "blank participant metadata");
  session.acceptConsent({
    checks: acceptedChecks,
    headphones: true,
    musicMakingYears: 0,
    formalTrainingYears: 0,
  });
  session.completeAudioCheck();
  session.beginMainBlock();
  if (session.enrolledAt !== null) throw new Error(`${participantId} enrolled before trial-1 playback`);

  for (const trial of schedule.trials) {
    mustThrow(() => session.submitRatings({}), "rate before playback");
    session.startPlayback(trial.stimulus_id, trial.wav_sha256);
    if (trial.trial === 1 && session.enrolledAt === null) throw new Error(`${participantId} did not enrol when trial-1 playback started`);
    mustThrow(() => session.startPlayback(trial.stimulus_id, trial.wav_sha256), "replay while playing");

    if (trial.trial === 1) {
      session = StudySession.restore({ config, schedule, snapshot: session.snapshotObject(), now });
      if (session.phase !== "playing") throw new Error(`${participantId} active playback did not survive saved-state restore`);
      mustThrow(() => session.startPlayback(trial.stimulus_id, trial.wav_sha256), "replay after playback-state restore");
    }

    session.finishPlayback(trial.stimulus_id);
    mustThrow(() => session.finishPlayback(trial.stimulus_id), "second playback end");

    if (trial.trial === 1) {
      session = StudySession.restore({ config, schedule, snapshot: session.snapshotObject(), now });
      if (session.phase !== "rating") throw new Error(`${participantId} rating state did not survive restore`);
      mustThrow(() => session.startPlayback(trial.stimulus_id, trial.wav_sha256), "replay after rating-state restore");
    }

    session.submitRatings({
      retrospective_sense_0_100: 50,
      surprise_0_100: 50,
      coherence_0_100: 50,
      liking_0_100: 50,
      hear_again_0_100: 50,
    });

    if (trial.trial === 1) {
      session = StudySession.restore({ config, schedule, snapshot: session.snapshotObject(), now });
      if (session.phase !== "trial-ready") throw new Error(`${participantId} between-trial state did not survive restore`);
      if (session.currentTrialIndex !== 1) throw new Error(`${participantId} restored trial index drifted`);
    }
  }
  if (session.phase !== "complete") throw new Error(`${participantId} did not complete`);
  session = StudySession.restore({ config, schedule, snapshot: session.snapshotObject(), now });
  mustThrow(() => session.startPlayback(schedule.trials[0].stimulus_id, schedule.trials[0].wav_sha256), "restart after completion");
  const exported = session.exportObject();
  if (exported.responses.length !== 12) throw new Error(`${participantId} export row count drifted`);
  const expected = schedule.trials.map((item) => item.stimulus_id).join(",");
  const actual = exported.responses.map((item) => item.stimulus_id).join(",");
  if (expected !== actual) throw new Error(`${participantId} export order drifted`);
  if (!exported.responses_csv.startsWith(config.response_schema_header + "\r\n")) throw new Error(`${participantId} response CSV header drifted`);
  if (!exported.participant_csv.startsWith(config.participant_schema_header + "\r\n")) throw new Error(`${participantId} participant CSV header drifted`);
  if (participantId === "P001") sampleExport = exported;
  results.push({ participant_id: participantId, trials: exported.responses.length, passed: true });
}

if (!sampleExport) throw new Error("P001 sample export was not produced");

console.log(JSON.stringify({
  gate: "participant JS state-machine dry-run",
  passed: results.every((item) => item.passed),
  participant_count: results.length,
  total_trial_count: results.reduce((sum, item) => sum + item.trials, 0),
  checked: [
    "consent-before-main-block",
    "blank-metadata-rejected",
    "audio-check-before-main-block",
    "rejected-pre-start-playback-remains-unenrolled",
    "enrolment-on-first-playback",
    "single-play state",
    "ratings-after-ended",
    "playback-state-restore-blocks-replay",
    "rating-state-restore-blocks-replay",
    "between-trial-state-restore",
    "completion-state-blocks-restart",
    "frozen trial order",
    "exact CSV headers",
    "sample export",
  ],
  participants: results,
  sample_export: sampleExport,
}, null, 2));
