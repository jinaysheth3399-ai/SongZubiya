"""Reset songs stuck in non-terminal mid-flight states back to a retryable state."""
from backend.database import SessionLocal
from backend.models import Song, SongStatus

db = SessionLocal()

stuck_statuses = {
    SongStatus.PROCESSING_AUDIO,
    SongStatus.UPLOADING,
    SongStatus.VERIFYING_FILE,
    SongStatus.SEARCHING,
    SongStatus.APPROVED,  # approved but never downloaded
}

songs = db.query(Song).all()
reset_to_approved = []
reset_to_pending = []
retry_reset = []

for s in songs:
    # Reset mid-flight states
    if s.status in stuck_statuses:
        if s.selected_youtube_url:
            s.status = SongStatus.APPROVED
            reset_to_approved.append(s.song_name)
        else:
            s.status = SongStatus.PENDING
            reset_to_pending.append(s.song_name)

    # Clear exhausted retry budgets so runner picks them up again
    if s.retry_count >= 3 and s.status not in {SongStatus.COMPLETED}:
        s.retry_count = 0
        retry_reset.append(s.song_name)

db.commit()
db.close()

print(f"Reset to APPROVED ({len(reset_to_approved)}): {reset_to_approved}")
print(f"Reset to PENDING  ({len(reset_to_pending)}):  {reset_to_pending}")
print(f"Retry count reset ({len(retry_reset)}):        {retry_reset}")
print("Done.")
