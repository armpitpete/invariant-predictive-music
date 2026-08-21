# RealSynthEngine v4R1 — Control Diagnostics v0.1

Status: **FROZEN BEFORE v4R1 IMPLEMENTATION OUTPUT IS INSPECTED**

Contract parent: `REAL_SYNTH_ENGINE_V4R1_REDESIGN_CONTRACT_v0_2.md`

## 1. Purpose

These diagnostics prevent a repeat of failed v4 Gate D's ambiguity, where automation was mechanically nonzero and WAV bytes differed but the owner heard no coherent evolution advantage.

A musician-facing macro must therefore show:

1. the correct semantic direction; and
2. a predeclared minimum effect magnitude.

These are gate-specific engineering floors, not claims of universal psychoacoustic just-noticeable differences. Human R-D remains the decisive perceptual/usefulness gate.

## 2. Common deterministic fixture

Unless a macro section overrides it:

- sample rate: `44,100 Hz`;
- block size: `128`;
- one representative frozen patch from each family: VA, FM, MODAL;
- lane: `TUNE`;
- pitch: MIDI `48` (C3);
- velocity: `100`;
- silent control-settle pre-roll: `20 ms`;
- macro control event at sample `0`;
- note-on after the pre-roll;
- held duration: `4.0 s`;
- post-note tail: `1.5 s`;
- tested macro values: `0.15`, `0.50`, `0.85`;
- all other macros fixed at `0.50`;
- identical patch, transport and written note data across the three values;
- metrics calculated on floating-point pre-master audio where available, with post-master PCM retained for human R-D.

The 5 ms control ramp must finish before note-on.

## 3. Spectral analysis substrate

For BRIGHTNESS, BODY, MOTION, CHARACTER and DRIVE audio diagnostics:

- mono analysis signal = `(L + R) / 2`;
- Hann STFT window: `4096` samples;
- hop: `1024` samples;
- analysed frequency band unless overridden: `80..10,000 Hz`;
- steady-state analysis window: `250 ms .. 3.50 s` after note-on;
- frames whose RMS is below `-60 dBFS` are excluded;
- all epsilon terms use `1e-12`.

Identical deterministic replay must reproduce metric values within `1e-9` relative/absolute numerical tolerance as applicable.

## 4. BRIGHTNESS

Primary metric: median spectral centroid over valid steady-state frames.

Direction:

`centroid(0.85) > centroid(0.50) > centroid(0.15)` allowing at most 1% numerical slack at the middle point.

Minimum effect:

`centroid(0.85) >= 1.12 * centroid(0.15)`.

Family rule:

- threshold PASS in at least 2/3 reference families;
- the remaining family must not reverse by more than 3%.

If BRIGHTNESS is used by R-E, it must individually meet the full threshold in the R-E patch.

## 5. BODY

Primary metric: low/resonant energy share.

`BODY_SHARE = energy(80..300 Hz) / energy(80..6000 Hz)`

using summed STFT power over valid steady-state frames.

Direction:

`BODY_SHARE(0.85) > BODY_SHARE(0.50) > BODY_SHARE(0.15)` allowing 0.005 absolute middle-point slack.

Minimum effect:

`BODY_SHARE(0.85) - BODY_SHARE(0.15) >= 0.04` absolute.

Family rule: threshold PASS in at least 2/3 families; no remaining family may fall by more than 0.01 absolute.

If BODY is used by R-E, it must meet the full threshold in the R-E patch.

## 6. MOTION

Primary metric: RMS-normalised spectral flux.

For adjacent magnitude spectra `S_t`, first normalise each by its L2 norm, then compute positive spectral difference:

`flux_t = sqrt(sum(max(S_t - S_(t-1), 0)^2))`

Primary value = median `flux_t` across the steady-state window.

Direction:

`flux(0.85) > flux(0.50) > flux(0.15)` allowing 3% middle-point slack.

Minimum effect:

`flux(0.85) >= 1.25 * flux(0.15)`.

Family rule: threshold PASS in at least 2/3 families; remaining family must not reverse by more than 5%.

If MOTION is used by R-E, it must meet the full threshold in the R-E patch.

## 7. ATTACK

ATTACK is tested on newly triggered notes, not by altering an attack that has already occurred.

Fixture override:

- note duration: `1.0 s`;
- analyse first `300 ms` after note-on.

Primary metric: time from note-on to the first 10 ms RMS envelope point reaching 90% of the maximum 10 ms RMS value found in the first 300 ms.

Direction:

`T90(0.85) < T90(0.50) < T90(0.15)` allowing 1 ms middle-point slack.

Minimum effect requires both:

- `T90(0.85) <= 0.75 * T90(0.15)`; and
- `T90(0.15) - T90(0.85) >= 5 ms`.

Family rule: threshold PASS in at least 2/3 families; remaining family must not become slower at 0.85 by more than 2 ms.

If ATTACK is used by R-E, it must meet the full threshold in the R-E patch.

## 8. CHARACTER

Primary metric: normalised spectral entropy across the analysed band.

For each valid frame, convert band power bins to probabilities `p_i`, then:

`H = -sum(p_i * ln(p_i)) / ln(N)`

Primary value = median H across steady-state frames.

Direction:

`H(0.85) > H(0.50) > H(0.15)` allowing 0.01 absolute middle-point slack.

Minimum effect:

`H(0.85) - H(0.15) >= 0.05` absolute.

This metric is intentionally aimed at spectral/timbral complexity. A mapping that only lengthens modal decay without increasing this frozen complexity diagnostic does not satisfy CHARACTER mechanically.

Family rule: threshold PASS in at least 2/3 families; remaining family must not fall by more than 0.015 absolute.

If CHARACTER is used by R-E, it must meet the full threshold in the R-E patch.

## 9. DRIVE

DRIVE must demonstrate both stronger nonlinear operating level and a measurable output consequence.

### Internal-authority metric

For the frozen patch, the effective pre-nonlinearity drive scalar at macro 0.85 must be at least:

`1.35 * effective_drive(0.15)`.

### Audio metric

Primary audio metric: crest factor in dB over the steady-state mono signal:

`CF = 20*log10(peak_abs / RMS)`.

Increasing saturation should reduce crest factor for the frozen diagnostic note.

Direction:

`CF(0.85) < CF(0.15)`.

Minimum audio effect:

`CF(0.15) - CF(0.85) >= 0.5 dB`.

Family rule: both internal-authority and audio thresholds PASS in at least 2/3 families; remaining family must not reverse crest factor by more than 0.25 dB.

If DRIVE is used by R-E, both thresholds must pass in the R-E patch.

## 10. WIDTH

Use stereo mid/side signals:

`M = (L + R) / sqrt(2)`

`S = (L - R) / sqrt(2)`

over the steady-state window.

Primary metric:

`SIDE_RATIO = RMS(S)^2 / (RMS(M)^2 + RMS(S)^2 + 1e-12)`.

Direction:

`SIDE_RATIO(0.85) > SIDE_RATIO(0.50) > SIDE_RATIO(0.15)` allowing 0.005 absolute middle-point slack.

Minimum effect:

`SIDE_RATIO(0.85) - SIDE_RATIO(0.15) >= 0.05` absolute.

Family rule: threshold PASS in at least 2/3 families; remaining family must not fall by more than 0.01 absolute.

If WIDTH is used by R-E, it must meet the full threshold in the R-E patch.

## 11. SPACE

Fixture override:

- held note duration: `2.0 s`;
- post-note tail: `2.0 s`.

Primary metric:

`LATE_RATIO = energy(250..1250 ms after note-off) / energy(250..1250 ms before note-off)`

using stereo summed energy.

Direction:

`LATE_RATIO(0.85) > LATE_RATIO(0.50) > LATE_RATIO(0.15)` allowing 5% middle-point slack.

Minimum effect requires both:

- `LATE_RATIO(0.85) >= 1.50 * LATE_RATIO(0.15)`; and
- `LATE_RATIO(0.85) - LATE_RATIO(0.15) >= 0.03` absolute.

Family rule: threshold PASS in at least 2/3 families; remaining family must not reverse by more than 10%.

If SPACE is used by R-E, it must meet the full threshold in the R-E patch.

## 12. Cross-macro mechanical PASS rule

Before R-D human audition:

- every macro must meet its family rule;
- no macro may have an unexplained opposite-direction result outside its allowed residual-family tolerance;
- every macro selected as an R-E evolution target must meet its full threshold specifically in the frozen R-E patch;
- all diagnostic code, patches, WAV hashes, raw metric values and PASS/FAIL calculations must be exported in a machine-readable artifact.

A threshold miss is a mechanical R-D FAIL/BLOCK and no human macro or evolution audition occurs.

## 13. Anti-overfitting rule

These thresholds are now frozen before v4R1 synthesis implementation output is inspected.

Implementation may be designed to satisfy the declared semantics, but thresholds may not be lowered after seeing output.

If a threshold later proves technically invalid as a metric rather than merely difficult to meet, v4R1 stops and requires a newly versioned diagnostics contract before further human evidence is collected.
