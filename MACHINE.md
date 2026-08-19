# IPM Machine v0

IPM Machine v0 is the first human-steerable product surface over the current v0.2 Tune / Bass / Rhythm composer.

It is intentionally an **orchestration layer**, not a new composition formula. The scientific engine remains unchanged.

## Product question

> Can a person steer IPM and finish a piece while retaining a clear sense of musical agency?

That question is **not to be tested against a toy playback layer**. Machine use testing remains blocked until the internal synth passes audible sound acceptance, not merely technical implementation checks.

Machine v0 does not claim live continuation yet. The current engine composes complete deterministic pieces, so v0 steers whole-piece renders honestly rather than simulating a continuation API that does not exist.

## Controls

- **NEW** — move to a new deterministic root seed and render a new musical world.
- **ACTIVITY** — control the existing Bass and Rhythm density governors. Tune remains the primary line.
- **SURPRISE** — generate a small deterministic pool of IPM-mode candidate pieces, rank them by mean realised Tune surprise, and select the requested surprise quantile. This does not change the Tune scoring formula.
- **HOLD** — pin the current selected seed. While held, Activity can change Bass/Rhythm around exactly the same Tune seed. Surprise target is stored but does not change the Tune seed until Hold is released.
- **PLAY / STOP** — audition the exact current piece through Machine Synth Engine v1.
- **FINISH** — write the current MIDI, synth-rendered WAV, full IPM trace and a machine manifest.

## Machine Synth Engine v1

PLAY and FINISH use the same deterministic 44.1 kHz stereo synthesis engine.

The fixed v1 signal path is:

> polyphonic additive oscillator banks → lane-specific ADSR → velocity-sensitive 12 dB low-pass filtering → equal-power stereo placement → deterministic stereo room taps → DC block → soft limiter

The three musical lanes have independent timbres:

- **TUNE** — harmonically layered lead, slight detune and restrained vibrato, left-of-centre placement;
- **BASS** — fundamental-led voice, slower release and low cutoff, near-centre placement;
- **RHYTHM** — brighter short-decay pitched voice with wider detune, right-of-centre placement.

The synth is deterministic: identical IPM events and synth contract produce byte-identical WAV output. It requires no SoundFont, DAW, external synthesizer or network service.

The synth is a **product renderer only**. It does not replace or alter the frozen scientific listener-study renderer.

### Audible acceptance status

**Synth Sound Acceptance v1: FAIL.**

The owner judged the frozen Tune solo, Bass solo, Rhythm solo and full-mix audition set as **uncomfortable, toyish, flat and basic**. Technical implementation success therefore does not make Synth Engine v1 acceptable for product testing.

See `SYNTH_SOUND_ACCEPTANCE_V1_RESULT.md`.

## Outputs

FINISH writes:

- `ipm-machine-<seed>.mid`
- `ipm-machine-<seed>.wav`
- `ipm-machine-<seed>.trace.json`
- `ipm-machine-<seed>.machine.json`

The WAV is the machine's current internal synthesizer render, but Synth Engine v1 has **not** passed audible product acceptance. MIDI remains the instrument-neutral musical output. The IPM trace remains the evidence object for how the piece was composed.

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
- an audibly accepted internal synth engine;
- user-editable synth patches or external controller mapping for synth parameters.

Those continuation features require an explicit continuation/state contract in the composition engine. They should not be faked at the UI layer.

## Gate order

1. **Synth Engine implementation gate** — PASSED for v1: deterministic rendering and exact technical contract.
2. **Synth Sound Acceptance v1** — **FAILED**: uncomfortable, toyish, flat, basic.
3. **Machine Synth Replacement Contract v2** — next: freeze audible requirements before another synth design.
4. **Machine Use Gate** — BLOCKED until a replacement synth passes sound acceptance.
5. Physical hardware design comes later.

## Recruitment boundary

The IPM listening-study recruitment hold is unrelated to this product surface. Machine v0 must not reserve participant IDs, send study invitations, ingest real listener-study responses, or treat product use as research participation.
