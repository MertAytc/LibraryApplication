from data import events


class MessageBroker:
    """Simulates publish-subscribe communication without WebSocket."""

    def publish(self, event_type: str, message: str) -> dict:
        event = {
            "type": event_type,
            "message": message,
        }

        events.append(event)

        print(
            f"[MESSAGE_BROKER] Published event: {event_type} - {message}",
            flush=True,
        )

        return event

