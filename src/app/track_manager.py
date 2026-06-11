import random


def resolve_selection(tag_data: dict, general: dict) -> tuple[bool, bool]:
    """Resolve the effective (shuffle, autoplay) flags for a tag.

    A tag may override either flag; otherwise the global ``track_selection``
    defaults from the ``general`` config apply.
    """
    defaults = general.get("track_selection", {})
    shuffle = tag_data.get("shuffle", defaults.get("shuffle", False))
    autoplay = tag_data.get("autoplay", defaults.get("autoplay", False))
    return shuffle, autoplay


class TrackManager:
    def __init__(self):
        self._cache = {}

    def select_next_piece(
        self, tag_id: str, tag_data: dict, shuffle: bool = False
    ) -> dict | None:
        tracks = tag_data.get("tracks", [])
        if not tracks:
            return None

        if shuffle and len(tracks) > 1:
            return random.choice(tracks)

        idx = self._cache.get(tag_id, 0)

        if idx >= len(tracks):
            idx = 0

        piece = tracks[idx]

        if len(tracks) > 1:
            self._cache[tag_id] = (idx + 1) % len(tracks)

        return piece

    def prepare(self, tag_id: str, tag_data: dict, general: dict) -> dict | None:
        """Build a playback plan for a tag.

        With ``autoplay`` enabled the whole track list is played in sequence
        (optionally shuffled). Otherwise the legacy round-robin behavior is
        kept: a single piece is selected per request using the cached state.
        """
        tracks = tag_data.get("tracks", [])
        if not tracks:
            return None

        shuffle, autoplay = resolve_selection(tag_data, general)

        if autoplay:
            return {
                "autoplay": True,
                "shuffle": shuffle,
                "pieces": tracks,
                "track_info": tracks[0],
            }

        piece = self.select_next_piece(tag_id, tag_data, shuffle)
        return {
            "autoplay": False,
            "shuffle": shuffle,
            "track_info": piece,
        }
