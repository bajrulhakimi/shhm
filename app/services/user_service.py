from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserService:
    @staticmethod
    def get_or_create(
        db: Session,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        user = db.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            db.add(user)
        else:
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            user.last_name = last_name or user.last_name
        db.commit()
        db.refresh(user)
        return user

