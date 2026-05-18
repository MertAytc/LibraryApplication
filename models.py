from pydantic import BaseModel


class RegisterUserRequest(BaseModel):
    user_id: str
    name: str

class LoginUserRequest(BaseModel):
    user_id: str

class UserPreferencesRequest(BaseModel):
    favorite_categories: list[str] = []
    favorite_authors: list[str] = []


class ReserveSeatRequest(BaseModel):
    user_id: str


class SubscribeBookRequest(BaseModel):
    user_id: str


class SeatAvailabilitySubscribeRequest(BaseModel):
    user_id: str


class AddBookRequest(BaseModel):
    title: str
    author: str
    category: str


class SendNotificationRequest(BaseModel):
    user_id: str
    title: str
    message: str


class Seat(BaseModel):
    id: str
    is_available: bool
    reserved_by: str | None = None
    reserved_until: str | None = None
    qr_checked: bool = False


class Book(BaseModel):
    id: int
    title: str
    author: str
    category: str
    is_available: bool
    borrowed_by: str | None = None
    due_date: str | None = None
    reserved_until: str | None = None
    waiting_queue: list[str] = []
    notified_user: str | None = None


class Notification(BaseModel):
    id: str
    user_id: str
    title: str
    message: str
    timestamp: str
    read: bool = False


class Event(BaseModel):
    type: str
    message: str = ""
