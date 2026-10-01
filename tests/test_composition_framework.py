from fractions import Fraction

from ipm.composition_framework import (
    CompositionFrameworkConfig,
    StructuralFunction,
    apply_structural_expression,
    build_directives,
    build_structural_plan,
    framework_activity_probability,
)
from ipm.engine import InstrumentConfig, compose
from ipm.model import NoteEvent, Voice


def test_structural_plan_is_deterministic_but_not_one_fixed_formula():
    config = CompositionFrameworkConfig()
    first = build_structural_plan(16, config, seed=1)
    again = build_structural_plan(16, config, seed=1)
    other = build_structural_plan(16, config, seed=2)
    assert first == again
    assert first != other


def test_structural_plan_can_repeat_or_omit_functions():
    repeated = build_structural_plan(
        16,
        CompositionFrameworkConfig(
            structural_override=("introduction", "recognition", "recognition", "aftermath")
        ),
        seed=1,
    )
    assert repeated.count(StructuralFunction.RECOGNITION) > 1
    denied = build_structural_plan(
        16,
        CompositionFrameworkConfig(carrier="denied-expectation"),
        seed=1,
    )
    assert StructuralFunction.ARRIVAL not in denied


def test_framework_density_shaping_preserves_activity_endpoints():
    for function in StructuralFunction:
        assert framework_activity_probability(
            0.0, 0.8, function, enabled=True
        ) == 0.0
        assert framework_activity_probability(
            1.0, 1.4, function, enabled=True
        ) == 1.0


def test_negative_space_control_scales_suspension_thinning():
    weak = framework_activity_probability(
        0.5,
        1.0,
        StructuralFunction.SUSPENSION,
        enabled=True,
        negative_space_strength=0.0,
    )
    strong = framework_activity_probability(
        0.5,
        1.0,
        StructuralFunction.SUSPENSION,
        enabled=True,
        negative_space_strength=1.0,
    )
    assert strong < weak


def test_structural_expression_is_deterministic_and_preserves_note_identity():
    voice = Voice.from_events(
        "TUNE",
        (
            NoteEvent(Fraction(0), Fraction(1), 60, 70),
            NoteEvent(Fraction(4), Fraction(1), 62, 70),
        ),
    )
    config = CompositionFrameworkConfig(enabled=True, expressive_gesture=1.0)
    plan = (StructuralFunction.SUSPENSION, StructuralFunction.ARRIVAL)
    left = apply_structural_expression(
        (voice,), plan, config, beats_per_bar=4
    )[0]
    right = apply_structural_expression(
        (voice,), plan, config, beats_per_bar=4
    )[0]
    assert left.events == right.events
    assert [(e.onset, e.duration, e.pitch) for e in left.events] == [
        (e.onset, e.duration, e.pitch) for e in voice.events
    ]
    assert [e.velocity for e in left.events] != [e.velocity for e in voice.events]


def test_quiet_arrival_does_not_encode_climax_as_maximum_velocity():
    voice = Voice.from_events(
        "TUNE",
        (
            NoteEvent(Fraction(0), Fraction(1), 60, 70),
            NoteEvent(Fraction(4), Fraction(1), 62, 70),
        ),
    )

    config = CompositionFrameworkConfig(enabled=True, expressive_gesture=1.0)
    plan = (StructuralFunction.COMPLICATION, StructuralFunction.ARRIVAL)
    rendered = apply_structural_expression(
        (voice,), plan, config, beats_per_bar=4
    )[0]
    assert rendered.events[1].velocity < rendered.events[0].velocity


def test_directives_make_expression_and_timbre_structural():
    plan = (
        StructuralFunction.INTRODUCTION,
        StructuralFunction.SUSPENSION,
        StructuralFunction.ARRIVAL,
    )
    directives = build_directives(plan, CompositionFrameworkConfig())
    assert len(directives) == len(plan)
    assert len({row["expressive"]["dynamic_shape"] for row in directives}) > 1
    assert len({row["timbre"]["texture"] for row in directives}) > 1
    assert all(row["timbre"]["identity"] == "restrained-evolving" for row in directives)


def test_engine_trace_contains_integrated_framework_state():
    result = compose(
        InstrumentConfig(
            bars=8,
            framework=CompositionFrameworkConfig(
                enabled=True,
                primary_emotion="warmth",
                secondary_emotion="uncertainty",
            ),
        )
    )
    framework = result.trace["composition_framework"]
    assert result.trace["validation"]["checks"]["composition_framework_integrated"]
    assert framework["version"] == "0.1"
    assert len(framework["structural_plan"]) == 8
    assert len(framework["bar_states"]) == 8
    assert len(framework["directives"]) == 8
    assert framework["integration_validation"]["passed"]
    assert framework["human_validation_required"]


def test_framework_records_expectation_deviation_and_consequence_without_claiming_emotion():
    result = compose(InstrumentConfig(bars=16))
    framework = result.trace["composition_framework"]
    metrics = framework["metrics"]
    assert 0.0 <= metrics["mean_prediction_strength"] <= 1.0
    assert 0.0 <= metrics["consequence_coverage"] <= 1.0
    assert 0.0 <= metrics["mean_negative_space"] <= 1.0
    assert "experimental proxies" in framework["epistemic_boundary"]
    for row in framework["bar_states"]:
        if row["deviation"]:
            assert row["consequence"] is not None


def test_framework_enabled_generation_is_reproducible():
    config = InstrumentConfig(
        bars=8,
        framework=CompositionFrameworkConfig(
            enabled=True,
            carrier="space",
            primary_emotion="tenderness",
            secondary_emotion="restraint",
        ),
    )
    left = compose(config)
    right = compose(config)
    assert left.voices == right.voices
    assert left.trace["composition_framework"] == right.trace["composition_framework"]


def test_framework_can_be_disabled_without_density_reinterpretation():
    disabled = CompositionFrameworkConfig(enabled=False)
    plan = build_structural_plan(8, disabled, seed=3)
    for function in set(plan):
        probability = framework_activity_probability(
            0.4, 1.2, function, enabled=False
        )
        assert probability == 0.4 ** 1.2


def test_framework_default_is_off_for_backward_compatibility():
    assert not CompositionFrameworkConfig().enabled


def test_framework_on_with_zero_interventions_preserves_underlying_music():
    base = InstrumentConfig(
        seed=202610011,
        bars=8,
        framework=CompositionFrameworkConfig(enabled=False),
    )
    neutral = InstrumentConfig(
        seed=202610011,
        bars=8,
        framework=CompositionFrameworkConfig(
            enabled=True,
            negative_space=0.0,
            expressive_gesture=0.0,
            transformation_strength=0.0,
        ),
    )
    assert compose(base).voices == compose(neutral).voices


def test_framework_active_intervention_changes_real_musical_output():
    control = compose(InstrumentConfig(seed=202610012, bars=8,
        framework=CompositionFrameworkConfig(enabled=False)))
    framework = compose(InstrumentConfig(seed=202610012, bars=8,
        framework=CompositionFrameworkConfig(
            enabled=True, negative_space=1.0, expressive_gesture=1.0,
            transformation_strength=1.0,
            structural_override=(
                "introduction", "recognition", "complication",
                "suspension", "arrival", "aftermath",
            ),
        )))
    assert control.voices != framework.voices
    trace = framework.trace["composition_framework"]
    assert trace["transformations"]
    assert trace["metrics"]["actual_transformations"] >= 1


def test_obligation_ledger_accounts_for_every_detected_deviation():
    result = compose(InstrumentConfig(seed=202610013, bars=12,
        framework=CompositionFrameworkConfig(
            enabled=True, negative_space=0.9,
            expressive_gesture=0.5, transformation_strength=0.5,
        )))
    framework = result.trace["composition_framework"]
    assert len(framework["obligation_ledger"]) == framework["metrics"]["deviations"]
    assert framework["integration_validation"]["checks"]["obligation_ledger_complete"]
    for obligation in framework["obligation_ledger"]:
        assert obligation["status"] in {
            "resolved", "explicitly-abandoned", "unresolved"
        }
        assert obligation["resolution_window"] in {
            "short", "medium", "end-of-section"
        }
