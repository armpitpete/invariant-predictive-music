"""Experimental lower-level emotional vocabulary for Composition Framework v0.1.

These are compositional hypotheses and tendencies, not universal mappings from
musical features to emotion. Listener testing decides whether any tendency
survives.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmotionalTendency:
    category: str
    device: str
    tends_toward: tuple[str, ...]
    rationale: str
    confidence: str = "hypothesis"


CATEGORIES = (
    "interval",
    "harmony",
    "voicing",
    "rhythm",
    "phrase",
    "articulation",
    "register",
    "timbre",
    "dynamics",
    "silence-density",
)


TENDENCIES: tuple[EmotionalTendency, ...] = (
    EmotionalTendency(
        "interval", "small-step approach to a target",
        ("tenderness", "vulnerability", "longing"),
        "Creates directional pull without requiring a large dramatic leap.",
    ),
    EmotionalTendency(
        "interval", "open fourth/fifth with sparse context",
        ("distance", "calm", "uncertainty"),
        "Leaves more harmonic interpretation open than a tightly defined sonority.",
    ),

    EmotionalTendency(
        "harmony", "delay an otherwise prepared resolution",
        ("longing", "uncertainty", "anticipation"),
        "Extends prediction before fulfilment.",
    ),
    EmotionalTendency(
        "harmony", "resolve by common-tone continuity",
        ("warmth", "security", "tenderness"),
        "Preserves identity while changing harmonic interpretation.",
    ),
    EmotionalTendency(
        "voicing", "widen upper voices while keeping a stable anchor",
        ("openness", "distance", "hope"),
        "Changes perceived space without demanding greater loudness.",
    ),
    EmotionalTendency(
        "voicing", "close inner voices with restrained bass motion",
        ("intimacy", "tenderness", "restraint"),
        "Concentrates attention without automatically increasing intensity.",
    ),
    EmotionalTendency(
        "rhythm", "stable pulse with one delayed expected attack",
        ("anticipation", "uncertainty"),
        "Builds a learned timing expectation and violates it locally.",
    ),
    EmotionalTendency(
        "rhythm", "reduce attacks before an important event",
        ("suspension", "vulnerability", "attention"),
        "Uses negative space to increase event significance.",
    ),

    EmotionalTendency(
        "phrase", "extend the final note of a prepared phrase",
        ("release", "tenderness", "arrival"),
        "Lets the consequence occupy more perceptual time.",
    ),
    EmotionalTendency(
        "phrase", "truncate a repeated phrase before its usual ending",
        ("unease", "uncertainty", "interruption"),
        "Withholds a learned completion without adding new material.",
    ),
    EmotionalTendency(
        "articulation", "soft attack with late-onset vibrato",
        ("vulnerability", "tenderness", "restraint"),
        "Separates note arrival from later expressive movement.",
    ),
    EmotionalTendency(
        "articulation", "selective portamento into destination notes",
        ("longing", "intimacy"),
        "Makes approach behaviour part of the phrase rather than random pitch drift.",
    ),
    EmotionalTendency(
        "register", "gradual rise followed by a lower quiet return",
        ("reaching", "release", "aftermath"),
        "Creates directional history without equating height with final importance.",
    ),
    EmotionalTendency(
        "register", "hold a narrow register through a dense section",
        ("restraint", "tension"),
        "Prevents automatic escalation by range expansion.",
    ),

    EmotionalTendency(
        "timbre", "slowly brighten a stable core spectrum",
        ("hope", "opening", "movement"),
        "Lets timbral evolution carry form while preserving sonic identity.",
    ),
    EmotionalTendency(
        "timbre", "reduce high-frequency detail during suspension",
        ("distance", "uncertainty", "restraint"),
        "Makes withdrawal a timbral event rather than just a volume change.",
    ),
    EmotionalTendency(
        "dynamics", "quiet emphasis at arrival",
        ("tenderness", "relief", "intimacy"),
        "Tests significance independently of maximum loudness.",
    ),
    EmotionalTendency(
        "dynamics", "small phrase-level swells tied to destinations",
        ("reaching", "release"),
        "Connects dynamic change to musical direction instead of random variation.",
    ),
    EmotionalTendency(
        "silence-density", "thin subsidiary layers before payoff",
        ("anticipation", "attention", "vulnerability"),
        "Protects the important event with contrast.",
    ),
    EmotionalTendency(
        "silence-density", "leave residual space after payoff",
        ("aftermath", "reflection", "calm"),
        "Allows the event to have a consequence rather than immediately resetting.",
    ),
)


INTERACTION_RULES: tuple[str, ...] = (
    "Do not infer emotion from one feature in isolation.",
    "Prefer two or three mutually compatible tendencies over stacking every cue.",
    "Expectation must be learned before a deviation can function as a deviation.",
    "A timbral change should preserve enough identity for the listener to recognise continuity.",
    "Silence and density changes must not force weak notes merely to satisfy a target.",
    "Intensity, register height and spectral brightness remain separate from significance.",
    "Humanisation must follow phrase function; random jitter is not evidence of expression.",
    "Conflicting emotional targets are allowed and should remain traceable.",
)


def validate_vocabulary() -> bool:
    represented = {item.category for item in TENDENCIES}
    return represented == set(CATEGORIES) and all(
        item.confidence == "hypothesis" for item in TENDENCIES
    )


def tendencies_for_target(
    primary: str,
    secondary: str,
    *,
    limit: int = 8,
) -> tuple[EmotionalTendency, ...]:
    """Return relevant hypotheses while preserving category diversity."""

    targets = {primary.lower(), secondary.lower()}
    ranked = sorted(
        TENDENCIES,
        key=lambda item: (
            -len(targets.intersection(word.lower() for word in item.tends_toward)),
            CATEGORIES.index(item.category),
            item.device,
        ),
    )

    chosen: list[EmotionalTendency] = []
    used_categories: set[str] = set()
    for item in ranked:
        if item.category not in used_categories:
            chosen.append(item)
            used_categories.add(item.category)
        if len(chosen) >= limit:
            break
    if len(chosen) < limit:
        for item in ranked:
            if item not in chosen:
                chosen.append(item)
            if len(chosen) >= limit:
                break
    return tuple(chosen)
