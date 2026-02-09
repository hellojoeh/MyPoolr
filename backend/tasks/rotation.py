"""Rotation management tasks."""

from celery_app import celery_app
from database import db_manager


@celery_app.task(bind=True, max_retries=3)
def advance_rotation_schedule(self, mypoolr_id: str):
    """Move to next rotation after completion."""
    try:
        # Get current MyPoolr
        result = db_manager.client.table("mypoolr").select("*").eq(
            "id", mypoolr_id
        ).execute()
        
        if not result.data:
            raise Exception(f"MyPoolr {mypoolr_id} not found")
        
        mypoolr = result.data[0]
        
        # Advance rotation position
        new_position = mypoolr["current_rotation_position"] + 1
        total_completed = mypoolr["total_rotations_completed"] + 1
        
        # Update MyPoolr
        update_data = {
            "current_rotation_position": new_position,
            "total_rotations_completed": total_completed
        }
        
        db_manager.client.table("mypoolr").update(update_data).eq(
            "id", mypoolr_id
        ).execute()
        
        return f"Advanced rotation for MyPoolr {mypoolr_id} to position {new_position}"
        
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)