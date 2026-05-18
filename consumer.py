import json
import re
import sys
import os
import requests
import random
import pika
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

QUEUE_NAME = "library_events"
BASE_URL = "http://localhost:8000"

#stores runtime statistics for consumed events and triggered actions.
stats = {
    "total_events": 0,
    "books_reserved": 0,
    "books_returned": 0,
    "seats_reserved": 0,
    "seats_released": 0,
    "seats_expired": 0,
    "notifications_sent": 0,
    "users_registered": 0,
    "high_occupancy_alerts": 0,
}

#extracts ket:value fields from event message strings.
def parse(message: str, key: str) -> str | None:
    match = re.search(rf"{key}:(\S+)", message)
    return match.group(1) if match else None

#sends a notification by calling the backend notification endpoint.
def send_notification(user_id: str, title: str, message: str):
    try:
        requests.post(
            f"{BASE_URL}/notifications/send",
            json={"user_id": user_id, "title": title, "message": message},
        )
        stats["notifications_sent"] += 1
        print(f"[CONSUMER] Notification sent to {user_id}: {title}", flush=True)
    except Exception as e:
        print(f"[CONSUMER] Failed to send notification: {e}", flush=True)

#handles BOOK_RESERVED events by sending a same-category book recommendation.
def handle_book_reserved(message: str):
    try:
        match = re.search(r"(.+) was reserved by (\S+) in category (.+)\. Due", message)
        if not match:
            print(f"[CONSUMER] Could not parse BOOK_RESERVED message.", flush=True)
            return

        title = match.group(1)
        user_id = match.group(2)
        category = match.group(3)

        books_response = requests.get(f"{BASE_URL}/books")
        all_books = books_response.json()

        recommendations = [
            b for b in all_books
            if b.get("category") == category
            and b.get("title") != title
            and b.get("is_available")
        ]

        if recommendations:
            rec = random.choice(recommendations)
            send_notification(
                user_id=user_id,
                title="Book Recommendation",
                message=f"You may also like '{rec['title']}' from {rec['category']}.",
            )
            print(f"[CONSUMER] Recommendation: {rec['title']} → {user_id}", flush=True)
        else:
            print(f"[CONSUMER] No recommendations in category: {category}", flush=True)

    except Exception as e:
        print(f"[CONSUMER] Error in handle_book_reserved: {e}", flush=True)

#handles BOOK_RETURNED events by triggering notification for the next waiting user.
def handle_book_returned(message: str):
    book_id = parse(message, "book_id")
    if book_id:
        try:
            requests.post(f"{BASE_URL}/books/{book_id}/notify-next")
            print(f"[CONSUMER] Notified next user in queue for book {book_id}.", flush=True)
        except Exception as e:
            print(f"[CONSUMER] Failed to notify next user: {e}", flush=True)

#handles SEAT_RELEASED events by notifying users waiting for available seats.
def handle_seat_released(message: str):
    match = re.search(r"Seat (\S+) was", message)
    if match:
        seat_id = match.group(1)
        try:
            requests.post(f"{BASE_URL}/seats/{seat_id}/notify-waiting")
            print(f"[CONSUMER] Notified waiting users for seat {seat_id}.", flush=True)
        except Exception as e:
            print(f"[CONSUMER] Failed to notify waiting users: {e}", flush=True)

#handles high occupancy event by broadcasting alerts to users except the triggering user.
def handle_seat_occupancy_high(message: str):
    excluded_user = parse(message, "excluded_user")
    match = re.search(r"Current occupancy: (\d+)%", message)
    occupancy = match.group(1) if match else "80+"

    try:
        users_response = requests.get(f"{BASE_URL}/admin/users")
        users = users_response.json()

        for user in users:
            if user["id"] == excluded_user:
                continue
            send_notification(
                user_id=user["id"],
                title="Library is crowded",
                message=f"Seat occupancy is above 80%. Current occupancy: {occupancy}%.",
            )

        stats["high_occupancy_alerts"] += 1
        print(f"[CONSUMER] HIGH OCCUPANCY broadcast sent.", flush=True)
    except Exception as e:
        print(f"[CONSUMER] Failed to broadcast occupancy alert: {e}", flush=True)

#handles expired seat reservations by notifying the expired user and seat waitlist.
def handle_seat_reservation_expired(message: str):
    expired_user = parse(message, "expired_user")
    match = re.search(r"Seat (\S+) reservation", message)
    seat_id = match.group(1) if match else None

    if expired_user and expired_user != "None":
        send_notification(
            user_id=expired_user,
            title="Seat Reservation Expired",
            message=f"Your reservation for seat {seat_id} expired because you did not scan the QR code.",
        )

    if seat_id:
        try:
            requests.post(f"{BASE_URL}/seats/{seat_id}/notify-waiting")
            print(f"[CONSUMER] Notified waiting users after seat expiry.", flush=True)
        except Exception as e:
            print(f"[CONSUMER] Failed to notify waiting users: {e}", flush=True)

    stats["seats_expired"] += 1

#handles new book events by notifying users with matching preferences.
def handle_book_added(message: str):
    match = re.search(r"Admin added new book: (.+) by (.+) in category (.+)\.", message)
    if not match:
        return

    title = match.group(1)
    author = match.group(2)
    category = match.group(3)

    try:
        users_response = requests.get(f"{BASE_URL}/admin/users")
        users = users_response.json()
        notified = 0

        for user in users:
            fav_categories = user.get("favorite_categories", [])
            fav_authors = user.get("favorite_authors", [])

            if category in fav_categories or author in fav_authors:
                send_notification(
                    user_id=user["id"],
                    title="New Book Added",
                    message=f"'{title}' by {author} was added in your favorite category or author list.",
                )
                notified += 1

        print(f"[CONSUMER] New book notifications sent to {notified} user(s).", flush=True)
    except Exception as e:
        print(f"[CONSUMER] Failed to handle BOOK_ADDED: {e}", flush=True)

#handles user registration events by sending a welcome notification.
def handle_user_registered(message: str):
    match = re.search(r"(.+) registered with user id (\S+)\.", message)
    if match:
        name = match.group(1)
        user_id = match.group(2).rstrip(".")
        send_notification(
            user_id=user_id,
            title="Welcome to the Library!",
            message=f"Hello {name}, welcome! You can browse books and reserve seats.",
        )

#routes each consumed event to the correct handler function.
def handle_event(event_type: str, message: str):
    now = datetime.now(timezone.utc).strftime("%H:%M:%S")
    stats["total_events"] += 1

    print(f"\n[CONSUMER] [{now}] Event: {event_type}", flush=True)
    print(f"           Message: {message}", flush=True)

    if event_type == "USER_REGISTERED":
        stats["users_registered"] += 1
        handle_user_registered(message)

    elif event_type == "BOOK_RESERVED":
        stats["books_reserved"] += 1
        handle_book_reserved(message)

    elif event_type == "BOOK_RETURNED":
        stats["books_returned"] += 1
        handle_book_returned(message)

    elif event_type == "SEAT_RESERVED":
        stats["seats_reserved"] += 1
        print(f"[CONSUMER] Seat reserved. Total: {stats['seats_reserved']}", flush=True)

    elif event_type == "SEAT_RELEASED":
        stats["seats_released"] += 1
        handle_seat_released(message)

    elif event_type == "SEAT_OCCUPANCY_HIGH":
        handle_seat_occupancy_high(message)

    elif event_type == "SEAT_RESERVATION_EXPIRED":
        handle_seat_reservation_expired(message)

    elif event_type == "BOOK_ADDED":
        handle_book_added(message)

    elif event_type == "BOOK_SUBSCRIBED":
        print(f"[CONSUMER] User joined waiting queue.", flush=True)

    elif event_type == "BOOK_QUEUE_NOTIFICATION_SENT":
        stats["notifications_sent"] += 1
        print(f"[CONSUMER] Next user in queue notified.", flush=True)

    elif event_type == "BOOK_PICKUP_EXPIRED":
        print(f"[CONSUMER] Book pickup expired. Moving to next in queue.", flush=True)

    elif event_type == "BOOK_DUE_REMINDER_SENT":
        print(f"[CONSUMER] Due reminder sent.", flush=True)

    elif event_type == "SEAT_CHECKED_IN":
        print(f"[CONSUMER] User checked in via QR.", flush=True)

    else:
        print(f"[CONSUMER] Event logged: {event_type}", flush=True)

    print(f"[CONSUMER] Stats: {stats}", flush=True)

#processes incoming RABBITMQ messages and acks them after handling.
def on_message(channel, method, properties, body):
    try:
        event = json.loads(body)
        event_type = event.get("type", "UNKNOWN")
        message = event.get("message", "")
        handle_event(event_type, message)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        print(f"[CONSUMER] Error processing message: {e}", flush=True)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

#connects to RABBITMQ ans statrs listening for library event messages.
def start_consumer():
    print("[CONSUMER] Connecting to RabbitMQ...", flush=True)

    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
        )
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)

        print(f"[CONSUMER] Listening on queue: {QUEUE_NAME}", flush=True)
        print("[CONSUMER] Waiting for events. Press CTRL+C to stop.\n", flush=True)

        channel.start_consuming()

    except KeyboardInterrupt:
        print("\n[CONSUMER] Stopped by user.", flush=True)
        connection.close()

    except Exception as e:
        print(f"[CONSUMER] Failed to connect to RabbitMQ: {e}", flush=True)


if __name__ == "__main__":
    start_consumer()