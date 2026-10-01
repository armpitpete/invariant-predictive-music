# Composition Framework v0.1 — Listener Study Protocol

## Purpose

Test whether framework-enabled versions are perceived differently from matched controls without telling listeners what emotion was intended.

## Blind comparison

For each experiment:
- render a framework-enabled version;
- render a matched framework-disabled control using the same seed and high-level instrument settings;
- normalise playback level so simple loudness differences do not reveal condition;
- randomise A/B order;
- do not expose filenames, condition labels or intended emotional targets.

## Primary questions

After each excerpt ask:
1. What emotion or emotional mixture did you perceive? Use your own words.
2. Where was the strongest or most important moment?
3. Immediately before that moment, what did you expect to happen?
4. Did the important moment feel earned, arbitrary, or neither?
5. Did any part feel over-produced or unnecessarily busy?
6. Did any part feel empty in a useful way or merely unfinished?
7. Did you recognise material returning in a changed form?
8. Would you choose to hear the piece again?

## Rating items

Use 1–7 scales for:
- coherence;
- emotional impact;
- memorability;
- anticipation;
- sense of resolution or meaningful redirection;
- intimacy;
- tension;
- desire to hear again.

Do not include the intended primary/secondary emotion labels in the questionnaire.


## Pairwise comparison

After hearing both A and B:
- Which felt more coherent?
- Which created stronger anticipation?
- Which had the more meaningful payoff or redirection?
- Which used space more effectively?
- Which felt more emotionally affecting?
- Which was more memorable?
- Which would you prefer to hear again?
- Or: no meaningful difference.

## Required metadata

Record per response:
- anonymous listener ID;
- experiment ID;
- presentation order;
- condition identity kept hidden until analysis;
- playback device category if known;
- whether the listener has formal musical training;
- free-text emotion description;
- strongest-moment timestamp;
- expectation description;
- all ratings;
- pairwise choices.

## Negative controls

Include at least:
- a framework-disabled matched control;
- a version where structural function labels are shuffled but pitches remain legal;
- a version where expressive directives are flattened;
- a version where suspension density shaping is removed.

Negative controls prevent a general preference for any extra processing from being mistaken for support for the framework.

## Analysis boundary

Automated metrics may be compared with listener responses, but must not replace them.

Predefined comparisons:
- intended target words vs free-text emotion descriptions;
- predicted structural arrival vs reported strongest moment;
- expectation-strength proxy vs reported anticipation;
- consequence coverage vs reported earnedness;
- negative-space proxy vs reported useful emptiness;
- transformed-return count vs reported recognition;
- intensity proxy vs reported emotional importance.

A mismatch is evidence against the current mapping or implementation, not a listener failure.


## Acceptance rule for emotional claims

Do not claim that a framework feature causes a named emotion from one successful example.

A tendency should only move from **hypothesis** toward **supported working rule** after:
- repeated listener results;
- matched controls;
- consistent direction across more than one seed/piece;
- no obvious loudness or production confound;
- documented failures as well as successes.

## Experiment sequence

The first evidence gate contains **one** matched 60–90 second structural A/B
pair. Enter only the generated `blind/` folder, listen to its opaque
`render-1.wav` and `render-2.wav` files, and record the judgment before
browsing the parent evidence folder or opening `private-condition-map.json`.

Only after that pair has been judged, failures classified, and demonstrated
problems repaired should the project expand to the eight-carrier
generalisation set:

1. melody-led;
2. harmony-led;
3. rhythm-led;
4. timbre-led;
5. space-led;
6. quiet payoff;
7. denied expectation;
8. transformed repetition.

This ordering prevents broad implementation work from outrunning evidence.
