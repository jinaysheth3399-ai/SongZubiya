"""Seeds the database with the fixed playlist + song dataset from the PRD.

Idempotent: re-running will not duplicate existing songs. New songs are added,
existing ones are left alone (so manual review choices are preserved).

Run:  python -m backend.seed_data
"""
from __future__ import annotations

import sys
from typing import Iterable

from backend.database import SessionLocal, init_db
from backend.models import Playlist, Song, SongStatus


# Songs are organized by Drive root folder name -> playlist name -> tracks.
# When you add a new top-level dataset, just add a new key under PLAYLIST_GROUPS;
# the runner will create/find that root folder in Drive automatically.
PLAYLIST_GROUPS: dict[str, dict[str, list[tuple[str, str, str]]]] = {}

PLAYLIST_GROUPS["Playlist 3"] = {
    "02_Lunch_Energy_12PM-130PM": [
        ("01", "Tum Hi Ho (Violin)", "Bollywood Violin Cover"),
        ("02", "Ae Dil Hai Mushkil (Piano)", "Pritam Instrumental"),
        ("03", "Hawayein (Instrumental)", "Pritam Instrumental"),
        ("04", "Phir Bhi Tumko Chaahunga (Piano)", "Bollywood Piano"),
        ("05", "Kesariya (Piano)", "Pritam Instrumental"),
        ("06", "Apna Bana Le (Piano)", "Bollywood Piano"),
        ("07", "Maan Meri Jaan (Piano)", "King Instrumental"),
        ("08", "Tera Ban Jaunga (Violin)", "Bollywood Violin"),
        ("09", "Shayad (Piano)", "Pritam Instrumental"),
        ("10", "Ve Kamleya (Instrumental)", "Pritam"),
        ("11", "Chaleya (Instrumental)", "Pritam / Arijit"),
        ("12", "Dil Diyan Gallan (Piano)", "Bollywood Piano"),
        ("13", "A Walk", "Tycho"),
        ("14", "Nuvole Bianche", "Ludovico Einaudi"),
        ("15", "River Flows in You", "Yiruma"),
        ("16", "Experience", "Ludovico Einaudi"),
        ("17", "Gymnopédie No.1", "Erik Satie"),
        ("18", "Weightless", "Marconi Union"),
        ("19", "Clair de Lune", "Debussy"),
        ("20", "Arrival of the Birds", "The Cinematic Orchestra"),
    ],
    "03_Afternoon_SlumpBuster_130PM-330PM": [
        ("01", "Malhari (Instrumental)", "Vishal-Shekhar"),
        ("02", "Khalibali (Instrumental)", "Shivam Pathak"),
        ("03", "Radha (Instrumental)", "Pritam"),
        ("04", "Disco Deewane (Instrumental)", "Shankar-Ehsaan-Loy"),
        ("05", "Swag Se Swagat (Instrumental)", "Vishal-Shekhar"),
        ("06", "Tattad Tattad (Instrumental)", "Bollywood"),
        ("07", "Dil Dhadakne Do (Title Instrumental)", "Shankar-Ehsaan-Loy"),
        ("08", "Zingaat (Instrumental)", "Ajay-Atul"),
        ("09", "Nachdi Phira (Instrumental)", "Bollywood"),
        ("10", "Happy", "Pharrell Williams"),
        ("11", "Don't Stop Me Now", "Queen"),
        ("12", "Shut Up and Dance", "Walk The Moon"),
        ("13", "I Gotta Feeling", "Black Eyed Peas"),
        ("14", "Can't Stop the Feeling", "Justin Timberlake"),
        ("15", "Uptown Funk (Clean)", "Bruno Mars"),
    ],
    "04_Peak_Productivity_330PM-530PM": [
        ("01", "Udd Gaye", "Ritviz"),
        ("02", "Sage", "Ritviz"),
        ("03", "Liggi", "Ritviz"),
        ("04", "Chalo Chalein", "Ritviz"),
        ("05", "Jeet", "Ritviz"),
        ("06", "Barso", "Ritviz"),
        ("07", "Pasoori (Instrumental)", "Coke Studio Instrumental"),
        ("08", "Amplifier (Instrumental)", "Bollywood Instrumental"),
        ("09", "Apna Bana Le (Instrumental)", "Bollywood Piano"),
        ("10", "Kesariya (Instrumental)", "Bollywood Instrumental"),
        ("11", "Maan Meri Jaan (Instrumental)", "King Instrumental"),
        ("12", "Say My Name", "ODESZA"),
        ("13", "Sunset Lover", "Petit Biscuit"),
        ("14", "Innerbloom", "RÜFÜS DU SOL"),
        ("15", "Kerala", "Bonobo"),
        ("16", "Something About Us", "Daft Punk"),
        ("17", "Midnight City", "M83"),
        ("18", "Higher Ground", "ODESZA"),
    ],
    "05_AfroHouse_Sunset_530PM-700PM": [
        ("01", "Khairiyat (Piano)", "Bollywood Piano"),
        ("02", "Shayad (Instrumental)", "Bollywood Instrumental"),
        ("03", "Raataan Lambiyan (Instrumental)", "Bollywood Instrumental"),
        ("04", "Qaafirana (Instrumental)", "Bollywood Piano"),
        ("05", "Husn", "Anuv Jain"),
        ("06", "Nadaaniyan", "Anuv Jain"),
        ("07", "Joy of Little Things", "When Chai Met Toast"),
        ("08", "cold/mess", "Prateek Kuhad"),
        ("09", "Kasoor", "Prateek Kuhad"),
        ("10", "Baarishein", "Anuv Jain"),
        ("11", "Firefly", "When Chai Met Toast"),
        ("12", "Blush", "Taba Chake"),
        ("13", "Resonance", "Home"),
        ("14", "Daydream", "Tycho"),
        ("15", "Electric Feel", "MGMT"),
        ("16", "A Real Hero", "College & Electric Youth"),
        ("17", "Ghostwriter", "RJD2"),
        ("18", "Pelota", "Khruangbin"),
    ],
    "06_AfroHouse_Sunset_530PM-700PM": [
        ("01", "Return to Oz (ARTBAT Remix)", "Monolink"),
        ("02", "Sirens", "Monolink"),
        ("03", "Father Ocean", "Monolink"),
        ("04", "Burning Sun", "Monolink"),
        ("05", "On My Knees (Adriatique Remix)", "RÜFÜS DU SOL"),
        ("06", "Miracle", "WhoMadeWho & Adriatique"),
        ("07", "Silence & Secrets (Adriatique Remix)", "WhoMadeWho"),
        ("08", "We Dance Again", "Black Coffee feat. Nakhane Toure"),
        ("09", "10 Missed Calls", "Black Coffee & Pharrell"),
        ("10", "Drive", "Black Coffee & David Guetta"),
        ("11", "Reflections", "Monolink"),
        ("12", "Beyond Us", "Adriatique & Eynka"),
        ("13", "Hypnotica", "Adriatique"),
        ("14", "The Prey (Mind Against Remix)", "Monolink"),
        ("15", "Desire", "Adriatique & Marino Canal"),
    ],
    "07_AfroHouse_Exit_700PM-800PM": [
        ("01", "Rearrange My Mind", "Monolink"),
        ("02", "Superman", "Black Coffee"),
        ("03", "Wish You Were Here", "Black Coffee & Msaki"),
        ("04", "Mesmerized", "Monolink"),
        ("05", "Miracle (RÜFÜS DU SOL Remix)", "WhoMadeWho & Adriatique"),
        ("06", "With You", "Adriatique & GORDO"),
        ("07", "SBCNCSLY", "Black Coffee & Sabrina Claudio"),
        ("08", "Under Darkening Skies", "Monolink"),
        ("09", "Swallow", "Monolink"),
        ("10", "Changing Colors", "Adriatique"),
        ("11", "The Prayer", "Themba"),
        ("12", "Gratitude", "Themba"),
    ],
}

PLAYLIST_GROUPS["Playlist 4"] = {
    "01_Morning_Focus_10AM-12PM": [
        ("01", "Tum Hi Ho (Piano)", "Bollywood Piano Cover"),
        ("02", "Channa Mereya (Violin)", "Bollywood Violin"),
        ("03", "Agar Tum Saath Ho (Flute)", "Bollywood Flute"),
        ("04", "Ilahi (Instrumental)", "Bollywood Instrumental"),
        ("05", "Tujhe Kitna Chahne Lage (Piano)", "Bollywood Piano"),
        ("06", "Kabira (Piano)", "Bollywood Instrumental"),
        ("07", "Kun Faya Kun (Instrumental)", "A.R. Rahman"),
        ("08", "Dil Se Re (Instrumental)", "A.R. Rahman"),
        ("09", "Tere Bina (Instrumental)", "A.R. Rahman"),
        ("10", "Naina Da Kya Kasoor (Instrumental)", "Amit Trivedi"),
        ("11", "Phir Le Aya Dil (Instrumental)", "Bollywood Instrumental"),
        ("12", "Afreen Afreen (Instrumental)", "Coke Studio Instrumental"),
        ("13", "Comptine d'un Autre Été", "Yann Tiersen"),
        ("14", "Time (Piano)", "Hans Zimmer"),
        ("15", "Divenire", "Ludovico Einaudi"),
        ("16", "I Giorni", "Ludovico Einaudi"),
        ("17", "Avril 14th", "Aphex Twin"),
        ("18", "Dawn", "Tycho"),
        ("19", "An Ending (Ascent)", "Brian Eno"),
    ],
    "02_Lunch_Energy_12PM-130PM": [
        ("01", "Gallan Goodiyaan (Instrumental)", "Shankar-Ehsaan-Loy"),
        ("02", "Balam Pichkari (Instrumental)", "Vishal-Shekhar"),
        ("03", "Badtameez Dil (Instrumental)", "Pritam"),
        ("04", "London Thumakda (Instrumental)", "Sohail Sen"),
        ("05", "Kar Gayi Chull (Instrumental)", "Bollywood Instrumental"),
        ("06", "Nachdi Phira (Instrumental)", "Bollywood Instrumental"),
        ("07", "Nashe Si Chadh Gayi (Instrumental)", "Pritam"),
        ("08", "Zingaat (Instrumental)", "Ajay-Atul"),
        ("09", "Ghungroo (Instrumental)", "Vishal-Shekhar"),
        ("10", "Sher Khul Gaye (Instrumental)", "Pritam"),
        ("11", "September", "Earth, Wind & Fire"),
        ("12", "Walking on Sunshine", "Katrina & The Waves"),
        ("13", "Celebration", "Kool & The Gang"),
        ("14", "Lovely Day", "Bill Withers"),
        ("15", "Three Little Birds", "Bob Marley"),
    ],
    "03_Afternoon_SlumpBuster_130PM-330PM": [
        ("01", "Aavegi", "Ritviz"),
        ("02", "Chandamama", "Ritviz"),
        ("03", "Baaraat", "Ritviz & Nucleya"),
        ("04", "Khamoshi", "Ritviz"),
        ("05", "Sathi", "Ritviz"),
        ("06", "Raahi", "Ritviz"),
        ("07", "Bass Rani", "Nucleya"),
        ("08", "Laung Gawacha", "Nucleya"),
        ("09", "Tere Liye", "OAFF & Savera"),
        ("10", "Saathi", "Zaeden"),
        ("11", "Tu Hi Hai (Instrumental)", "Bollywood Instrumental"),
        ("12", "Awake", "Tycho"),
        ("13", "Opus", "Eric Prydz"),
        ("14", "Strobe", "Deadmau5"),
        ("15", "Sun Models", "ODESZA"),
        ("16", "Kong", "Bonobo"),
        ("17", "Porcelain", "Moby"),
        ("18", "Bloom", "RÜFÜS DU SOL"),
    ],
    "04_Peak_Productivity_330PM-530PM": [
        ("01", "Kho Gaye Hum Kahan", "Prateek Kuhad & Jasleen Royal"),
        ("02", "Khone De", "Prateek Kuhad"),
        ("03", "Dil Beparvah", "Prateek Kuhad"),
        ("04", "Husn", "Anuv Jain"),
        ("05", "Gul", "Anuv Jain"),
        ("06", "Riha", "Anuv Jain"),
        ("07", "Passing By", "When Chai Met Toast"),
        ("08", "Khoj", "When Chai Met Toast"),
        ("09", "Ocean Tide", "When Chai Met Toast"),
        ("10", "Aaoge Tum Kabhi", "The Local Train"),
        ("11", "Bandey", "The Local Train"),
        ("12", "Hello", "Parekh & Singh"),
        ("13", "Maria Tambien", "Khruangbin"),
        ("14", "White Gloves", "Khruangbin"),
        ("15", "Calf Born in Winter", "Khruangbin"),
        ("16", "Midnight in a Perfect World", "DJ Shadow"),
        ("17", "Resonance", "Home"),
        ("18", "Nightcall", "Kavinsky"),
    ],
    "05_AfroHouse_Sunset_530PM-700PM": [
        ("01", "Return to Oz (ARTBAT Remix)", "Monolink"),
        ("02", "Sirens", "Monolink"),
        ("03", "Father Ocean", "Monolink"),
        ("04", "Burning Sun", "Monolink"),
        ("05", "On My Knees (Adriatique Remix)", "RÜFÜS DU SOL"),
        ("06", "Miracle", "WhoMadeWho & Adriatique"),
        ("07", "Silence & Secrets (Adriatique Remix)", "WhoMadeWho"),
        ("08", "We Dance Again", "Black Coffee feat. Nakhane Toure"),
        ("09", "10 Missed Calls", "Black Coffee & Pharrell"),
        ("10", "Drive", "Black Coffee & David Guetta"),
        ("11", "Reflections", "Monolink"),
        ("12", "Beyond Us", "Adriatique & Eynka"),
        ("13", "Hypnotica", "Adriatique"),
        ("14", "The Prey (Mind Against Remix)", "Monolink"),
        ("15", "Desire", "Adriatique & Marino Canal"),
    ],
    "06_AfroHouse_Exit_700PM-800PM": [
        ("01", "Rearrange My Mind", "Monolink"),
        ("02", "Superman", "Black Coffee"),
        ("03", "Wish You Were Here", "Black Coffee & Msaki"),
        ("04", "Mesmerized", "Monolink"),
        ("05", "Miracle (RÜFÜS DU SOL Remix)", "WhoMadeWho & Adriatique"),
        ("06", "With You", "Adriatique & GORDO"),
        ("07", "SBCNCSLY", "Black Coffee & Sabrina Claudio"),
        ("08", "Under Darkening Skies", "Monolink"),
        ("09", "Swallow", "Monolink"),
        ("10", "Changing Colors", "Adriatique"),
        ("11", "The Prayer", "Themba"),
        ("12", "Gratitude", "Themba"),
    ],
}

# Backwards-compat alias for any older importers.
PLAYLIST_DATA = PLAYLIST_GROUPS["Playlist 3"]


def _build_query(song_name: str, artist: str) -> str:
    return f"{song_name} {artist}".strip()


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        added_playlists = 0
        added_songs = 0
        for root_name, playlists in PLAYLIST_GROUPS.items():
            for playlist_name, tracks in playlists.items():
                playlist = (
                    db.query(Playlist)
                    .filter(
                        Playlist.name == playlist_name,
                        Playlist.drive_root_name == root_name,
                    )
                    .one_or_none()
                )
                if playlist is None:
                    playlist = Playlist(name=playlist_name, drive_root_name=root_name)
                    db.add(playlist)
                    db.flush()
                    added_playlists += 1
                elif not playlist.drive_root_name:
                    playlist.drive_root_name = root_name

                existing_keys: set[tuple[str, str, str]] = {
                    (s.track_no, s.song_name, s.artist) for s in playlist.songs
                }
                for track_no, song_name, artist in tracks:
                    key = (track_no, song_name, artist)
                    if key in existing_keys:
                        continue
                    song = Song(
                        playlist_id=playlist.id,
                        track_no=track_no,
                        song_name=song_name,
                        artist=artist,
                        search_query=_build_query(song_name, artist),
                        status=SongStatus.PENDING,
                    )
                    db.add(song)
                    added_songs += 1

        db.commit()
        print(f"Seed complete. New playlists: {added_playlists}. New songs: {added_songs}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    sys.exit(0)
