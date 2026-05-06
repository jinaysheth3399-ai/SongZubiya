"""Confidence scoring for YouTube candidates against the expected song.

Returns a 0-100 integer. The scoring rules are taken directly from the PRD.
"""
from __future__ import annotations

import re
from rapidfuzz import fuzz


# Modifiers the user can request as part of the song name.
# If the requested song contains the modifier, we reward a candidate that also has it.
# We also do NOT penalize the modifier-related "negative" keywords if the user asked for them.
MODIFIER_KEYWORDS = [
    "instrumental",
    "piano",
    "violin",
    "remix",
    "cover",
    "clean",
]

OFFICIAL_KEYWORDS = ["official", "audio", "video", "official audio", "official video"]


# Penalty terms: keyword -> penalty value. Applied unless excused by a requested modifier.
PENALTIES: dict[str, int] = {
    "reaction": 50,
    "tutorial": 40,
    "lesson": 40,
    "karaoke": 30,
    "lyrics": 20,
    "slowed": 25,
    "reverb": 25,
    "live": 20,
    "playlist": 35,
    "mix": 35,
    "shorts": 30,
}


def _norm(s: str | None) -> str:
    return (s or "").lower()


def _contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _parse_duration_to_seconds(duration: str | None) -> int | None:
    """Parse common YouTube duration strings: 'M:SS', 'H:MM:SS', 'PT3M21S', etc."""
    if not duration:
        return None
    d = duration.strip()
    # ISO-8601 e.g. PT3M21S
    iso = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d)
    if iso:
        h, m, s = (int(g) if g else 0 for g in iso.groups())
        return h * 3600 + m * 60 + s
    # Colon-separated
    if ":" in d:
        parts = [p for p in d.split(":") if p.isdigit()]
        if 2 <= len(parts) <= 3:
            parts = [int(p) for p in parts]
            if len(parts) == 2:
                m, s = parts
                return m * 60 + s
            h, m, s = parts
            return h * 3600 + m * 60 + s
    # Bare seconds
    if d.isdigit():
        return int(d)
    return None


def calculate_match_score(
    expected_song: str,
    expected_artist: str,
    youtube_title: str,
    channel_name: str,
    duration: str | None,
) -> int:
    """Confidence score 0-100 for a candidate against the expected song.

    Rules per PRD §12: positive points for fuzzy song/artist match, requested
    modifier match, official keywords, and a valid duration; negative points
    for misleading keywords (reaction, tutorial, etc.) — but never for a
    modifier the user explicitly asked for.
    """
    expected_song = expected_song or ""
    expected_artist = expected_artist or ""
    youtube_title = youtube_title or ""
    channel_name = channel_name or ""

    title_n = _norm(youtube_title)
    channel_n = _norm(channel_name)
    song_n = _norm(expected_song)
    artist_n = _norm(expected_artist)

    score = 0

    # +Song fuzzy match — token_set_ratio is robust to extra words like "(Official Video)"
    song_ratio = fuzz.token_set_ratio(song_n, title_n) if song_n else 0
    score += int(round((song_ratio / 100.0) * 50))

    # +Artist fuzzy match — match against title OR channel, take max.
    # The user's "artist" field is sometimes descriptive ("Bollywood Violin Cover",
    # "Pritam Instrumental") rather than a literal artist name, so this contributes
    # less than the song-name match and is bonus-only (no penalty for mismatch).
    if artist_n:
        artist_ratio = max(
            fuzz.token_set_ratio(artist_n, title_n),
            fuzz.token_set_ratio(artist_n, channel_n),
        )
        score += int(round((artist_ratio / 100.0) * 15))

    # +Requested modifier match (instrumental/piano/violin/remix/cover/clean).
    # Reward each modifier that the user asked for and that the title actually has.
    requested_modifiers = {m for m in MODIFIER_KEYWORDS if _contains_word(song_n, m)}
    if requested_modifiers:
        matched_modifiers = sum(1 for m in requested_modifiers if _contains_word(title_n, m))
        if matched_modifiers:
            # Up to 20 points: 15 base + 5 if every requested modifier matched.
            bonus = 15 + (5 if matched_modifiers == len(requested_modifiers) else 0)
            score += bonus

    # +Official/audio/video keyword
    if any(_contains_word(title_n, k.replace(" ", " ")) for k in OFFICIAL_KEYWORDS):
        score += 10

    # +Valid duration in a reasonable range (60s - 15min)
    secs = _parse_duration_to_seconds(duration)
    if secs is not None and 60 <= secs <= 15 * 60:
        score += 10

    # -Penalties (skip if the user requested that modifier)
    for keyword, penalty in PENALTIES.items():
        if keyword in requested_modifiers:
            continue
        if _contains_word(title_n, keyword):
            score -= penalty

    # Clamp
    if score < 0:
        score = 0
    if score > 100:
        score = 100
    return score
