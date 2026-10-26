
import argparse
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import AIMemory

EXPIRY_DAYS = 90


def cleanup_expired_memories(dry_run=True, user_id=None):
    db = SessionLocal()

    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=EXPIRY_DAYS)

        query = db.query(AIMemory).filter(
            AIMemory.last_used_at < cutoff_date
        )

        # Optional scope prevents accidentally deleting other users' data.
        if user_id:
            query = query.filter(AIMemory.user_id == user_id)

        expired_memories = query.all()

        print(f"Expiry cutoff: {cutoff_date.isoformat()}")
        print(f"Expired memories found: {len(expired_memories)}")

        for memory in expired_memories:
            print(
                f"Memory ID: {memory.id} | "
                f"User: {memory.user_id} | "
                f"Last Used: {memory.last_used_at}"
            )

        if dry_run:
            print("DRY RUN: No memories were deleted.")
            return len(expired_memories)

        for memory in expired_memories:
            db.delete(memory)

        db.commit()
        print(f"{len(expired_memories)} expired memories deleted.")
        return len(expired_memories)

    except Exception as error:
        db.rollback()
        print("EXPIRY JOB ERROR:", repr(error))
        raise

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clean up expired AI memories.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete expired memories. Without this flag, runs a dry run.",
    )
    parser.add_argument(
        "--user-id",
        help="Restrict cleanup to one user ID.",
    )
    args = parser.parse_args()

    cleanup_expired_memories(
        dry_run=not args.execute,
        user_id=args.user_id,
    )
