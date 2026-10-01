from ipm.emotional_vocabulary import (
    CATEGORIES,
    INTERACTION_RULES,
    TENDENCIES,
    tendencies_for_target,
    validate_vocabulary,
)


def test_emotional_vocabulary_covers_every_required_lower_level_category():
    assert validate_vocabulary()
    assert {item.category for item in TENDENCIES} == set(CATEGORIES)


def test_all_emotional_mappings_are_explicitly_hypotheses():
    assert all(item.confidence == "hypothesis" for item in TENDENCIES)


def test_target_lookup_preserves_category_diversity():
    selected = tendencies_for_target("tenderness", "uncertainty", limit=8)
    assert len(selected) == 8
    assert len({item.category for item in selected}) >= 6


def test_interaction_rules_keep_intensity_separate_from_significance():
    joined = " ".join(INTERACTION_RULES).lower()
    assert "intensity" in joined
    assert "significance" in joined
    assert "random jitter" in joined
