from array import array
from fractions import Fraction

from ipm.experiment_audio import (
    _fit_frames,
    _slice_shifted_events,
    sample_boundaries,
    scale_pcm,
    shared_peak_gain,
)
from ipm.model import NoteEvent


def _pcm(*values: int) -> bytes:
    return array("h", values).tobytes()


def test_sample_boundaries_use_one_cumulative_timeline():
    assert sample_boundaries(
        tempo_bpm=58,
        beats_per_bar=4,
        bars=8,
        target_bar=4,
    ) == (729931, 912414, 1459862)


def test_segment_slice_rebases_events_and_rejects_boundary_crossing():
    events = (
        NoteEvent(Fraction(15), Fraction(1, 2), 60, 70),
        NoteEvent(Fraction(16), Fraction(3, 4), 62, 74),
        NoteEvent(Fraction(20), Fraction(1, 2), 64, 74),
    )
    target = _slice_shifted_events(events, start=Fraction(16), end=Fraction(20))
    assert target == (NoteEvent(Fraction(0), Fraction(3, 4), 62, 74),)


def test_fit_frames_crops_and_zero_pads_stereo_s16():
    one_frame = _pcm(100, -100)
    assert _fit_frames(one_frame * 3, 2) == one_frame * 2
    assert _fit_frames(one_frame, 3) == one_frame + bytes(8)


def test_shared_gain_applied_to_reused_pcm_keeps_it_bit_identical():
    shared_prefix = _pcm(1000, -1000, 2000, -2000)
    shared_suffix = _pcm(1500, -1500, 2500, -2500)
    targets = (
        _pcm(3000, -3000),
        _pcm(4000, -4000),
        _pcm(5000, -5000),
    )
    gain = shared_peak_gain((shared_prefix, shared_suffix, *targets))
    prefix = scale_pcm(shared_prefix, gain)
    suffix = scale_pcm(shared_suffix, gain)
    assembled = tuple(prefix + scale_pcm(target, gain) + suffix for target in targets)

    prefix_bytes = len(prefix)
    suffix_bytes = len(suffix)
    assert len({item[:prefix_bytes] for item in assembled}) == 1
    assert len({item[-suffix_bytes:] for item in assembled}) == 1
    assert len({item[prefix_bytes:-suffix_bytes] for item in assembled}) == 3
