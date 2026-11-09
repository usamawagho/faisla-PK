from uuid import UUID

from sqlalchemy.orm import Session

from app.models.user import Notification
from app.repositories.notification_repository import NotificationRepository


class NotificationNotFoundError(Exception):
    pass


class NotificationService:
    def __init__(
        self,
        db: Session,
        repository: NotificationRepository | None = None,
    ) -> None:
        self.db = db
        self.repository = repository or NotificationRepository()

    def create(
        self,
        user_id: int,
        title: str,
        message: str,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
        )
        return self.repository.add(self.db, notification)

    def list_for_user(
        self,
        user_id: int,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        return self.repository.list_for_user(
            self.db,
            user_id,
            offset=offset,
            limit=limit,
        )

    def mark_read(self, notification_id: UUID, user_id: int) -> Notification:
        notification = self.repository.get_for_user(
            self.db,
            notification_id,
            user_id,
            lock=True,
        )
        if notification is None:
            raise NotificationNotFoundError("Notification not found")
        if not notification.is_read:
            notification.is_read = True
            self.db.commit()
            self.db.refresh(notification)
        return notification
