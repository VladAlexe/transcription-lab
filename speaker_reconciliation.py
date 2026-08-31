from __future__ import annotations
from collections import Counter, defaultdict
from models import TranscriptSegment


def initialize_mapping(segments: list[TranscriptSegment]) -> dict[str, str]:
    return {speaker: speaker for speaker in sorted({s.speaker_id for s in segments})}


def apply_speaker_mapping(segment: TranscriptSegment, mapping: dict[str, str]) -> str:
    return mapping.get(segment.speaker_id, segment.speaker_id).strip() or segment.speaker_id


def speaker_statistics(segments: list[TranscriptSegment]) -> dict[str, tuple[int, float]]:
    counts: Counter[str] = Counter(); durations: defaultdict[str, float] = defaultdict(float)
    for item in segments: counts[item.speaker_id] += 1; durations[item.speaker_id] += max(0, item.absolute_end-item.absolute_start)
    return {key: (counts[key], durations[key]) for key in sorted(counts)}
