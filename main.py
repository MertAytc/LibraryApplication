from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from pydantic import BaseModel


from data import events, notifications, preference_options, seat_waiting_users, seats
from models import (
    ReserveSeatRequest,
    SubscribeBookRequest,
    SeatAvailabilitySubscribeRequest,
    RegisterUserRequest,
    UserPreferencesRequest,
    AddBookRequest,
    LoginUserRequest,
)
from services.library_server import LibraryServer

app = FastAPI(
    title="Library Communication Patterns API",
    description="A simple backend that demonstrates request-response, queue, publish-subscribe, and event-driven communication without WebSocket.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

library_server = LibraryServer()


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    return {"message": "Library backend is running."}


# ── Users ─────────────────────────────────────────────────────────────────────

@app.post("/users/register")
def register_user(request: RegisterUserRequest) -> dict:
    return library_server.register_user(
        user_id=request.user_id,
        name=request.name,
    )

@app.post("/users/login")
def login_user(request: LoginUserRequest) -> dict:
    return library_server.login_user(request.user_id)

@app.get("/admin/users")
def get_users() -> list[dict]:
    return library_server.get_users()

@app.post("/users/{user_id}/preferences")
def update_user_preferences(user_id: str, request: UserPreferencesRequest) -> dict:
    return library_server.update_user_preferences(
        user_id=user_id,
        favorite_categories=request.favorite_categories,
        favorite_authors=request.favorite_authors,
    )

@app.get("/users/{user_id}/preferences")
def get_user_preferences(user_id: str) -> dict:
    return library_server.get_user_preferences(user_id)

@app.get("/preferences/options")
def get_preference_options() -> dict:
    return library_server.get_preference_options()


# ── Seats ─────────────────────────────────────────────────────────────────────

@app.get("/seats")
def get_seats() -> list[dict]:
    return library_server.get_seats()

@app.get("/seats/occupancy")
def get_seat_occupancy() -> dict:
    return library_server.get_seat_occupancy()

@app.post("/seats/{seat_id}/reserve")
def reserve_seat(seat_id: str, request: ReserveSeatRequest) -> dict:
    return library_server.reserve_seat(seat_id, request.user_id)

@app.post("/seats/{seat_id}/check-in")
def check_in_seat(seat_id: str) -> dict:
    return library_server.check_in_seat(seat_id)

@app.post("/seats/{seat_id}/release")
def release_seat(seat_id: str) -> dict:
    return library_server.release_seat(seat_id)

@app.post("/seats/{seat_id}/notify-waiting")
def notify_seat_waiting_users(seat_id: str) -> dict:
    """Consumer tarafından çağrılır — koltuğu bekleyen kullanıcılara bildirim gönderir."""
    notifications_sent = library_server.notify_seat_waiting_users(seat_id)
    return {
        "success": True,
        "message": f"Notified {len(notifications_sent)} waiting user(s).",
        "notifications": notifications_sent,
    }

@app.get("/users/{user_id}/seat-reservation")
def get_user_seat_reservation(user_id: str) -> dict:
    return library_server.get_user_seat_reservation(user_id)

@app.post("/seats/subscribe-availability")
def subscribe_to_seat_availability(request: SeatAvailabilitySubscribeRequest) -> dict:
    return library_server.subscribe_to_seat_availability(request.user_id)

@app.post("/system/check-expired-seats")
def check_expired_seats() -> dict:
    return library_server.check_expired_seat_reservations()


# ── Books ─────────────────────────────────────────────────────────────────────

@app.get("/books")
def get_books() -> list[dict]:
    return library_server.get_books()

@app.get("/books/search")
def search_books(query: str) -> list[dict]:
    return library_server.search_books(query)

@app.post("/books/{book_id}/reserve")
def reserve_book(book_id: int, request: SubscribeBookRequest) -> dict:
    return library_server.reserve_book(book_id, request.user_id)

@app.post("/books/{book_id}/subscribe")
def subscribe_to_book(book_id: int, request: SubscribeBookRequest) -> dict:
    return library_server.subscribe_to_book(book_id, request.user_id)

@app.post("/books/{book_id}/notify-next")
def notify_next_book_waiting_user(book_id: int) -> dict:
    """Consumer tarafından çağrılır — kitabı bekleyen sıradaki kullanıcıya bildirim gönderir."""
    book = library_server._find_book(book_id)
    if book is None:
        return {"success": False, "message": "Book not found."}
    notification = library_server.notify_next_book_waiting_user(book)
    return {
        "success": True,
        "message": "Next user in queue notified.",
        "notification": notification,
    }

@app.get("/users/{user_id}/waiting-books")
def get_user_waiting_books(user_id: str) -> list[dict]:
    return library_server.get_user_waiting_books(user_id)

@app.get("/users/{user_id}/borrowed-books")
def get_user_borrowed_books(user_id: str) -> list[dict]:
    return library_server.get_user_borrowed_books(user_id)

@app.post("/admin/books/{book_id}/return")
def admin_return_book(book_id: int) -> dict:
    return library_server.return_book(book_id)

@app.post("/admin/books")
def add_book(request: AddBookRequest) -> dict:
    return library_server.add_book(
        title=request.title,
        author=request.author,
        category=request.category,
    )

@app.post("/books/{book_id}/send-due-reminder")
def send_book_due_reminder(book_id: int) -> dict:
    return library_server.send_book_due_reminder(book_id)

@app.post("/system/check-book-due-reminders")
def check_book_due_reminders() -> dict:
    return library_server.check_book_due_reminders()

@app.post("/system/check-expired-book-pickups")
def check_expired_book_pickups() -> dict:
    return library_server.check_expired_book_pickups()


# ── Consumer endpoint'leri ────────────────────────────────────────────────────

class SendNotificationRequest(BaseModel):
    user_id: str
    title: str
    message: str

@app.post("/notifications/send")
def send_notification(request: SendNotificationRequest) -> dict:
    """Consumer tarafından çağrılır — kullanıcıya bildirim gönderir."""
    notification = library_server.notification_service.send(
        user_id=request.user_id,
        title=request.title,
        message=request.message,
    )
    return {"success": True, "notification": notification}

@app.post("/notifications/broadcast")
def broadcast_notification(request: SendNotificationRequest) -> dict:
    """Consumer tarafından çağrılır — tüm kullanıcılara bildirim gönderir."""
    sent = []
    for user in library_server.get_users():
        notification = library_server.notification_service.send(
            user_id=user["id"],
            title=request.title,
            message=request.message,
        )
        sent.append(notification)
    return {"success": True, "sent_count": len(sent), "notifications": sent}


# ── Notifications & Events ────────────────────────────────────────────────────

@app.get("/notifications/{user_id}")
def get_notifications(user_id: str, since: str | None = None) -> list[dict]:
    user_notifications = [
        n for n in notifications
        if n["user_id"] == user_id
    ]

    if since:
        since_time = datetime.fromisoformat(since)
        user_notifications = [
            n for n in user_notifications
            if datetime.fromisoformat(n["timestamp"]) > since_time
        ]

    return user_notifications

@app.get("/events")
def get_events() -> list[dict]:
    return events