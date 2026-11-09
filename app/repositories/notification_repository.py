from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Notification


class NotificationRepository:
    def add(self, db: Session, notification: Notification) -> Notification:
        db.add(notification)
        db.flush()
        return notification

    def list_for_user(
        self,
        db: Session,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        return list(
            db.scalars(
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.created_at.desc(), Notification.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def get_for_user(
        self,
        db: Session,
        notification_id: UUID,
        user_id: int,
        *,
        lock: bool = False,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        return db.scalar(statement)
