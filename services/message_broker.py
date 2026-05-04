import json

import pika

from data import events


class MessageBroker:

    def __init__(self) -> None:
        self.queue_name = "library_events"

    def publish(self, event_type: str, message: str) -> dict:
        event = {
            "type": event_type,
            "message": message,
        }

        events.append(event)

        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host="localhost")
            )
            channel = connection.channel()

            channel.queue_declare(queue=self.queue_name, durable=True)

            channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                ),
            )

            connection.close()

            print(
                f"[RABBITMQ] Published event to {self.queue_name}: {event_type} - {message}",
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


