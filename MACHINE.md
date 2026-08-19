# IPM Machine v0

IPM Machine v0 is the first human-steerable product surface over the current v0.2 Tune / Bass / Rhythm composer.

It is intentionally an **orchestration layer**, not a new composition formula. The scientific engine remains unchanged.

## Product question

> Can a person steer IPM and finish a piece while retaining a clear sense of musical agency?

Machine v0 does not claim live continuation yet. The current engine composes complete deterministic pieces, so v0 steers whole-piece renders honestly rather than simulating a continuation API that does not exist.

## Controls

- **NEW** — move to a new deterministic root seed and render a new musical world.
- **ACTIVITY** — control the existing Bass and Rhythm density governors. Tune remains the primary line.
- **SURPRISE** — generate a small deterministic pool of IPM-mode candidate pieces, rank them by mean realised Tune surprise, and select the requested surprise quantile. This does not change the Tune scoring formula.
- **HOLD** — pin the current selected seed. While held, Activity can change Bass/Rhythm around exactly the same Tune seed. Surprise target is stored but does not change the Tune seed until Hold is released.
- **PLAY / STOP** — audition a built-in dependency-free WAV preview.
- **FINISH** — write the current MIDI, preview WAV, full IPM trace and a machine manifest.

## Outputs

FINISH writes:

- `ipm-machine-<seed>.mid`
- `ipm-machine-<seed>.wav`
- `ipm-machine-<seed>.trace.json`
- `ipm-machine-<seed>.machine.json`

The WAV is a convenience preview synth. MIDI is the instrument-neutral musical output. The IPM trace remains the evidence object for how the piece was composed.

## Run

```bash
python -m pip install -e '.[dev]'
ipm-machine
```

Open the printed local URL, normally:

```text
http://127.0.0.1:8765
```

Optional controls:

```bash
ipm-machine --seed 987762706 --candidate-count 5 --port 8765
```

## Deliberate v0 boundaries

Machine v0 does **not** yet provide:

- live bar-by-bar continuation from an arbitrary current state;
- semantic memory slots such as A/B/C return points;
- a true branch-from-held-history operation;
- external MIDI clock or hardware controller mapping;
- production-quality internal synthesis.

Those features require an explicit continuation/state contract in the composition engine. They should not be faked at the UI layer.

## Recruitment boundary

The IPM listening-study recruitment hold is unrelated to this product surface. Machine v0 must not reserve participant IDs, send study invitations, ingest real listener-study responses, or treat product use as research participation.
