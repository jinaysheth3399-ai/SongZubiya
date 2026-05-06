import sqlite3
c = sqlite3.connect("playlist.db")
print("tables:", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")])
print("\nplaylists schema:")
for r in c.execute("PRAGMA table_info(playlists)"):
    print(" ", r)
print("\nplaylists indexes:")
for r in c.execute("PRAGMA index_list(playlists)"):
    print(" ", r)
print("\nplaylists rows:")
for r in c.execute("SELECT id, name, drive_root_name FROM playlists"):
    print(" ", r)
print("\nplaylists_new exists?", any(
    r[0] == "playlists_new"
    for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")
))
