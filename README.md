# Invariant Predictive Music

Reference implementation of the **Invariant Predictive Music (IPM)** model.

The project tests a simple claim: a musical system can remain learnable and coherent while producing useful surprise when it preserves deeper invariants, integrates deviations retrospectively, and treats silence as a real alternative to every subsidiary note.

The authoritative design is in [`SPEC.md`](SPEC.md).

## v0.1 target

Generate one deterministic 16-bar, three-voice MIDI study from a seed motif with a complete decision trace.

The implementation is built in explicit gates:

1. hard monophonic timing + deterministic seeded randomness;
2. active-sonority vertical compatibility;
3. subsidiary NOTE / CONTINUE / SILENCE competition;
4. main-voice EXPECTED / REVEALING / EXPLORATORY competition;
5. end-to-end 16-bar study + trace + MIDI export.

## Study #001

Study #001 uses a four-note seed with scale-degree shape **1-3-4-2** and duration ratio **1:1:2:4**. Eight two-bar main-voice decisions produce 16 bars in 4/4. The main line is frozen before the responsive (`B_R`) and harmonic/colour (`B_H`) voices are evaluated against it and against silence.

Generate the default deterministic study:

```bash
python -m pip install -e '.[dev]'
ipm-study
```

or directly:

```bash
python -m ipm.study --midi examples/study-001.mid --trace examples/study-001.trace.json
```

The trace records all three main futures, their scores, every subsidiary candidate, silence scores, selected events, final texture occupancy, vertical compatibility, and acceptance checks.

## Development

Python 3.11+ is required.

```bash
python -m pip install -e '.[dev]'
pytest
```

The repository runs the full suite on Python 3.11 and 3.13 in GitHub Actions.

## Voice hierarchy

- `M` — main predictive melody
- `B_R` — responsive stochastic counter-voice
- `B_H` — sparse harmonic/colour counter-voice

The main voice defines the musical world. Subsidiary voices are generated conditionally and must justify sounding over silence.
