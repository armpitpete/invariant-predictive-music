"""Composition Framework v0.1 integration layer.

This module sits above the IPM prediction experiment. It does not redefine
musical quality or claim that structural proxies equal perceived emotion.
It supplies deterministic form, space, expressive and timbral intent plus
traceable evaluation hooks for controlled listening experiments.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from fractions import Fraction
from math import sqrt
from typing import Any, Sequence

from .model import NoteEvent, Voice


class StructuralFunction(str, Enum):
    INTRODUCTION = "introduction"
    RECOGNITION = "recognition"
    COMPLICATION = "complication"
    SUSPENSION = "suspension"
    ARRIVAL = "arrival"
    AFTERMATH = "aftermath"


class ConsequenceKind(str, Enum):
    FULFILMENT = "fulfilment"
    REDIRECTION = "new-direction"
    INTENTIONAL_ABANDONMENT = "intentional-abandonment"
    UNRESOLVED = "unresolved"


_VALID_CARRIERS = {
    "balanced",
    "melody",
    "harmony",
    "rhythm",
    "timbre",
    "space",
    "quiet-payoff",
    "denied-expectation",
    "transformed-repetition",
}


@dataclass(frozen=True, slots=True)
class CompositionFrameworkConfig:
    enabled: bool = False
    primary_emotion: str = "tenderness"
    secondary_emotion: str = "uncertainty"
    carrier: str = "balanced"
    negative_space: float = 0.55
    expressive_gesture: float = 0.55
    transformation_strength: float = 0.55
    timbral_strength: float = 0.0
    consequence_horizon_bars: int = 3
    structural_override: tuple[str, ...] = ()
    timbral_identity: str = "restrained-evolving"

    def __post_init__(self) -> None:
        if self.carrier not in _VALID_CARRIERS:
            raise ValueError(f"unknown emotional carrier: {self.carrier}")
        for name in (
            "negative_space", "expressive_gesture",
            "transformation_strength", "timbral_strength",
        ):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} must be in 0..1")

        if self.consequence_horizon_bars < 1:
            raise ValueError("consequence_horizon_bars must be >= 1")
        for value in self.structural_override:
            StructuralFunction(value)


_FORM_TEMPLATES: tuple[tuple[StructuralFunction, ...], ...] = (
    (
        StructuralFunction.INTRODUCTION,
        StructuralFunction.RECOGNITION,
        StructuralFunction.COMPLICATION,
        StructuralFunction.SUSPENSION,
        StructuralFunction.ARRIVAL,
        StructuralFunction.AFTERMATH,
    ),
    (
        StructuralFunction.INTRODUCTION,
        StructuralFunction.RECOGNITION,
        StructuralFunction.COMPLICATION,
        StructuralFunction.RECOGNITION,
        StructuralFunction.SUSPENSION,
        StructuralFunction.ARRIVAL,
        StructuralFunction.AFTERMATH,
    ),
    (
        StructuralFunction.INTRODUCTION,
        StructuralFunction.RECOGNITION,
        StructuralFunction.SUSPENSION,
        StructuralFunction.COMPLICATION,
        StructuralFunction.AFTERMATH,
    ),
    (
        StructuralFunction.INTRODUCTION,
        StructuralFunction.COMPLICATION,

        StructuralFunction.RECOGNITION,
        StructuralFunction.SUSPENSION,
        StructuralFunction.ARRIVAL,
        StructuralFunction.COMPLICATION,
        StructuralFunction.AFTERMATH,
    ),
)


def _template(config: CompositionFrameworkConfig, seed: int) -> tuple[StructuralFunction, ...]:
    if config.structural_override:
        return tuple(StructuralFunction(value) for value in config.structural_override)
    if config.carrier == "denied-expectation":
        return _FORM_TEMPLATES[2]
    return _FORM_TEMPLATES[seed % len(_FORM_TEMPLATES)]


def build_structural_plan(
    bars: int,
    config: CompositionFrameworkConfig,
    *,
    seed: int,
) -> tuple[StructuralFunction, ...]:
    """Expand a seeded functional form across bars without fixed clock timings."""

    if bars < 1:
        raise ValueError("bars must be positive")
    template = _template(config, seed)
    if bars == 1:
        return (template[0],)
    return tuple(template[min(len(template) - 1, (bar * len(template)) // bars)] for bar in range(bars))


def structural_function_for_bar(

    config: CompositionFrameworkConfig,
    bar: int,
    bars: int,
    *,
    seed: int,
) -> StructuralFunction:
    return build_structural_plan(bars, config, seed=seed)[bar]


_ACTIVITY_EXPONENT: dict[StructuralFunction, float] = {
    StructuralFunction.INTRODUCTION: 1.30,
    StructuralFunction.RECOGNITION: 1.08,
    StructuralFunction.COMPLICATION: 0.82,
    StructuralFunction.SUSPENSION: 2.25,
    StructuralFunction.ARRIVAL: 1.12,
    StructuralFunction.AFTERMATH: 1.45,
}


def framework_activity_probability(
    base_activity: float,
    phase_exponent: float,
    function: StructuralFunction,
    *,
    enabled: bool,
    negative_space_strength: float = 0.55,
) -> float:
    """Preserve exact endpoints while scaling functional density shaping."""

    if base_activity in {0.0, 1.0}:
        return base_activity
    exponent = phase_exponent
    if enabled:
        function_exponent = _ACTIVITY_EXPONENT[function]
        shaped = 1.0 + (function_exponent - 1.0) * negative_space_strength
        exponent *= shaped
    return base_activity ** exponent


def _bar_index(event: NoteEvent, beats_per_bar: int) -> int:
    return int(event.onset // beats_per_bar)


_VELOCITY_DELTA: dict[StructuralFunction, int] = {
    StructuralFunction.INTRODUCTION: -2,
    StructuralFunction.RECOGNITION: 0,
    StructuralFunction.COMPLICATION: 1,
    StructuralFunction.SUSPENSION: -4,
    StructuralFunction.ARRIVAL: -1,
    StructuralFunction.AFTERMATH: -3,
}


def apply_structural_expression(
    voices: Sequence[Voice],
    plan: Sequence[StructuralFunction],
    config: CompositionFrameworkConfig,
    *,
    beats_per_bar: int,
) -> tuple[Voice, ...]:
    """Apply intentional dynamic phrasing; never random humanisation."""

    if not config.enabled or config.expressive_gesture == 0:
        return tuple(voices)
    amount = config.expressive_gesture
    rendered: list[Voice] = []
    for voice in voices:
        events: list[NoteEvent] = []
        for event in voice.events:
            bar = min(len(plan) - 1, _bar_index(event, beats_per_bar))
            delta = round(_VELOCITY_DELTA[plan[bar]] * amount)
            if voice.name != "TUNE":
                delta = round(delta * 0.6)
            velocity = max(1, min(127, event.velocity + delta))
            events.append(
                NoteEvent(event.onset, event.duration, event.pitch, velocity)
            )
        rendered.append(Voice.from_events(voice.name, events))
    return tuple(rendered)


@dataclass(frozen=True, slots=True)
class ExpressiveDirective:
    function: StructuralFunction
    attack: str
    note_length: str
    vibrato: str
    portamento: str
    timing: str
    dynamic_shape: str


@dataclass(frozen=True, slots=True)
class TimbralDirective:
    function: StructuralFunction
    identity: str
    envelope: str
    spectrum: str
    filter_motion: str
    spatial_motion: str
    texture: str


def _expressive_directive(function: StructuralFunction) -> ExpressiveDirective:
    table = {
        StructuralFunction.INTRODUCTION: ("soft", "natural", "late-subtle", "rare", "settled", "restrained"),
        StructuralFunction.RECOGNITION: ("clear", "natural", "stable", "minimal", "steady", "stable"),
        StructuralFunction.COMPLICATION: ("firmer", "shorter", "delayed", "selective", "slightly-forward", "uneven"),
        StructuralFunction.SUSPENSION: ("soft", "held", "late", "selective", "held-back", "reduced"),
        StructuralFunction.ARRIVAL: ("clear", "held", "late-subtle", "selective", "settled", "quiet-emphasis"),
        StructuralFunction.AFTERMATH: ("soft", "released", "fading", "rare", "relaxed", "receding"),
    }
    return ExpressiveDirective(function, *table[function])


def _timbral_directive(
    function: StructuralFunction,
    identity: str,
) -> TimbralDirective:
    table = {
        StructuralFunction.INTRODUCTION: ("slow", "narrow", "minimal", "centered", "sparse"),
        StructuralFunction.RECOGNITION: ("stable", "identity-band", "subtle", "stable", "recognisable"),
        StructuralFunction.COMPLICATION: ("responsive", "broader", "active", "wider", "layered"),
        StructuralFunction.SUSPENSION: ("slow", "reduced", "closing", "narrowing", "thinned"),
        StructuralFunction.ARRIVAL: ("open", "clear", "opening", "wider", "resolved-without-max-density"),
        StructuralFunction.AFTERMATH: ("soft", "darkening", "settling", "contracting", "residual"),
    }
    return TimbralDirective(function, identity, *table[function])


def build_directives(
    plan: Sequence[StructuralFunction],
    config: CompositionFrameworkConfig,
) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for bar, function in enumerate(plan):
        expressive = _expressive_directive(function)
        timbral = _timbral_directive(function, config.timbral_identity)
        rows.append(
            {
                "bar": bar,
                "function": function.value,
                "expressive": {
                    **asdict(expressive),
                    "function": expressive.function.value,
                },
                "timbre": {
                    **asdict(timbral),
                    "function": timbral.function.value,
                },
            }
        )
    return tuple(rows)


def _events_for_bar(
    voice: Voice,
    bar: int,
    beats_per_bar: int,
) -> tuple[NoteEvent, ...]:
    start = Fraction(bar * beats_per_bar)
    end = start + beats_per_bar
    return tuple(event for event in voice.events if start <= event.onset < end)


def _motif_identity(events: Sequence[NoteEvent]) -> tuple[Any, ...]:
    if not events:
        return ("rest",)
    contour = tuple(
        (1 if right.pitch > left.pitch else -1 if right.pitch < left.pitch else 0)
        for left, right in zip(events, events[1:], strict=False)
    )
    durations = tuple(round(float(event.duration) * 4) for event in events)
    return (len(events), contour, durations)


def _exact_rendering(events: Sequence[NoteEvent]) -> tuple[Any, ...]:
    return tuple(
        (event.pitch, event.onset.numerator, event.onset.denominator,
         event.duration.numerator, event.duration.denominator, event.velocity)
        for event in events
    )


def _bar_density(
    voices: Sequence[Voice],
    bar: int,
    beats_per_bar: int,
) -> float:
    start = Fraction(bar * beats_per_bar)
    end = start + beats_per_bar
    sounded = Fraction(0)
    for voice in voices:
        for event in voice.events:
            overlap = max(Fraction(0), min(end, event.end) - max(start, event.onset))
            sounded += overlap
    return min(1.0, float(sounded / (beats_per_bar * max(1, len(voices)))))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _correlation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or len(left) < 2:
        return 0.0
    ml, mr = _mean(left), _mean(right)
    dl = [value - ml for value in left]
    dr = [value - mr for value in right]

    numerator = sum(a * b for a, b in zip(dl, dr, strict=True))
    left_norm = sqrt(sum(value * value for value in dl))
    right_norm = sqrt(sum(value * value for value in dr))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def framework_config_json(config: CompositionFrameworkConfig) -> dict[str, Any]:
    return {
        "enabled": config.enabled,
        "primary_emotion": config.primary_emotion,
        "secondary_emotion": config.secondary_emotion,
        "carrier": config.carrier,
        "negative_space": config.negative_space,
        "expressive_gesture": config.expressive_gesture,
        "transformation_strength": config.transformation_strength,
        "timbral_strength": config.timbral_strength,
        "consequence_horizon_bars": config.consequence_horizon_bars,
        "structural_override": list(config.structural_override),
        "timbral_identity": config.timbral_identity,
    }


def build_framework_trace(
    config: CompositionFrameworkConfig,
    *,
    seed: int,
    beats_per_bar: int,
    bars: int,
    tune_trace: Sequence[dict[str, Any]],
    voices: Sequence[Voice],
    pattern_lock_trace: Sequence[dict[str, Any]] = (),
) -> dict[str, Any]:
    plan = build_structural_plan(bars, config, seed=seed)
    directives = build_directives(plan, config)
    identities: dict[tuple[Any, ...], list[tuple[int, tuple[Any, ...]]]] = {}
    states: list[dict[str, Any]] = []

    for bar in range(bars):
        tune_events = _events_for_bar(voices[0], bar, beats_per_bar)
        identity = _motif_identity(tune_events)
        exact = _exact_rendering(tune_events)
        previous = identities.get(identity, [])
        transformed_return = any(rendering != exact for _, rendering in previous)

        recurrence_count = len(previous)
        identities.setdefault(identity, []).append((bar, exact))

        tune_row = tune_trace[bar]
        selected = tune_row["selected"]
        alternatives = tune_row.get("alternatives", ())
        prediction_strength = max(
            (item["probability"] for item in alternatives),
            default=selected["probability"],
        )
        density = _bar_density(voices, bar, beats_per_bar)
        negative_space = 1.0 - density
        function = plan[bar]
        branch = tune_row["selected_branch"]
        disruptive_function = function in {
            StructuralFunction.COMPLICATION,
            StructuralFunction.SUSPENSION,
        }
        deviation = disruptive_function and branch != "expected"
        if bar and disruptive_function:
            previous_density = states[-1]["density"]
            deviation = deviation or density < previous_density - 0.18

        importance_bonus = {
            StructuralFunction.INTRODUCTION: 0.02,
            StructuralFunction.RECOGNITION: 0.05,
            StructuralFunction.COMPLICATION: 0.18,
            StructuralFunction.SUSPENSION: 0.15,
            StructuralFunction.ARRIVAL: 0.25,
            StructuralFunction.AFTERMATH: 0.08,
        }[function]
        significance = min(
            1.0,
            float(selected["retrospective_necessity"]) + importance_bonus,
        )
        velocities = [event.velocity for event in tune_events]
        intensity = _mean([value / 127.0 for value in velocities])


        states.append(
            {
                "bar": bar,
                "function": function.value,
                "motif_identity": repr(identity),
                "recurrence_count": recurrence_count,
                "transformed_return": transformed_return,
                "prediction_strength": prediction_strength,
                "expectation_established": (
                    prediction_strength >= 0.20 or recurrence_count > 0
                ),
                "selected_branch": branch,
                "deviation": deviation,
                "density": density,
                "negative_space": negative_space,
                "structural_significance_proxy": significance,
                "intensity_proxy": intensity,
                "consequence": None,
            }
        )

    deviation_rows = [row for row in states if row["deviation"]]
    resolved = 0
    abandoned = 0
    unresolved = 0
    for row in deviation_rows:
        start = row["bar"]
        outcome: dict[str, Any] | None = None
        for later in states[start + 1 : start + 1 + config.consequence_horizon_bars]:
            later_function = StructuralFunction(later["function"])
            if later_function == StructuralFunction.ARRIVAL or (
                later["selected_branch"] == "expected"
                and later["expectation_established"]
            ):
                outcome = {
                    "kind": ConsequenceKind.FULFILMENT.value,
                    "bar": later["bar"],
                    "delay_bars": later["bar"] - start,
                }
                break

            if (
                later_function == StructuralFunction.COMPLICATION
                and later["selected_branch"] != "expected"
            ):
                outcome = {
                    "kind": ConsequenceKind.REDIRECTION.value,
                    "bar": later["bar"],
                    "delay_bars": later["bar"] - start,
                }
                break
        if outcome is None:
            later_has_arrival = any(
                StructuralFunction(later["function"]) == StructuralFunction.ARRIVAL
                for later in states[start + 1 :]
            )
            if not later_has_arrival:
                outcome = {
                    "kind": ConsequenceKind.INTENTIONAL_ABANDONMENT.value,
                    "bar": None,
                    "delay_bars": None,
                    "reason": "structural plan intentionally omits a later arrival",
                }
                abandoned += 1
            else:
                outcome = {
                    "kind": ConsequenceKind.UNRESOLVED.value,
                    "bar": None,
                    "delay_bars": None,
                    "reason": "no consequence inside configured horizon",
                }
                unresolved += 1
        else:
            resolved += 1
        row["consequence"] = outcome

    prediction = [row["prediction_strength"] for row in states]
    space = [row["negative_space"] for row in states]
    intensity = [row["intensity_proxy"] for row in states]
    significance = [row["structural_significance_proxy"] for row in states]
    suspension_space = [
        row["negative_space"]
        for row in states
        if row["function"] == StructuralFunction.SUSPENSION.value
    ]
    tune_transformed = sum(bool(row["transformed_return"]) for row in states)
    explicit_pattern_returns = sum(
        bool(application.get("accepted"))
        for lock in pattern_lock_trace
        for application in lock.get("applications", ())
    )
    transformed = tune_transformed + explicit_pattern_returns
    recurrences = sum(row["recurrence_count"] > 0 for row in states)
    consequence_coverage = (
        (resolved + abandoned) / len(deviation_rows)
        if deviation_rows
        else 1.0
    )


    metrics = {
        "mean_prediction_strength": _mean(prediction),
        "learnable_returns": recurrences,
        "transformed_returns": transformed,
        "tune_transformed_returns": tune_transformed,
        "explicit_pattern_returns": explicit_pattern_returns,
        "deviations": len(deviation_rows),
        "resolved_deviations": resolved,
        "intentional_abandonments": abandoned,
        "unresolved_deviations": unresolved,
        "consequence_coverage": consequence_coverage,
        "mean_negative_space": _mean(space),
        "mean_suspension_space": _mean(suspension_space),
        "intensity_significance_correlation": _correlation(intensity, significance),
        "distinct_structural_functions": len({row["function"] for row in states}),
    }
    evaluations = {
        "learnable_material_present": any(
            row["expectation_established"] for row in states
        ),
        "expectation_forms": any(
            row["expectation_established"] for row in states[1:]
        ),
        "deviation_is_explicit": all(
            row["consequence"] is not None for row in deviation_rows
        ),
        "deviation_has_consequence": consequence_coverage == 1.0,
        "important_moments_have_space": (
            not suspension_space
            or _mean(suspension_space) >= max(0.0, _mean(space) - 0.10)
        ),
        "expression_is_structurally_directed": (
            not config.enabled
            or len({row["expressive"]["dynamic_shape"] for row in directives}) > 1
        ),
        "timbre_is_structurally_directed": (
            not config.enabled
            or len({row["timbre"]["texture"] for row in directives}) > 1
        ),
        "repetition_can_transform": (
            config.carrier != "transformed-repetition" or transformed > 0
        ),
        "intensity_is_not_significance": (
            abs(metrics["intensity_significance_correlation"]) < 0.95
        ),
        "mixed_emotional_target_declared": bool(
            config.primary_emotion
            and config.secondary_emotion
            and config.primary_emotion != config.secondary_emotion
        ),
        "form_is_not_single_fixed_template": len(_FORM_TEMPLATES) > 1,
    }

    integration_checks = {
        "plan_covers_every_bar": len(plan) == bars,
        "directives_cover_every_bar": len(directives) == bars,
        "state_covers_every_bar": len(states) == bars,
        "all_deviations_accounted_for": all(
            row["consequence"] is not None for row in deviation_rows
        ),
        "no_unresolved_major_deviations": unresolved == 0,
    }
    return {
        "version": "0.1",
        "scope": "high-level-composition-framework",
        "config": framework_config_json(config),
        "structural_plan": [function.value for function in plan],
        "bar_states": states,
        "directives": list(directives),
        "metrics": metrics,
        "evaluation": evaluations,
        "integration_validation": {
            "passed": all(integration_checks.values()),
            "checks": integration_checks,
        },
        "epistemic_boundary": (
            "Structural metrics and significance values are experimental proxies; "
            "they do not establish perceived emotion or listener preference."
        ),
        "human_validation_required": True,
    }


@dataclass(frozen=True, slots=True)
class StructuralObligation:
    obligation_id: str
    created_at_bar: int
    source_identity: str
    expected_event: str
    deviation_type: str
    importance: float
    resolution_window: str
    status: str
    resolution_type: str | None
    resolved_at_bar: int | None


def apply_framework_transformation(
    voices: Sequence[Voice],
    plan: Sequence[StructuralFunction],
    config: CompositionFrameworkConfig,
    *,
    beats_per_bar: int,
) -> tuple[tuple[Voice, ...], tuple[dict[str, Any], ...]]:
    """Apply one bounded, traceable rhythmic transformation at the first arrival.

    v0.1 deliberately keeps this narrow: one TUNE duration change is enough to
    prove that a framework directive can alter real musical material without
    inventing a broad transformation engine before the first listening test.
    """

    if not config.enabled or config.transformation_strength <= 0.0:
        return tuple(voices), ()

    try:
        arrival_bar = next(
            index for index, function in enumerate(plan)
            if function is StructuralFunction.ARRIVAL
        )
    except StopIteration:
        return tuple(voices), ()

    tune = voices[0]
    start = Fraction(arrival_bar * beats_per_bar)
    end = start + beats_per_bar
    indexes = [
        index for index, event in enumerate(tune.events)
        if start <= event.onset < end
    ]
    if not indexes:
        return tuple(voices), ()

    changed_index: int | None = None
    changed_event: NoteEvent | None = None
    operation = "held-resolution-duration-extension"

    for index in reversed(indexes):
        event = tune.events[index]
        next_onset = (
            tune.events[index + 1].onset
            if index + 1 < len(tune.events)
            else end
        )
        available = min(end, next_onset) - event.onset
        target = event.duration * (
            Fraction(1, 1)
            + Fraction(round(25 * config.transformation_strength), 100)
        )
        new_duration = min(available, target)
        if new_duration > event.duration:
            changed_index = index
            changed_event = NoteEvent(
                event.onset, new_duration, event.pitch, event.velocity
            )
            break

    if changed_index is None:
        changed_index = indexes[0]
        event = tune.events[changed_index]
        shrink = max(
            Fraction(1, 16),
            event.duration * Fraction(
                max(5, round(15 * config.transformation_strength)), 100
            ),
        )
        new_duration = max(Fraction(1, 16), event.duration - shrink)
        if new_duration == event.duration:
            return tuple(voices), ()
        operation = "arrival-rhythmic-contraction"
        changed_event = NoteEvent(
            event.onset, new_duration, event.pitch, event.velocity
        )

    before = tune.events[changed_index]
    events = list(tune.events)
    events[changed_index] = changed_event
    transformed_tune = Voice.from_events(tune.name, events)
    transformed = (transformed_tune, *voices[1:])
    trace = ({
        "bar": arrival_bar,
        "voice": tune.name,
        "operation": operation,
        "source": {
            "onset": [before.onset.numerator, before.onset.denominator],
            "duration": [before.duration.numerator, before.duration.denominator],
            "pitch": before.pitch,
        },
        "result": {
            "onset": [changed_event.onset.numerator, changed_event.onset.denominator],
            "duration": [changed_event.duration.numerator, changed_event.duration.denominator],
            "pitch": changed_event.pitch,
        },
        "identity_preserved": before.pitch == changed_event.pitch,
    },)
    return transformed, trace


def build_obligation_ledger(
    states: Sequence[dict[str, Any]],
    *,
    horizon_bars: int,
) -> tuple[StructuralObligation, ...]:
    """Turn observed deviations into explicit structural debts and outcomes."""

    obligations: list[StructuralObligation] = []
    for row in states:
        if not row["deviation"]:
            continue
        start = int(row["bar"])
        resolution_type: str | None = None
        resolved_at: int | None = None
        status = "open"
        for later in states[start + 1 : start + 1 + horizon_bars]:
            later_function = StructuralFunction(later["function"])
            if later_function is StructuralFunction.ARRIVAL or (
                later["selected_branch"] == "expected"
                and later["expectation_established"]
            ):
                resolution_type = ConsequenceKind.FULFILMENT.value
                resolved_at = int(later["bar"])
                status = "resolved"
                break
            if (
                later_function is StructuralFunction.COMPLICATION
                and later["selected_branch"] != "expected"
            ):
                resolution_type = ConsequenceKind.REDIRECTION.value
                resolved_at = int(later["bar"])
                status = "resolved"
                break

        if resolution_type is None:
            later_has_arrival = any(
                StructuralFunction(later["function"]) is StructuralFunction.ARRIVAL
                for later in states[start + 1 :]
            )
            if not later_has_arrival:
                resolution_type = ConsequenceKind.INTENTIONAL_ABANDONMENT.value
                status = "explicitly-abandoned"
            else:
                resolution_type = ConsequenceKind.UNRESOLVED.value
                status = "unresolved"

        importance = float(row["structural_significance_proxy"])
        window = (
            "short" if horizon_bars <= 2
            else "medium" if horizon_bars <= 4
            else "end-of-section"
        )
        obligations.append(StructuralObligation(
            obligation_id=f"obligation-{start:02d}",
            created_at_bar=start,
            source_identity=str(row["motif_identity"]),
            expected_event="return-to-established-behaviour-or-arrival",
            deviation_type=(
                "structural-withholding"
                if row["function"] == StructuralFunction.SUSPENSION.value
                else "structural-complication"
            ),
            importance=importance,
            resolution_window=window,
            status=status,
            resolution_type=resolution_type,
            resolved_at_bar=resolved_at,
        ))
    return tuple(obligations)
