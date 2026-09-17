from sqlalchemy.orm import Session
from app.models.entities import AuditLog, User

def log(db: Session, user: User | None, action: str, entity_type: str, entity_id: int | None = None, details: str | None = None):
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity_type=entity_type, entity_id=entity_id, details=details))
    db.commit()
