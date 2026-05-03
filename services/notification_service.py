from data import notifications


class NotificationService:
    def send(self, user_id: str, title: str, message: str) -> dict:
        notification = {
            "user_id": user_id,
            "title": title,
            "message": message,
        }

        notifications.append(notification)

        print(
            f"[NOTIFICATION_SERVICE] Notification sent to {user_id}: {title} - {message}",
            flush=True,
        )

        return notification

