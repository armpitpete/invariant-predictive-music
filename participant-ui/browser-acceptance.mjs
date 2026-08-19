import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { chromium } from "playwright";

const webRoot = path.resolve(process.argv[2] ?? "participant-web");
const outputDir = path.resolve(process.argv[3] ?? "participant-browser-acceptance");
fs.mkdirSync(outputDir, { recursive: true });

const RATING_FIELDS = [
  "retrospective_sense_0_100",
  "surprise_0_100",
  "coherence_0_100",
  "liking_0_100",
  "hear_again_0_100",
];
const FORBIDDEN_LABELS = ["predictable", "unstructured-surprise"];
const FROZEN_SEEDS = [
  "2026081804", "2026081805", "2026081808", "2026081810",
  "2026081812", "2026081813", "2026081814", "2026081817",
  "2026081819", "2026081822", "2026081827", "2026081828",
];

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function readJson(filename) {
  return JSON.parse(fs.readFileSync(filename, "utf8"));
}

function contentType(filename) {
  switch (path.extname(filename).toLowerCase()) {
    case ".html": return "text/html; charset=utf-8";
    case ".js":
    case ".mjs": return "text/javascript; charset=utf-8";
    case ".json": return "application/json; charset=utf-8";
    case ".css": return "text/css; charset=utf-8";
    case ".csv": return "text/csv; charset=utf-8";
    case ".wav": return "audio/wav";
    default: return "application/octet-stream";
  }
}

function createStaticServer(root) {
  const server = http.createServer((request, response) => {
    try {
      const url = new URL(request.url, "http://127.0.0.1");
      const relative = decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname);
      const filename = path.resolve(root, `.${relative}`);
      assert(filename === root || filename.startsWith(`${root}${path.sep}`), "path traversal rejected");
      const data = fs.readFileSync(filename);
      response.writeHead(200, {
        "Content-Type": contentType(filename),
        "Content-Length": data.length,
        "Cache-Control": "no-store",
      });
      response.end(data);
    } catch (error) {
      response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      response.end("not found\n");
    }
  });
  return server;
}

function listTextFiles(root) {
  const result = [];
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) result.push(...listTextFiles(full));
    else if (!entry.name.endsWith(".wav")) result.push(full);
  }
  return result;
}

function assertNoConditionLeak(text, label) {
  const lowered = text.toLowerCase();
  for (const forbidden of FORBIDDEN_LABELS) {
    assert(!lowered.includes(forbidden), `${label} leaks condition label ${forbidden}`);
  }
  for (const seed of FROZEN_SEEDS) {
    assert(!text.includes(seed), `${label} leaks frozen episode seed ${seed}`);
  }
}

function assertNoMappingKeys(value, label, location = "$") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoMappingKeys(item, label, `${location}[${index}]`));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, child] of Object.entries(value)) {
    assert(!/^condition(?:_|$)/i.test(key), `${label} exposes condition mapping key ${location}.${key}`);
    assert(!/^(?:episode_)?seed(?:_|$)/i.test(key), `${label} exposes episode-seed mapping key ${location}.${key}`);
    assertNoMappingKeys(child, label, `${location}.${key}`);
  }
}

function chooseGroupSchedules() {
  const schedulesDir = path.join(webRoot, "schedules");
  const schedules = fs.readdirSync(schedulesDir)
    .filter((name) => /^P\d{3}\.json$/.test(name))
    .map((name) => readJson(path.join(schedulesDir, name)))
    .sort((a, b) => a.participant_id.localeCompare(b.participant_id));
  const byGroup = new Map();
  for (const schedule of schedules) {
    if (!byGroup.has(schedule.counterbalance_group)) byGroup.set(schedule.counterbalance_group, schedule);
  }
  assert([...byGroup.keys()].sort().join(",") === "1,2,3", "expected exactly counterbalance groups 1,2,3");
  const selected = [byGroup.get(1), byGroup.get(2), byGroup.get(3)];
  const union = new Set(selected.flatMap((schedule) => schedule.trials.map((trial) => trial.stimulus_id)));
  assert(union.size === 36, "one synthetic session per group must cover all 36 opaque stimuli exactly once");
  assert(selected.every((schedule) => schedule.trials.length === 12), "each selected schedule must contain 12 trials");
  return selected;
}

function auditDurations(exported) {
  const starts = new Map();
  const durations = [];
  for (const event of exported.audit) {
    if (event.event === "playback_started") starts.set(event.trial, Date.parse(event.at));
    if (event.event === "playback_completed") {
      const start = starts.get(event.trial);
      assert(Number.isFinite(start), `trial ${event.trial} has no playback_start audit event`);
      durations.push((Date.parse(event.at) - start) / 1000);
    }
  }
  assert(durations.length === 12, "export must contain 12 completed playback intervals");
  for (const seconds of durations) {
    assert(seconds >= 30, `playback ended implausibly early (${seconds.toFixed(3)} s)`);
    assert(seconds <= 50, `playback took implausibly long (${seconds.toFixed(3)} s)`);
  }
  return durations;
}

async function runSyntheticSession(browser, baseUrl, schedule) {
  const context = await browser.newContext({ acceptDownloads: true });
  const page = await context.newPage();
  page.setDefaultTimeout(60_000);
  const requestedStimuli = [];
  page.on("response", (response) => {
    const match = new URL(response.url()).pathname.match(/\/stimuli\/(stim-[a-f0-9]+\.wav)$/);
    if (match && response.ok()) requestedStimuli.push(match[1]);
  });

  await page.addInitScript(() => {
    globalThis.__ipmDirectGestureTurn = false;
    globalThis.__ipmMediaPlayAudit = [];
    document.addEventListener("click", (event) => {
      if (!event.isTrusted) return;
      globalThis.__ipmDirectGestureTurn = true;
      setTimeout(() => { globalThis.__ipmDirectGestureTurn = false; }, 0);
    }, true);
    const originalPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function (...args) {
      const record = {
        same_click_turn: globalThis.__ipmDirectGestureTurn === true,
        user_activation_active: globalThis.navigator?.userActivation?.isActive ?? null,
        src: this.src,
      };
      globalThis.__ipmMediaPlayAudit.push(record);
      if (!record.same_click_turn) {
        return Promise.reject(new DOMException(
          "Synthetic WebKit-style gate: audible media play() was not called directly in the trusted click task.",
          "NotAllowedError",
        ));
      }
      return originalPlay.apply(this, args);
    };
  });

  await page.goto(`${baseUrl}/?participant=${schedule.participant_id}`, { waitUntil: "networkidle" });
  assert(await page.evaluate(() => Boolean(globalThis.crypto?.subtle)), "browser WebCrypto is unavailable");
  assert((await page.locator("audio").count()) === 0, "native audio controls unexpectedly exposed");

  const config = readJson(path.join(webRoot, "config.json"));
  assertNoMappingKeys(config, "participant config");
  assertNoMappingKeys(schedule, `${schedule.participant_id} schedule`);
  for (const item of config.consent.checks) await page.locator(`#consent-${item.id}`).check();
  await page.locator("#headphones").check();
  await page.locator("#music-years").fill("3.5");
  await page.locator("#training-years").fill("1.5");
  await page.locator("#consent-continue").click();

  await page.locator("#play-check").click();
  await page.locator("#comfortable").waitFor({ state: "attached" });
  await page.waitForFunction(() => !document.querySelector("#comfortable")?.disabled);
  await page.locator("#comfortable").check();
  await page.locator("#begin").click();

  const wallDurations = [];
  for (let index = 0; index < schedule.trials.length; index += 1) {
    const trial = schedule.trials[index];
    await page.waitForFunction(() => document.querySelector("#play-status")?.textContent === "Ready");
    assert(await page.locator("#play-stimulus").isEnabled(), `${schedule.participant_id} trial ${trial.trial} play button unavailable after frozen-audio verification`);
    const started = Date.now();
    await page.locator("#play-stimulus").click();
    try {
      await page.waitForFunction(() => document.querySelector("#play-status")?.textContent === "Playing…", null, { timeout: 5_000 });
    } catch (error) {
      const diagnostics = await page.evaluate(() => ({
        status: document.querySelector("#play-status")?.textContent ?? null,
        body: document.body.innerText,
        media_play_audit: globalThis.__ipmMediaPlayAudit ?? [],
      }));
      throw new Error(`${schedule.participant_id} trial ${trial.trial} did not start playback: ${JSON.stringify(diagnostics)}`, { cause: error });
    }
    await page.locator("#ratings").waitFor({ state: "visible", timeout: 50_000 });
    const elapsed = (Date.now() - started) / 1000;
    wallDurations.push(elapsed);
    assert(elapsed >= 30, `${schedule.participant_id} trial ${trial.trial} reached ratings too early (${elapsed.toFixed(3)} s)`);
    assert(elapsed <= 50, `${schedule.participant_id} trial ${trial.trial} playback exceeded acceptance window (${elapsed.toFixed(3)} s)`);

    for (let fieldIndex = 0; fieldIndex < RATING_FIELDS.length; fieldIndex += 1) {
      const field = RATING_FIELDS[fieldIndex];
      const value = 20 + ((schedule.counterbalance_group * 7 + trial.trial * 3 + fieldIndex) % 61);
      await page.locator(`#${field}`).evaluate((element, nextValue) => {
        element.value = String(nextValue);
        element.dispatchEvent(new Event("input", { bubbles: true }));
      }, value);
    }
    assert(await page.locator("#submit-ratings").isEnabled(), `${schedule.participant_id} ratings did not unlock after all sliders were touched`);
    await page.locator("#submit-ratings").click();
  }

  await page.getByRole("heading", { name: "Study complete" }).waitFor();
  const mediaPlayAudit = await page.evaluate(() => globalThis.__ipmMediaPlayAudit ?? []);
  assert(mediaPlayAudit.length === 12, "browser must call HTMLMediaElement.play exactly once per trial");
  assert(mediaPlayAudit.every((item) => item.same_click_turn === true), "media play escaped the direct trusted-click task");

  const downloadPromise = page.waitForEvent("download");
  await page.locator("#download-export").click();
  const download = await downloadPromise;
  const exportPath = path.join(outputDir, `${schedule.participant_id}-synthetic-export.json`);
  await download.saveAs(exportPath);
  const exportedText = fs.readFileSync(exportPath, "utf8");
  assertNoConditionLeak(exportedText, `${schedule.participant_id} export`);
  const exported = JSON.parse(exportedText);
  assertNoMappingKeys(exported, `${schedule.participant_id} export`);

  assert(exported.participant_id === schedule.participant_id, "export participant ID drifted");
  assert(exported.terminal_state === "complete", "synthetic session did not export complete state");
  assert(Boolean(exported.enrolled_at_utc), "main-block boundary was not recorded in synthetic export");
  assert(exported.responses.length === 12, "synthetic export must contain exactly 12 responses");
  assert(exported.responses.map((row) => row.stimulus_id).join(",") === schedule.trials.map((trial) => trial.stimulus_id).join(","), "export response order drifted from frozen schedule");
  assert(exported.participant.counterbalance_group === schedule.counterbalance_group, "export counterbalance group drifted");
  assert(exported.participant.completed_main_block === "true", "completed_main_block is not true");
  assert(exported.participant.playback_failure === "false", "synthetic session reports playback failure");
  assert(exported.participant.duplicate_participation === "", "participant UI must not decide duplicate status");
  assert(exported.participant.record_usable === "", "participant UI must not decide record usability");
  assert(exported.participant.exclusion_reason === "", "participant UI must not decide exclusion reason");
  assert(exported.responses_csv.startsWith(config.response_schema_header + "\r\n"), "response CSV header drifted");
  assert(exported.participant_csv.startsWith(config.participant_schema_header + "\r\n"), "participant CSV header drifted");

  const playbackStarts = exported.audit.filter((event) => event.event === "playback_started");
  const playbackEnds = exported.audit.filter((event) => event.event === "playback_completed");
  const ratingEvents = exported.audit.filter((event) => event.event === "ratings_submitted");
  assert(playbackStarts.length === 12 && playbackEnds.length === 12 && ratingEvents.length === 12, "audit trail does not contain exactly 12 play/end/rating events");
  for (let index = 0; index < playbackStarts.length; index += 1) {
    assert(playbackStarts[index].stimulus_id === schedule.trials[index].stimulus_id, "playback audit order drifted");
    assert(playbackStarts[index].wav_sha256 === schedule.trials[index].wav_sha256, "browser-verified WAV digest drifted from frozen schedule");
  }
  const auditSeconds = auditDurations(exported);
  assert(requestedStimuli.join(",") === schedule.trials.map((trial) => `${trial.stimulus_id}.wav`).join(","), "browser did not fetch exactly the scheduled WAV sequence once each");

  await context.close();
  return {
    participant_id: schedule.participant_id,
    synthetic_nonhuman_session: true,
    counterbalance_group: schedule.counterbalance_group,
    trial_count: 12,
    stimulus_ids: schedule.trials.map((trial) => trial.stimulus_id),
    wav_sha256_verified_from_browser_audit: 12,
    browser_fetch_count: requestedStimuli.length,
    direct_user_gesture_play_calls: mediaPlayAudit.length,
    direct_user_gesture_gate_passed: mediaPlayAudit.every((item) => item.same_click_turn === true),
    min_wall_playback_seconds: Math.min(...wallDurations),
    max_wall_playback_seconds: Math.max(...wallDurations),
    min_audit_playback_seconds: Math.min(...auditSeconds),
    max_audit_playback_seconds: Math.max(...auditSeconds),
    export_path: path.basename(exportPath),
    passed: true,
  };
}

const bundleTextFiles = listTextFiles(webRoot);
for (const filename of bundleTextFiles) {
  assertNoConditionLeak(fs.readFileSync(filename, "utf8"), path.relative(webRoot, filename));
}
assertNoMappingKeys(readJson(path.join(webRoot, "config.json")), "participant config");
for (const filename of fs.readdirSync(path.join(webRoot, "schedules")).filter((name) => name.endsWith(".json"))) {
  assertNoMappingKeys(readJson(path.join(webRoot, "schedules", filename)), filename);
}
assert(!fs.existsSync(path.join(webRoot, "researcher")), "participant bundle unexpectedly contains researcher directory");
assert(!fs.existsSync(path.join(webRoot, "condition-key.csv")), "participant bundle unexpectedly contains condition key");

const selectedSchedules = chooseGroupSchedules();
const server = createStaticServer(webRoot);
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const address = server.address();
const baseUrl = `http://127.0.0.1:${address.port}`;

let browser;
try {
  browser = await chromium.launch({ headless: true });
  const sessions = await Promise.all(
    selectedSchedules.map((schedule) => runSyntheticSession(browser, baseUrl, schedule)),
  );
  const stimulusUnion = new Set(sessions.flatMap((session) => session.stimulus_ids));
  assert(stimulusUnion.size === 36, "three-group browser run did not cover all 36 frozen stimuli");
  const report = {
    gate: "participant browser delivery acceptance",
    passed: sessions.every((session) => session.passed),
    synthetic_nonhuman_sessions: true,
    real_participants_recruited: 0,
    groups_covered: sessions.map((session) => session.counterbalance_group).sort(),
    participant_schedules_exercised: sessions.map((session) => session.participant_id),
    total_trial_count: sessions.reduce((sum, session) => sum + session.trial_count, 0),
    unique_stimulus_count: stimulusUnion.size,
    browser_webcrypto_delivery_hash_check: true,
    actual_browser_playback_to_ended: true,
    direct_user_gesture_playback_gate: true,
    autoplay_policy_override_used: false,
    exported_records_verified: true,
    condition_mapping_leak_detected: false,
    bundle_text_files_scanned: bundleTextFiles.length,
    sessions,
  };
  fs.writeFileSync(path.join(outputDir, "participant-browser-acceptance.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(JSON.stringify(report, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}