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
  const session = new StudySession({ config, schedule, now });
  const acceptedChecks = Object.fromEntries(config.consent.checks.map((item) => [item.id, true]));
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

  for (const trial of schedule.trials) {
    mustThrow(() => session.submitRatings({}), "rate before playback");
    session.startPlayback(trial.stimulus_id, trial.wav_sha256);
    mustThrow(() => session.startPlayback(trial.stimulus_id, trial.wav_sha256), "replay while playing");
    session.finishPlayback(trial.stimulus_id);
    mustThrow(() => session.finishPlayback(trial.stimulus_id), "second playback end");
    session.submitRatings({
      retrospective_sense_0_100: 50,
      surprise_0_100: 50,
      coherence_0_100: 50,
      liking_0_100: 50,
      hear_again_0_100: 50,
    });
  }
  if (session.phase !== "complete") throw new Error(`${participantId} did not complete`);
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
  checked: ["consent-before-enrolment", "blank-metadata-rejected", "audio-check-before-enrolment", "single-play state", "ratings-after-ended", "frozen trial order", "exact CSV headers", "sample export"],
  participants: results,
  sample_export: sampleExport,
}, null, 2));
