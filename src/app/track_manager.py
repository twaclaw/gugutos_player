class TrackManager:
    def __init__(self):
        self._cache = {}

    def select_next_piece(self, tag_id: str, tag_data: dict) -> dict | None:
        tracks = tag_data.get("tracks", [])
        if not tracks:
            return None

        idx = self._cache.get(tag_id, 0)

        if idx >= len(tracks):
            idx = 0

        piece = tracks[idx]

        if len(tracks) > 1:
            self._cache[tag_id] = (idx + 1) % len(tracks)

        return piece
