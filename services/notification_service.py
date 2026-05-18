import uuid
from datetime import datetime, timezone
from data import notifications


class NotificationService:
    def send(self, user_id: str, title: str, message: str) -> dict:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
        }

        notifications.append(notification)

        print(
            f"[NOTIFICATION_SERVICE] Notification sent to {user_id}: {title} - {message}",
            flush=True,
        )

        return notification