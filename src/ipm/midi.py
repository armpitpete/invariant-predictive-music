"""Minimal dependency-free Standard MIDI File writer for IPM studies."""

from __future__ import annotations

from typing import Sequence

from .model import Beat, Voice


def _vlq(value: int) -> bytes:
    if value < 0:
        raise ValueError("variable-length quantity cannot be negative")
    buffer = value & 0x7F
    encoded = bytearray([buffer])
    value >>= 7
    while value:
        buffer = (value & 0x7F) | 0x80
        encoded.insert(0, buffer)
        value >>= 7
    return bytes(encoded)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    if len(kind) != 4:
        raise ValueError("MIDI chunk type must contain four bytes")
    return kind + len(payload).to_bytes(4, "big") + payload


def _beat_to_ticks(value: Beat, ppq: int) -> int:
    ticks = value * ppq
    if ticks.denominator != 1:
        raise ValueError("beat value cannot be represented exactly at the requested PPQ")
    return ticks.numerator


def _track(events: Sequence[tuple[int, int, bytes]]) -> bytes:
    ordered = sorted(events, key=lambda item: (item[0], item[1]))
    payload = bytearray()
    cursor = 0
    for tick, _, message in ordered:
        if tick < cursor:
            raise ValueError("MIDI events must be time-ordered")
        payload.extend(_vlq(tick - cursor))
        payload.extend(message)
        cursor = tick
    payload.extend(_vlq(0))
    payload.extend(b"\xFF\x2F\x00")
    return _chunk(b"MTrk", bytes(payload))


def _tempo_track(tempo_bpm: int, beats_per_bar: int) -> bytes:
    if tempo_bpm <= 0:
        raise ValueError("tempo_bpm must be positive")
    if beats_per_bar <= 0 or beats_per_bar > 255:
        raise ValueError("beats_per_bar must be in 1..255")
    microseconds = round(60_000_000 / tempo_bpm)
    if not 0 < microseconds < 1 << 24:
        raise ValueError("tempo is outside MIDI tempo-event range")
    events = [
        (0, 0, b"\xFF\x03\x09IPM Study"),
        (0, 1, b"\xFF\x51\x03" + microseconds.to_bytes(3, "big")),
        (0, 2, b"\xFF\x58\x04" + bytes((beats_per_bar, 2, 24, 8))),
    ]
    return _track(events)


def _voice_track(
    voice: Voice,
    *,
    channel: int,
    ppq: int,
    program: int = 0,
) -> bytes:
    if not 0 <= channel <= 15:
        raise ValueError("MIDI channel must be in 0..15")
    if not 0 <= program <= 127:
        raise ValueError("MIDI program must be in 0..127")
    name = voice.name.encode("ascii")
    if len(name) > 127:
        raise ValueError("track name is too long")

    events: list[tuple[int, int, bytes]] = [
        (0, 0, b"\xFF\x03" + bytes((len(name),)) + name),
        (0, 1, bytes((0xC0 | channel, program))),
    ]
    for event in voice.events:
        start = _beat_to_ticks(event.onset, ppq)
        end = _beat_to_ticks(event.end, ppq)
        # Note-offs sort before note-ons at the same tick to preserve monophonic adjacency.
        events.append((start, 3, bytes((0x90 | channel, event.pitch, event.velocity))))
        events.append((end, 2, bytes((0x80 | channel, event.pitch, 0))))
    return _track(events)


def render_midi(
    voices: Sequence[Voice],
    *,
    tempo_bpm: int = 88,
    beats_per_bar: int = 4,
    ppq: int = 480,
) -> bytes:
    """Render one format-1 MIDI file with a tempo track plus one track per voice."""

    if ppq <= 0 or ppq > 0x7FFF:
        raise ValueError("ppq must be in 1..32767")
    if len(voices) > 15:
        raise ValueError("reference writer supports at most 15 pitched voice tracks")

    tracks = [_tempo_track(tempo_bpm, beats_per_bar)]
    for channel, voice in enumerate(voices):
        tracks.append(_voice_track(voice, channel=channel, ppq=ppq))

    header = (
        (1).to_bytes(2, "big")
        + len(tracks).to_bytes(2, "big")
        + ppq.to_bytes(2, "big")
    )
    return _chunk(b"MThd", header) + b"".join(tracks)
