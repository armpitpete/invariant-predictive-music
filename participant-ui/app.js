import { StudySession } from "./protocol.mjs";

const $ = (selector) => document.querySelector(selector);
const app = $("#app");
let config;
let schedule;
let session;
let storageKey;
let audio = null;
let objectUrl = null;
let preparedStimulus = null;
let maxObservedTime = 0;

function htmlEscape(value) {
  return String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
}

function renderError(message) {
  app.innerHTML = `<section class="card"><h1>Study unavailable</h1><p>${htmlEscape(message)}</p></section>`;
}

async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest("SHA-256", buffer);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function assertPersistentStorage() {
  const key = "ipm-listening-storage-check";
  localStorage.setItem(key, "ok");
  if (localStorage.getItem(key) !== "ok") throw new Error("Browser storage is unavailable.");
  localStorage.removeItem(key);
}

function persistSession() {
  localStorage.setItem(storageKey, JSON.stringify(session.snapshotObject()));
}

async function loadStudy() {
  assertPersistentStorage();
  if (!globalThis.crypto?.subtle) throw new Error("This study requires a secure HTTPS connection for audio integrity checking.");
  const participantId = new URLSearchParams(location.search).get("participant");
  if (!participantId || !/^P\d{3}$/.test(participantId)) throw new Error("Open the study using the participant-specific link supplied by the researcher.");
  config = await fetch("./config.json", { cache: "no-store" }).then((response) => {
    if (!response.ok) throw new Error("Could not load study configuration.");
    return response.json();
  });
  if (!config.participant_ids.includes(participantId)) throw new Error("This participant ID is not in the frozen P001–P036 enrolment set.");
  schedule = await fetch(`./schedules/${participantId}.json`, { cache: "no-store" }).then((response) => {
    if (!response.ok) throw new Error("Could not load the frozen participant schedule.");
    return response.json();
  });
  storageKey = [
    "ipm-listening-v1",
    participantId,
    schedule.source_schedule_sha256,
    config.frozen_listener_artifact.artifact_sha256,
  ].join(":");
  const saved = localStorage.getItem(storageKey);
  if (saved) {
    session = StudySession.restore({ config, schedule, snapshot: JSON.parse(saved) });
    resumeSavedSession();
    return;
  }
  session = new StudySession({ config, schedule });
  renderConsent();
}

function resumeSavedSession() {
  if (session.phase === "playing") {
    session.failPlayback("The study page was reloaded while an excerpt was playing.");
    persistSession();
    renderTerminal("A technical playback failure was recorded because the page reloaded during an excerpt. Do not restart or replay the study.");
    return;
  }
  if (session.phase === "rating") {
    renderRestoredRating();
    return;
  }
  if (session.phase === "audio-check") {
    renderAudioCheck();
    return;
  }
  if (session.phase === "ready") {
    session.beginMainBlock();
    persistSession();
    renderTrial();
    return;
  }
  if (session.phase === "trial-ready") {
    renderTrial();
    return;
  }
  if (session.phase === "complete") {
    renderTerminal("Thank you. The listening block is complete.");
    return;
  }
  if (session.phase === "technical-failure") {
    renderTerminal("A technical playback failure was recorded. Do not restart or replay the study.");
    return;
  }
  if (session.phase === "withdrawn") {
    renderTerminal("You stopped the study. No more excerpts will be played.");
    return;
  }
  renderConsent();
}

function renderConsent() {
  const consent = config.consent;
  app.innerHTML = `
    <section class="card">
      <p class="eyebrow">Participant ${htmlEscape(schedule.participant_id)}</p>
      <h1>${htmlEscape(consent.title)}</h1>
      ${consent.information.map((text) => `<p>${htmlEscape(text)}</p>`).join("")}
      <div class="consent-list">
        ${consent.checks.map((item) => `<label><input type="checkbox" id="consent-${htmlEscape(item.id)}"> <span>${htmlEscape(item.text)}</span></label>`).join("")}
        <label><input type="checkbox" id="headphones"> <span>${htmlEscape(consent.headphones_check)}</span></label>
      </div>
      <div class="grid two">
        <label>Years of music-making experience<input id="music-years" type="number" min="0" max="100" step="0.5" required></label>
        <label>Years of formal musical training<input id="training-years" type="number" min="0" max="100" step="0.5" required></label>
      </div>
      <div class="actions"><button id="consent-continue">Continue to audio check</button></div>
      <p id="consent-error" class="error" hidden></p>
    </section>`;
  $("#consent-continue").addEventListener("click", () => {
    try {
      const checks = Object.fromEntries(config.consent.checks.map((item) => [item.id, $(`#consent-${item.id}`).checked]));
      session.acceptConsent({
        checks,
        headphones: $("#headphones").checked,
        musicMakingYears: $("#music-years").value,
        formalTrainingYears: $("#training-years").value,
      });
      persistSession();
      renderAudioCheck();
    } catch (error) {
      const node = $("#consent-error");
      node.hidden = false;
      node.textContent = error.message;
    }
  });
}

function renderAudioCheck() {
  app.innerHTML = `
    <section class="card">
      <p class="eyebrow">Audio check</p>
      <h1>Set a comfortable volume</h1>
      <p>Keep your headphones on. Play the short check tone and set your device to a comfortable listening level. The tone is not part of the experiment.</p>
      <div class="actions"><button id="play-check">Play check tone</button></div>
      <label class="confirm"><input id="comfortable" type="checkbox" disabled> I heard the check tone clearly and the volume is comfortable.</label>
      <div class="actions"><button id="begin" disabled>Begin 12-trial listening block</button></div>
      <p class="muted">The study is not counted as enrolled until the first scheduled excerpt actually starts playing.</p>
    </section>`;
  $("#play-check").addEventListener("click", async () => {
    const context = new AudioContext();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = 440;
    gain.gain.value = 0.06;
    oscillator.connect(gain).connect(context.destination);
    oscillator.start();
    oscillator.stop(context.currentTime + 0.8);
    await new Promise((resolve) => setTimeout(resolve, 900));
    await context.close();
    $("#comfortable").disabled = false;
  }, { once: true });
  $("#comfortable").addEventListener("change", (event) => { $("#begin").disabled = !event.target.checked; });
  $("#begin").addEventListener("click", () => {
    session.completeAudioCheck();
    session.beginMainBlock();
    persistSession();
    renderTrial();
  }, { once: true });
}

function stopCurrentAudio() {
  const active = audio;
  audio = null;
  preparedStimulus = null;
  if (active) {
    active.pause();
    active.removeAttribute("src");
    active.load();
  }
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }
}

function releaseCompletedAudio() {
  audio = null;
  preparedStimulus = null;
  if (objectUrl) {
    URL.revokeObjectURL(objectUrl);
    objectUrl = null;
  }
}

function renderTrial() {
  const trial = session.currentTrial;
  app.innerHTML = `
    <section class="card">
      <div class="trial-head"><p class="eyebrow">Trial ${trial.trial} of 12</p><button id="stop-study" class="text-button">Stop study</button></div>
      <h1>Listen to the full excerpt</h1>
      <p>The frozen excerpt is verified before the play button unlocks. Then press play once. The rating questions will appear only after the excerpt reaches the end.</p>
      <div class="player-box"><button id="play-stimulus" disabled>Play excerpt</button><span id="play-status" class="muted">Preparing frozen audio…</span></div>
      <p id="trial-error" class="error" hidden></p>
      <div id="ratings" hidden></div>
    </section>`;
  $("#stop-study").addEventListener("click", () => {
    session.withdraw();
    persistSession();
    stopCurrentAudio();
    renderTerminal("You stopped the study. No more excerpts will be played.");
  });
  $("#play-stimulus").addEventListener("click", () => startPreparedPlayback(trial), { once: true });
  prepareFrozenStimulus(trial);
}

async function prepareFrozenStimulus(trial) {
  const button = $("#play-stimulus");
  const status = $("#play-status");
  try {
    const response = await fetch(`./stimuli/${trial.stimulus_id}.wav`, { cache: "no-store" });
    if (!response.ok) throw new Error("The audio file could not be loaded.");
    const bytes = await response.arrayBuffer();
    const actualSha = await sha256Hex(bytes);
    if (actualSha !== trial.wav_sha256) throw new Error("Audio integrity check failed. Stop and tell the researcher.");
    if (session.phase !== "trial-ready" || session.currentTrial?.stimulus_id !== trial.stimulus_id) return;

    stopCurrentAudio();
    objectUrl = URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
    audio = new Audio(objectUrl);
    audio.controls = false;
    audio.preload = "auto";
    audio.playbackRate = 1;
    maxObservedTime = 0;
    preparedStimulus = { stimulus_id: trial.stimulus_id, wav_sha256: actualSha };

    audio.addEventListener("ratechange", () => { if (audio && audio.playbackRate !== 1) audio.playbackRate = 1; });
    audio.addEventListener("timeupdate", () => { if (audio) maxObservedTime = Math.max(maxObservedTime, audio.currentTime); });
    audio.addEventListener("seeking", () => {
      if (!audio) return;
      if (Math.abs(audio.currentTime - maxObservedTime) > 0.35) failPlayback("Seeking was detected during the excerpt.");
    });
    audio.addEventListener("error", () => failPlayback("The browser reported an audio playback error."), { once: true });
    audio.addEventListener("abort", () => failPlayback("Audio playback was interrupted."), { once: true });
    audio.addEventListener("ended", () => {
      if (!audio || session.phase !== "playing") return;
      session.finishPlayback(trial.stimulus_id);
      persistSession();
      const currentStatus = $("#play-status");
      if (currentStatus) currentStatus.textContent = "Completed";
      releaseCompletedAudio();
      renderRatings();
    }, { once: true });

    if (button && status) {
      button.disabled = false;
      status.textContent = "Ready";
    }
  } catch (error) {
    if (session.phase === "trial-ready") {
      failPlayback(error.message);
      return;
    }
    const node = $("#trial-error");
    if (node) {
      node.hidden = false;
      node.textContent = error.message;
    }
  }
}

function startPreparedPlayback(trial) {
  const button = $("#play-stimulus");
  const status = $("#play-status");
  if (!audio || !preparedStimulus || preparedStimulus.stimulus_id !== trial.stimulus_id) {
    failPlayback("Verified audio was not ready when playback was requested.");
    return;
  }
  button.disabled = true;
  status.textContent = "Starting…";
  let startRecorded = false;

  const recordActualStart = () => {
    if (startRecorded || session.phase !== "trial-ready") return;
    startRecorded = true;
    session.startPlayback(trial.stimulus_id, preparedStimulus.wav_sha256);
    persistSession();
    const currentStatus = $("#play-status");
    if (currentStatus) currentStatus.textContent = "Playing…";
  };

  audio.addEventListener("playing", recordActualStart, { once: true });
  try {
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.then === "function") {
      playPromise.then(recordActualStart).catch((error) => {
        if (session.phase === "trial-ready" || session.phase === "playing") failPlayback(error.message);
      });
    }
  } catch (error) {
    if (session.phase === "trial-ready" || session.phase === "playing") failPlayback(error.message);
  }
}

function failPlayback(reason) {
  if (!(session.phase === "playing" || session.phase === "trial-ready")) return;
  session.failPlayback(reason);
  persistSession();
  stopCurrentAudio();
  renderTerminal("A technical playback failure was recorded. Do not restart or replay the study.");
}

function ratingMarkup() {
  return `
    <h2>Rate what you just heard</h2>
    ${config.ratings.map((item) => `
      <fieldset class="rating" data-field="${htmlEscape(item.field)}">
        <legend>${htmlEscape(item.prompt)}</legend>
        <input type="range" min="0" max="100" step="1" value="50" data-touched="false" id="${htmlEscape(item.field)}">
        <div class="scale"><span>0 — ${htmlEscape(item.min_anchor)}</span><output for="${htmlEscape(item.field)}">—</output><span>100 — ${htmlEscape(item.max_anchor)}</span></div>
      </fieldset>`).join("")}
    <div class="actions"><button id="submit-ratings" disabled>${session.currentTrialIndex === 11 ? "Finish study" : "Next trial"}</button></div>`;
}

function wireRatings() {
  for (const item of config.ratings) {
    const input = $(`#${item.field}`);
    const output = input.closest("fieldset").querySelector("output");
    input.addEventListener("input", () => {
      input.dataset.touched = "true";
      output.value = input.value;
      const allTouched = config.ratings.every((rating) => $(`#${rating.field}`).dataset.touched === "true");
      $("#submit-ratings").disabled = !allTouched;
    });
  }
  $("#submit-ratings").addEventListener("click", () => {
    const values = Object.fromEntries(config.ratings.map((item) => [item.field, Number($(`#${item.field}`).value)]));
    session.submitRatings(values);
    persistSession();
    if (session.phase === "complete") renderTerminal("Thank you. The listening block is complete.");
    else renderTrial();
  }, { once: true });
}

function renderRatings() {
  const host = $("#ratings");
  host.hidden = false;
  host.innerHTML = ratingMarkup();
  wireRatings();
}

function renderRestoredRating() {
  const trial = session.currentTrial;
  app.innerHTML = `
    <section class="card">
      <p class="eyebrow">Trial ${trial.trial} of 12</p>
      <h1>Rate the excerpt you already heard</h1>
      <p>The excerpt finished before this page was reloaded. It cannot be replayed; complete the ratings below.</p>
      <div id="ratings">${ratingMarkup()}</div>
    </section>`;
  wireRatings();
}

function downloadExport() {
  const payload = session.exportObject();
  const blob = new Blob([JSON.stringify(payload, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${session.participantId}-study-export.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function renderTerminal(message) {
  const exportable = Boolean(session.consent);
  app.innerHTML = `
    <section class="card">
      <p class="eyebrow">Participant ${htmlEscape(session.participantId)}</p>
      <h1>${session.phase === "complete" ? "Study complete" : "Study stopped"}</h1>
      <p>${htmlEscape(message)}</p>
      ${exportable ? '<p>Download the study export and return it using the method given by the researcher. This interface does not upload it automatically.</p><div class="actions"><button id="download-export">Download study export</button></div>' : ""}
    </section>`;
  if (exportable) $("#download-export").addEventListener("click", downloadExport);
}

loadStudy().catch((error) => renderError(error.message));