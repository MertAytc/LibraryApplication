from data import books, events, seats, seat_waiting_users, users, preference_options, seat_occupancy_state
from services.message_broker import MessageBroker
from services.notification_service import NotificationService
from datetime import datetime, timedelta, timezone
from threading import Timer

#contains the main business logic for users,seats,books and event publishing.
class LibraryServer:
    def __init__(self) -> None:
        self.message_broker = MessageBroker()
        self.notification_service = NotificationService()
    #--------USER FUNCTIONS----------
    #registers a new user and publishes a USER_REGISTERED event.
    def register_user(self, user_id: str, name: str) -> dict:
        existing_user = self._find_user(user_id)

        if existing_user is not None:
            return {
                "success": False,
                "message": "User already exists.",
                "user": existing_user,
            }

        user = {
            "id": user_id,
            "name": name,
            "favorite_categories": [],
            "favorite_authors": [],
        }

        users.append(user)

        event = self.message_broker.publish(
            "USER_REGISTERED",
            f"{name} registered with user id {user_id}.",
        )

        return {
            "success": True,
            "message": "User registered successfully.",
            "user": user,
            "event": event,
        }
    #cheks whether a user exists and returns Login result.
    def login_user(self, user_id: str) -> dict:
        user = self._find_user(user_id)

        if user is None:
            return {"success": False, "message": "User not found."}

        return {"success": True, "message": "Login successful.", "user": user}

    #returns all registered users for admin operations.
    def get_users(self) -> list[dict]:
        return users

    #update a user's favorite categories and authors.
    def update_user_preferences(
        self,
        user_id: str,
        favorite_categories: list[str],
        favorite_authors: list[str],
    ) -> dict:
        user = self._find_user(user_id)

        if user is None:
            return {"success": False, "message": "User not found."}

        user["favorite_categories"] = favorite_categories
        user["favorite_authors"] = favorite_authors

        event = self.message_broker.publish(
            "USER_PREFERENCES_UPDATED",
            f"{user_id} updated favorite categories and authors.",
        )

        return {
            "success": True,
            "message": "Preferences updated successfully.",
            "user": user,
            "event": event,
        }
    
    #returns the selected category and author preferences of a user.
    def get_user_preferences(self, user_id: str) -> dict:
        user = self._find_user(user_id)

        if user is None:
            return {"success": False, "message": "User not found."}

        return {
            "success": True,
            "user_id": user["id"],
            "name": user["name"],
            "favorite_categories": user.get("favorite_categories", []),
            "favorite_authors": user.get("favorite_authors", []),
        }
    #returns available cateogory and author options for preference selection.
    def get_preference_options(self) -> dict:
        return preference_options

    
    #--------SEAT FUNCTIONS----------
    #returns all seats with their current availability and reservation status.
    def get_seats(self) -> list[dict]:
        return seats

    #returns the active seat reservation of a specific user.
    def get_user_seat_reservation(self, user_id: str) -> dict:
        reservation = next(
            (seat for seat in seats if seat["reserved_by"] == user_id),
            None,
        )

        if reservation is None:
            return {
                "success": False,
                "message": "User does not have an active seat reservation.",
                "seat": None,
            }

        return {
            "success": True,
            "message": "Active seat reservation found.",
            "seat": reservation,
        }
    #reserves an available seat for a user and starts the QR check-in timer.
    def reserve_seat(self, seat_id: str, user_id: str) -> dict:
        seat = self._find_seat(seat_id)

        if seat is None:
            return {"success": False, "message": "Seat not found."}

        existing_reservation = next(
            (s for s in seats if s.get("reserved_by") == user_id),
            None,
        )

        if existing_reservation is not None:
            return {
                "success": False,
                "message": "User already has an active seat reservation.",
                "seat": existing_reservation,
            }

        if not seat["is_available"]:
            return {"success": False, "message": "Seat is already reserved."}

        reserved_until = datetime.now(timezone.utc) + timedelta(seconds=55)

        seat["is_available"] = False
        seat["reserved_by"] = user_id
        seat["reserved_until"] = reserved_until.isoformat()
        seat["qr_checked"] = False

        event = self.message_broker.publish(
            "SEAT_RESERVED",
            f"Seat {seat_id} was reserved by {user_id} until {seat['reserved_until']}.",
        )

        occupancy_event = self.check_seat_occupancy(excluded_user_id=user_id)
        Timer(55, self.check_expired_seat_reservations).start()

        return {
            "success": True,
            "message": "Seat reserved successfully.",
            "seat": seat,
            "event": event,
            "occupancy_event": occupancy_event,
        }
    #marks a reserved seat as occupied after QR check-in.
    def check_in_seat(self, seat_id: str) -> dict:
        seat = self._find_seat(seat_id)

        if seat is None:
            return {"success": False, "message": "Seat not found."}

        if seat["is_available"]:
            return {"success": False, "message": "Seat is not reserved."}

        if seat.get("qr_checked", False):
            return {"success": False, "message": "Seat is already checked in."}

        seat["qr_checked"] = True
        seat["reserved_until"] = None

        event = self.message_broker.publish(
            "SEAT_CHECKED_IN",
            f"{seat['reserved_by']} checked in to seat {seat_id} by scanning QR code.",
        )

        return {
            "success": True,
            "message": "Seat check-in successful. Seat is now occupied.",
            "seat": seat,
            "event": event,
        }
    #manually releases a reserved or occupied seat.
    def release_seat(self, seat_id: str) -> dict:
        seat = self._find_seat(seat_id)

        if seat is None:
            return {"success": False, "message": "Seat not found."}

        if seat["is_available"]:
            return {"success": False, "message": "Seat is already available."}

        seat["is_available"] = True
        seat["reserved_by"] = None
        seat["reserved_until"] = None
        seat["qr_checked"] = False

        event = self.message_broker.publish(
            "SEAT_RELEASED",
            f"Seat {seat_id} was manually released and became available.",
        )
        return {
            "success": True,
            "message": "Seat released successfully.",
            "seat": seat,
            "event": event,
        }

    #checks seat occupancy and publishes a high occupancy event when it exceeds 80%.
    def check_seat_occupancy(self, excluded_user_id: str | None = None) -> dict | None:
        total_seats = len(seats)
        reserved_or_occupied_seats = len([s for s in seats if not s["is_available"]])
        occupancy_rate = reserved_or_occupied_seats / total_seats

        if occupancy_rate <= 0.8:
            seat_occupancy_state["high_occupancy_notified"] = False
            return None

        if seat_occupancy_state["high_occupancy_notified"]:
            return {
                "message": "High occupancy notification was already sent.",
                "occupancy_rate": occupancy_rate,
            }

        event = self.message_broker.publish(
            "SEAT_OCCUPANCY_HIGH",
            f"Library seat occupancy is above 80%. Current occupancy: {occupancy_rate * 100:.0f}%. excluded_user:{excluded_user_id}",
        )


        seat_occupancy_state["high_occupancy_notified"] = True

        return {
            "event": event,
            "occupancy_rate": occupancy_rate,
        }

    #subscribes a user to seat availability notifications when no seats are available.
    def subscribe_to_seat_availability(self, user_id: str) -> dict:
        available_seats = [s for s in seats if s["is_available"]]

        if available_seats:
            return {
                "success": False,
                "message": "There are already available seats.",
                "available_seats": available_seats,
            }

        if user_id in seat_waiting_users:
            return {
                "success": False,
                "message": "User is already subscribed to seat availability notifications.",
            }

        seat_waiting_users.append(user_id)

        event = self.message_broker.publish(
            "SEAT_AVAILABILITY_SUBSCRIBED",
            f"{user_id} subscribed to seat availability notifications.",
        )

        return {
            "success": True,
            "message": "User will be notified when a seat becomes available.",
            "waiting_users": seat_waiting_users,
            "event": event,
        }
    #sends seat availability notifications to users waiting for an empty seat.
    def notify_seat_waiting_users(self, seat_id: str) -> list[dict]:
        """Consumer tarafından POST /seats/{seat_id}/notify-waiting üzerinden çağrılır."""
        sent_notifications = []

        if not seat_waiting_users:
            return sent_notifications

        for user_id in seat_waiting_users:
            notification = self.notification_service.send(
                user_id=user_id,
                title="Seat Available",
                message=f"Seat {seat_id} is now available.",
            )
            sent_notifications.append(notification)

        self.message_broker.publish(
            "SEAT_AVAILABLE_NOTIFICATION_SENT",
            f"Seat availability notification sent to {len(seat_waiting_users)} user(s).",
        )

        seat_waiting_users.clear()

        return sent_notifications

    #releases seat reservations that expşred before QR check-in.
    def check_expired_seat_reservations(self) -> dict:
        now = datetime.now(timezone.utc)
        expired_seats = []

        for seat in seats:
            reserved_until = seat.get("reserved_until")

            if seat["is_available"] or seat.get("qr_checked", False) or reserved_until is None:
                continue

            reserved_until_time = datetime.fromisoformat(reserved_until)

            if reserved_until_time <= now:
                expired_user = seat.get("reserved_by")
                expired_seats.append(seat["id"])

                seat["is_available"] = True
                seat["reserved_by"] = None
                seat["reserved_until"] = None
                seat["qr_checked"] = False

                self.message_broker.publish(
                    "SEAT_RESERVATION_EXPIRED",
                    f"Seat {seat['id']} reservation expired. expired_user:{expired_user}",
                )
        return {
            "success": True,
            "expired_seats": expired_seats,
            "message": f"{len(expired_seats)} expired seat reservation(s) cleared.",
        }

    ##calculates and returns the current seat occupancy rate.
    def get_seat_occupancy(self) -> dict:
        total_seats = len(seats)
        occupied_or_reserved = len([s for s in seats if not s["is_available"]])
        occupancy_rate = occupied_or_reserved / total_seats

        return {
            "total_seats": total_seats,
            "occupied_or_reserved": occupied_or_reserved,
            "available_seats": total_seats - occupied_or_reserved,
            "occupancy_rate": occupancy_rate,
            "occupancy_percent": round(occupancy_rate * 100, 2),
        }

    # -------BOOK FUNCTIONS--------

    #returns all books with availability, borrower and queue information.
    def get_books(self) -> list[dict]:
        return books

    #reserves an available book for a user and starts the due reminder time.
    def reserve_book(self, book_id: int, user_id: str) -> dict:
        book = self._find_book(book_id)

        if book is None:
            return {"success": False, "message": "Book not found."}

        if not book["is_available"]:
            return {
                "success": False,
                "message": "Book is currently borrowed. You can subscribe to the waiting queue.",
                "book": book,
            }

        notified_user = book.get("notified_user")

        if notified_user is not None and notified_user != user_id:
            return {
                "success": False,
                "message": "This book is temporarily reserved for another user in the queue.",
                "notified_user": notified_user,
                "queue_count": len(book.get("waiting_queue", [])),
                "queue_position": (
                    book["waiting_queue"].index(user_id) + 1
                    if user_id in book.get("waiting_queue", [])
                    else None
                ),
            }

        due_date = datetime.now(timezone.utc) + timedelta(seconds=60)

        book["is_available"] = False
        book["borrowed_by"] = user_id
        book["due_date"] = due_date.isoformat()
        book["reserved_until"] = None
        book["notified_user"] = None
        book["due_reminder_sent"] = False

        event = self.message_broker.publish(
            "BOOK_RESERVED",
            f"{book['title']} was reserved by {user_id} in category {book.get('category')}. Due date: {book['due_date']}.",
        )
        Timer(40, self.send_book_due_reminder, args=[book_id]).start()

        return {
            "success": True,
            "message": "Book reserved successfully.",
            "book": book,
            "event": event,
        }
    #sends a due date reminder notification to the current borrower.
    def send_book_due_reminder(self, book_id: int) -> dict:
        book = self._find_book(book_id)

        if book is None:
            return {"success": False, "message": "Book not found."}

        if book["is_available"]:
            return {"success": False, "message": "Book is already returned."}

        if book.get("due_reminder_sent", False):
            return {"success": False, "message": "Due reminder already sent."}

        borrowed_by = book.get("borrowed_by")
        due_date = book.get("due_date")

        if borrowed_by is None or due_date is None:
            return {"success": False, "message": "Book does not have an active borrower."}

        due_date_time = datetime.fromisoformat(due_date)
        now = datetime.now(timezone.utc)
        remaining_seconds = int((due_date_time - now).total_seconds())

        notification = self.notification_service.send(
            user_id=borrowed_by,
            title="Book Due Reminder",
            message=f"{book['title']} must be returned in about {remaining_seconds} seconds.",
        )

        event = self.message_broker.publish(
            "BOOK_DUE_REMINDER_SENT",
            f"Due reminder sent to {borrowed_by} for {book['title']}.",
        )

        book["due_reminder_sent"] = True

        return {
            "success": True,
            "message": "Due reminder sent.",
            "book": book,
            "notification": notification,
            "event": event,
        }

    #checks borrowed books and sends reminders for books near their due date.
    def check_book_due_reminders(self) -> dict:
        now = datetime.now(timezone.utc)
        reminder_threshold = now + timedelta(days=2)
        sent_reminders = []

        for book in books:
            due_date = book.get("due_date")
            borrowed_by = book.get("borrowed_by")

            if book["is_available"] or due_date is None or borrowed_by is None:
                continue

            if book.get("due_reminder_sent", False):
                continue

            due_date_time = datetime.fromisoformat(due_date)

            if due_date_time <= reminder_threshold:
                notification = self.notification_service.send(
                    user_id=borrowed_by,
                    title="Book Due Reminder",
                    message=f"{book['title']} must be returned by {book['due_date']}.",
                )

                event = self.message_broker.publish(
                    "BOOK_DUE_REMINDER_SENT",
                    f"Due reminder sent to {borrowed_by} for {book['title']}.",
                )

                book["due_reminder_sent"] = True
                sent_reminders.append({"book": book, "notification": notification, "event": event})

        return {
            "success": True,
            "sent_reminders": sent_reminders,
            "message": f"{len(sent_reminders)} due reminder(s) sent.",
        }

    #searches books by title,author and category.
    def search_books(self, query: str) -> list[dict]:
        query = query.lower()

        return [
            {**book, "queue_count": len(book.get("waiting_queue", []))}
            for book in books
            if query in book.get("title", "").lower()
            or query in book.get("author", "").lower()
            or query in book.get("category", "").lower()
        ]

    #adds a user to the waiting queue of a borrowed book
    def subscribe_to_book(self, book_id: int, user_id: str) -> dict:
        book = self._find_book(book_id)

        if book is None:
            return {"success": False, "message": "Book not found."}

        if book["is_available"]:
            return {"success": False, "message": "Book is already available."}

        if book.get("borrowed_by") == user_id:
            return {"success": False, "message": "You already borrowed this book."}

        if user_id in book["waiting_queue"]:
            return {"success": False, "message": "User is already in the queue."}

        book["waiting_queue"].append(user_id)

        event = self.message_broker.publish(
            "BOOK_SUBSCRIBED",
            f"{user_id} subscribed to {book['title']}.",
        )

        return {
            "success": True,
            "message": "User subscribed and added to waiting queue.",
            "book": book,
            "event": event,
        }

    #returns books that a user is waiting for with queue position.
    def get_user_waiting_books(self, user_id: str) -> list[dict]:
        return [
            {
                **book,
                "queue_position": book["waiting_queue"].index(user_id) + 1,
                "queue_count": len(book["waiting_queue"]),
            }
            for book in books
            if user_id in book["waiting_queue"]
        ]

    #returns books currently borrowed by a specific user.
    def get_user_borrowed_books(self, user_id: str) -> list[dict]:
        return [
            {**book, "queue_count": len(book.get("waiting_queue", []))}
            for book in books
            if book.get("borrowed_by") == user_id
        ]

    #botifies the next user in a book's waiting queue.
    def notify_next_book_waiting_user(self, book: dict) -> dict | None:
        """Consumer tarafından POST /books/{book_id}/notify-next üzerinden çağrılır."""
        if not book["waiting_queue"]:
            book["notified_user"] = None
            book["reserved_until"] = None
            return None

        next_user = book["waiting_queue"].pop(0)
        reserved_until = datetime.now(timezone.utc) + timedelta(seconds=20)

        book["notified_user"] = next_user
        book["reserved_until"] = reserved_until.isoformat()

        notification = self.notification_service.send(
            user_id=next_user,
            title="Book Available",
            message=f"{book['title']} is now available for you. Please reserve it within 20 seconds.",
        )

        self.message_broker.publish(
            "BOOK_QUEUE_NOTIFICATION_SENT",
            f"Notification sent to {next_user} for {book['title']}.",
        )

        Timer(20, self.check_expired_book_pickups).start()

        return notification

    #marks a borrowed book as returned and publishes a BOOK_RETURNED event.
    def return_book(self, book_id: int) -> dict:
        book = self._find_book(book_id)

        if book is None:
            return {"success": False, "message": "Book not found."}

        if book["is_available"]:
            return {"success": False, "message": "Book is already available."}

        previous_borrower = book.get("borrowed_by")

        book["is_available"] = True
        book["borrowed_by"] = None
        book["due_date"] = None
        book["due_reminder_sent"] = False

        event = self.message_broker.publish(
            "BOOK_RETURNED",
            f"{book['title']} was returned by {previous_borrower}. book_id:{book_id}",
        )
        return {
            "success": True,
            "message": "Book returned successfully.",
            "book": book,
            "event": event,
        }

    #adds a new book to the library and published a BOOK_ADDED event.
    def add_book(self, title: str, author: str, category: str) -> dict:
        new_book_id = max((book["id"] for book in books), default=0) + 1

        book = {
            "id": new_book_id,
            "title": title,
            "author": author,
            "category": category,
            "is_available": True,
            "borrowed_by": None,
            "due_date": None,
            "reserved_until": None,
            "notified_user": None,
            "due_reminder_sent": False,
            "waiting_queue": [],
        }

        books.append(book)

        event = self.message_broker.publish(
            "BOOK_ADDED",
            f"Admin added new book: {title} by {author} in category {category}.",
        )
        return {
            "success": True,
            "message": "Book added successfully.",
            "book": book,
            "event": event,
        }

    #moves to the next waiting user when a notified user does not reserve the book in time.
    def check_expired_book_pickups(self) -> dict:
        now = datetime.now(timezone.utc)
        expired_pickups = []

        for book in books:
            reserved_until = book.get("reserved_until")
            notified_user = book.get("notified_user")

            if not book["is_available"] or reserved_until is None or notified_user is None:
                continue

            reserved_until_time = datetime.fromisoformat(reserved_until)

            if reserved_until_time <= now:
                expired_pickups.append({
                    "book_id": book["id"],
                    "book_title": book["title"],
                    "expired_user": notified_user,
                })

                self.message_broker.publish(
                    "BOOK_PICKUP_EXPIRED",
                    f"{notified_user} did not reserve {book['title']} in time. book_id:{book['id']}",
                )

                book["notified_user"] = None
                book["reserved_until"] = None

                self.notify_next_book_waiting_user(book)

        return {
            "success": True,
            "expired_pickups": expired_pickups,
            "message": f"{len(expired_pickups)} expired book pickup(s) handled.",
        }

    # -----HELPER FUNCTIONS------

    #finds and returns a user by user ID.
    def _find_user(self, user_id: str) -> dict | None:
        return next((user for user in users if user["id"] == user_id), None)

    #finds and returns a seat by seat ID.
    def _find_seat(self, seat_id: str) -> dict | None:
        return next((seat for seat in seats if seat["id"] == seat_id), None)

    #finds and returns a book by book ID.
    def _find_book(self, book_id: int) -> dict | None:
        return next((book for book in books if book["id"] == book_id), None)