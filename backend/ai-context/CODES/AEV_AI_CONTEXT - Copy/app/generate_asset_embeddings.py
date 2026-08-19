print("SCRIPT STARTED")

from sqlalchemy import text

from app.database import SessionLocal
from app.models import Asset
from app.embedding import generate_embedding


def build_asset_text(asset: Asset) -> str:
    parts = [
        asset.asset_name,
        asset.asset_type,
        asset.operating_system,
        asset.ip_address,
        asset.description,
        (
            f"Risk score: {asset.risk_score}"
            if asset.risk_score is not None
            else None
        ),
    ]

    return " | ".join(
        str(part)
        for part in parts
        if part
    )


def generate_embeddings_for_assets():
    db = SessionLocal()

    try:
        assets = db.query(Asset).order_by(Asset.id).all()

        if not assets:
            print("No assets found.")
            return

        for asset in assets:
            asset_text = build_asset_text(asset)
            embedding_vector = generate_embedding(asset_text)

            db.execute(
                text("""
                    UPDATE assets
                    SET embedding = CAST(:embedding AS vector)
                    WHERE id = :asset_id
                """),
                {
                    "embedding": str(embedding_vector),
                    "asset_id": asset.id,
                },
            )

            print(
                f"Generated and updated embedding for: "
                f"{asset.asset_name}"
            )

        db.commit()
        print("All asset embeddings committed successfully.")

        verification = db.execute(
            text("""
                SELECT
                    id,
                    asset_name,
                    embedding IS NOT NULL AS has_embedding
                FROM assets
                ORDER BY id
            """)
        ).mappings().all()

        print("\nVerification from the same database connection:")

        for row in verification:
            print(
                row["id"],
                row["asset_name"],
                row["has_embedding"],
            )

    except Exception as error:
        db.rollback()
        print("ERROR:", repr(error))
        raise

    finally:
        db.close()


if __name__ == "__main__":
    generate_embeddings_for_assets()