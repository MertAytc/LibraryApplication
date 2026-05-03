from fastapi import FastAPI

from data import events, notifications
from models import ReserveSeatRequest, SubscribeBookRequest, SeatAvailabilitySubscribeRequest
from services.library_server import LibraryServer

app = FastAPI(
    title="Library Communication Patterns API",
    description="A simple backend that demonstrates request-response, queue, publish-subscribe, and event-driven communication without WebSocket.",
)

library_server = LibraryServer()


@app.get("/")
def root() -> dict:
    return {
        "message": "Library backend is running.",
        "websocket_used": False,
    }


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

@app.post("/system/check-expired-seats")
def check_expired_seats() -> dict:
    return library_server.check_expired_seat_reservations()

@app.get("/users/{user_id}/seat-reservation")
def get_user_seat_reservation(user_id: str) -> dict:
    return library_server.get_user_seat_reservation(user_id)


@app.post("/seats/subscribe-availability")
def subscribe_to_seat_availability(request: SeatAvailabilitySubscribeRequest) -> dict:
    return library_server.subscribe_to_seat_availability(request.user_id)


@app.get("/books")
def get_books() -> list[dict]:
    return library_server.get_books()

@app.post("/books/{book_id}/reserve")
def reserve_book(book_id: int, request: SubscribeBookRequest) -> dict:
    return library_server.reserve_book(book_id, request.user_id)

@app.post("/system/check-book-due-reminders")
def check_book_due_reminders() -> dict:
    return library_server.check_book_due_reminders()



@app.get("/books/search")
def search_books(query: str) -> list[dict]:
    return library_server.search_books(query)

@app.get("/users/{user_id}/waiting-books")
def get_user_waiting_books(user_id: str) -> list[dict]:
    return library_server.get_user_waiting_books(user_id)



@app.post("/books/{book_id}/subscribe")
def subscribe_to_book(book_id: int, request: SubscribeBookRequest) -> dict:
    return library_server.subscribe_to_book(book_id, request.user_id)


@app.post("/books/{book_id}/return")
def return_book(book_id: int) -> dict:
    return library_server.return_book(book_id)


@app.get("/notifications/{user_id}")
def get_notifications(user_id: str) -> list[dict]:
    return [
        notification
        for notification in notifications
        if notification["user_id"] == user_id
    ]


@app.get("/events")
def get_events() -> list[dict]:
    return events
