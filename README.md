# Invariant Predictive Music

Reference implementation of the **Invariant Predictive Music (IPM)** model.

The project tests a simple claim: a musical system can remain learnable and coherent while producing useful surprise when it preserves deeper invariants, integrates deviations retrospectively, and treats silence as a real alternative to every subsidiary note.

The authoritative design is in [`SPEC.md`](SPEC.md).

## v0.1 target

Generate one deterministic 16-bar, three-voice MIDI study from a seed motif with a complete decision trace.

The first implementation gate deliberately contains no musical generation logic. It establishes two hard invariants first:

1. every monophonic voice rejects self-overlap;
2. the same random seed reproduces the same stochastic sequence.

## Development

Python 3.11+ is required.

```bash
python -m pip install -e '.[dev]'
pytest
```

## Voice hierarchy

- `M` — main predictive melody
- `B_R` — responsive stochastic counter-voice
- `B_H` — sparse harmonic/colour counter-voice

The main voice defines the musical world. Subsidiary voices are generated conditionally and must justify sounding over silence.
