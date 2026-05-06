import json
import pathlib
from backend.database import SessionLocal
from backend.models import Song, Playlist, SongStatus

db = SessionLocal()
playlists = db.query(Playlist).order_by(Playlist.name).all()
songs = db.query(Song).order_by(Song.playlist_id, Song.track_no).all()

out = {
    "playlists": [
        {
            "id": p.id,
            "name": p.name,
            "drive_root_name": p.drive_root_name,
            "drive_folder_id": p.drive_folder_id,
        }
        for p in playlists
    ],
    "songs": [
        {
            "id": s.id,
            "playlist_id": s.playlist_id,
            "track_no": s.track_no,
            "song_name": s.song_name,
            "artist": s.artist,
            "drive_web_link": s.drive_web_link,
            "status": s.status,
        }
        for s in songs
        if s.status == SongStatus.COMPLETED and s.drive_web_link
    ],
}
db.close()

out_path = pathlib.Path("frontend/public/data.json")
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"Exported {len(out['playlists'])} playlists, {len(out['songs'])} songs")
