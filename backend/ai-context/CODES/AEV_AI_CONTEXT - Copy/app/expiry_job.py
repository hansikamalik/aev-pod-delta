from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import AIMemory


EXPIRY_DAYS = 90


def cleanup_expired_memories(dry_run=True):
    db = SessionLocal()

    try:
        cutoff_date = (
            datetime.now(timezone.utc)
            - timedelta(days=EXPIRY_DAYS)
        )

        expired_memories = (
            db.query(AIMemory)
            .filter(
                AIMemory.last_used_at < cutoff_date
            )
            .all()
        )

        print(f"Expiry cutoff: {cutoff_date}")
        print(
            f"Expired memories found: "
            f"{len(expired_memories)}"
        )

        for memory in expired_memories:
            print(
                f"Memory ID: {memory.id} | "
                f"User: {memory.user_id} | "
                f"Last Used: {memory.last_used_at}"
            )

        if dry_run:
            print(
                "DRY RUN: No memories were deleted."
            )
            return

        for memory in expired_memories:
            db.delete(memory)

        db.commit()

        print(
            f"{len(expired_memories)} expired "
            f"memories deleted successfully."
        )

    except Exception as error:
        db.rollback()
        print("EXPIRY JOB ERROR:", repr(error))

    finally:
        db.close()


if __name__ == "__main__":
    cleanup_expired_memories(dry_run=True)