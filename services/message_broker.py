import json
import pika
from data import events


class MessageBroker:

    def __init__(self) -> None:
        self.queue_name = "library_events"
        self._connection = None
        self._channel = None

    def _get_channel(self):
        try:
            if self._connection is None or self._connection.is_closed:
                self._connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host="localhost")
                )
                self._channel = self._connection.channel()
                self._channel.queue_declare(queue=self.queue_name, durable=True)
        except Exception as error:
            print(f"[MESSAGE_BROKER] Connection error: {error}", flush=True)
            self._connection = None
            self._channel = None
        return self._channel

    def publish(self, event_type: str, message: str) -> dict:
        event = {
            "type": event_type,
            "message": message,
        }

        events.append(event)

        try:
            channel = self._get_channel()

            if channel is None:
                raise Exception("Channel could not be established.")

            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                ),
            )

            print(
                f"[RABBITMQ] Published: {event_type} - {message}",
                flush=True,
            )

        except Exception as error:
            print(
                f"[MESSAGE_BROKER] RabbitMQ publish failed: {error}",
                flush=True,
            )
            print(
                f"[MESSAGE_BROKER] Stored event locally: {event_type} - {message}",
                flush=True,
            )

        return event

    def close(self):
        try:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
                print("[MESSAGE_BROKER] Connection closed.", flush=True)
        except Exception as error:
            print(f"[MESSAGE_BROKER] Error closing connection: {error}", flush=True)