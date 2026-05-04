from data import books, events, seats, seat_waiting_users, users,preference_options
from services.message_broker import MessageBroker
from services.notification_service import NotificationService
from datetime import datetime,timedelta,timezone
from threading import Timer


class LibraryServer:
    def __init__(self) -> None:
        self.message_broker = MessageBroker()
        self.notification_service = NotificationService()

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
    

    def login_user(self, user_id: str) -> dict:
        user = self._find_user(user_id)

        if user is None:
            return {
                "success": False,
                "message": "User not found.",
            }

        return {
            "success": True,
            "message": "Login successful.",
            "user": user,
        }
    
    def get_users(self) -> list[dict]:
        return users

    def update_user_preferences(
        self,
        user_id: str,
        favorite_categories: list[str],
        favorite_authors: list[str],
    ) -> dict:
        user = self._find_user(user_id)

        if user is None:
            return {
                "success": False,
                "message": "User not found.",
            }

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
    
    def get_user_preferences(self, user_id: str) -> dict:
        user = self._find_user(user_id)

        if user is None:
            return {
                "success": False,
                "message": "User not found.",
            }

        return {
            "success": True,
            "user_id": user["id"],
            "name": user["name"],
            "favorite_categories": user.get("favorite_categories", []),
            "favorite_authors": user.get("favorite_authors", []),
        }
    def get_preference_options(self) -> dict:
        return preference_options


    def get_seats(self) -> list[dict]:
        return seats
    
    def get_user_seat_reservation(self, user_id: str) -> dict:
        reservation = next(
            (
                seat
                for seat in seats
                if seat["reserved_by"] == user_id
            ),
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


    def reserve_seat(self, seat_id: str, user_id: str) -> dict:
        seat = self._find_seat(seat_id)

        if seat is None:
            return {"success": False, "message": "Seat not found."}

        existing_reservation = next(
            (
                seat_item
                for seat_item in seats
                if seat_item.get("reserved_by") == user_id
            ),
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

        occupancy_event = self.check_seat_occupancy()

        Timer(55, self.check_expired_seat_reservations).start()

        return {
            "success": True,
            "message": "Seat reserved successfully.",
            "seat": seat,
            "event": event,
            "occupancy_event": occupancy_event,
        }
    
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

        seat_notifications = self.notify_seat_waiting_users(seat_id)

        return {
            "success": True,
            "message": "Seat released successfully.",
            "seat": seat,
            "event": event,
            "seat_notifications": seat_notifications,
        }
    
    def check_seat_occupancy(self) -> dict | None:
        total_seats = len(seats)
        reserved_or_occupied_seats = len([
            seat for seat in seats
            if not seat["is_available"]
        ])

        occupancy_rate = reserved_or_occupied_seats / total_seats

        if occupancy_rate <= 0.8:
            return None

        event = self.message_broker.publish(
            "SEAT_OCCUPANCY_HIGH",
            f"Library seat occupancy is above 80%. Current occupancy: {occupancy_rate * 100:.0f}%.",
        )

        sent_notifications = []

        for user in users:
            notification = self.notification_service.send(
                user_id=user["id"],
                title="Library is crowded",
                message=f"Seat occupancy is above 80%. Current occupancy: {occupancy_rate * 100:.0f}%.",
            )
            sent_notifications.append(notification)

        self.message_broker.publish(
            "BROADCAST_NOTIFICATION_SENT",
            "High occupancy notification sent to all users.",
        )

        return {
            "event": event,
            "sent_notifications": sent_notifications,
            "occupancy_rate": occupancy_rate,
        }
    
    def subscribe_to_seat_availability(self, user_id: str) -> dict:
        available_seats = [
            seat for seat in seats
            if seat["is_available"]
        ]

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

    def notify_seat_waiting_users(self, seat_id: str) -> list[dict]:
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



    def check_expired_seat_reservations(self) -> dict:
        now = datetime.now(timezone.utc)
        expired_seats = []

        for seat in seats:
            reserved_until = seat.get("reserved_until")

            if seat["is_available"] or seat.get("qr_checked", False) or reserved_until is None:
                continue

            reserved_until_time = datetime.fromisoformat(reserved_until)

            if reserved_until_time <= now:
                expired_seats.append(seat["id"])

                seat["is_available"] = True
                seat["reserved_by"] = None
                seat["reserved_until"] = None
                seat["qr_checked"] = False

                self.message_broker.publish(
                    "SEAT_RESERVATION_EXPIRED",
                    f"Seat {seat['id']} reservation expired and became available again.",
                )

                self.notify_seat_waiting_users(seat["id"])

        return {
            "success": True,
            "expired_seats": expired_seats,
            "message": f"{len(expired_seats)} expired seat reservation(s) cleared.",
        }
    
    def get_seat_occupancy(self) -> dict:
        total_seats = len(seats)
        occupied_or_reserved = len([
            seat
            for seat in seats
            if not seat["is_available"]
        ])

        occupancy_rate = occupied_or_reserved / total_seats

        return {
            "total_seats": total_seats,
            "occupied_or_reserved": occupied_or_reserved,
            "available_seats": total_seats - occupied_or_reserved,
            "occupancy_rate": occupancy_rate,
            "occupancy_percent": round(occupancy_rate * 100, 2),
        }
   
 
    def get_books(self) -> list[dict]:
        return books
    
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
            }

        due_date = datetime.now(timezone.utc) + timedelta(seconds=60)

        book["is_available"] = False
        book["borrowed_by"] = user_id
        book["due_date"] = due_date.isoformat()
        book["reserved_until"] = None
        book["notified_user"] = None
        book["due_reminder_sent"]=False

        event = self.message_broker.publish(
            "BOOK_RESERVED",
            f"{book['title']} was reserved by {user_id}. Due date: {book['due_date']}.",
        )
        Timer(40, self.send_book_due_reminder, args=[book_id]).start()
        return {
            "success": True,
            "message": "Book reserved successfully.",
            "book": book,
            "event": event,
        }
    
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

                sent_reminders.append(
                    {
                        "book": book,
                        "notification": notification,
                        "event": event,
                    }
                )

        return {
            "success": True,
            "sent_reminders": sent_reminders,
            "message": f"{len(sent_reminders)} due reminder(s) sent.",
        }


    
    def search_books(self, query: str) -> list[dict]:
        query = query.lower()

        matched_books = [
            {
                **book,
                "queue_count": len(book.get("waiting_queue", [])),
            }
            for book in books
            if query in book.get("title", "").lower()
            or query in book.get("author", "").lower()
            or query in book.get("category", "").lower()
        ]

        return matched_books



    def subscribe_to_book(self, book_id: int, user_id: str) -> dict:
        book = self._find_book(book_id)

        if book is None:
            return {"success": False, "message": "Book not found."}

        if book["is_available"]:
            return {"success": False, "message": "Book is already available."}

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
    def get_user_waiting_books(self, user_id: str) -> list[dict]:
        waiting_books = []

        for book in books:
            if user_id in book["waiting_queue"]:
                waiting_books.append(
                    {
                        **book,
                        "queue_position": book["waiting_queue"].index(user_id) + 1,
                        "queue_count": len(book["waiting_queue"]),
                    }
                )

        return waiting_books
    
    def get_user_borrowed_books(self, user_id: str) -> list[dict]:
        borrowed_books = []

        for book in books:
            if book.get("borrowed_by") == user_id:
                borrowed_books.append(
                    {
                        **book,
                        "queue_count": len(book.get("waiting_queue", [])),
                    }
                )

        return borrowed_books

    
    def notify_next_book_waiting_user(self, book: dict) -> dict | None:
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

        published_event = self.message_broker.publish(
            "BOOK_RETURNED",
            f"{book['title']} was returned to the library by {previous_borrower}.",
        )

        notification = self.notify_next_book_waiting_user(book)

        return {
            "success": True,
            "message": "Book returned successfully by admin.",
            "book": book,
            "event": published_event,
            "notification": notification,
        }
    
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
            f"Admin added new book: {title} by {author} in {category}.",
        )

        matched_notifications = []

        for user in users:
            favorite_categories = user.get("favorite_categories", [])
            favorite_authors = user.get("favorite_authors", [])

            if category in favorite_categories or author in favorite_authors:
                notification = self.notification_service.send(
                    user_id=user["id"],
                    title="New Book Added",
                    message=f"{title} by {author} was added in your favorite category or author list.",
                )
                matched_notifications.append(notification)

        if matched_notifications:
            self.message_broker.publish(
                "NEW_BOOK_PREFERENCE_NOTIFICATION_SENT",
                f"New book notification sent to {len(matched_notifications)} user(s).",
            )

        return {
            "success": True,
            "message": "Book added successfully.",
            "book": book,
            "event": event,
            "matched_notifications": matched_notifications,
        }

    
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
                expired_pickups.append(
                    {
                        "book_id": book["id"],
                        "book_title": book["title"],
                        "expired_user": notified_user,
                    }
                )

                self.message_broker.publish(
                    "BOOK_PICKUP_EXPIRED",
                    f"{notified_user} did not reserve {book['title']} in time.",
                )

                book["notified_user"] = None
                book["reserved_until"] = None

                self.notify_next_book_waiting_user(book)

        return {
            "success": True,
            "expired_pickups": expired_pickups,
            "message": f"{len(expired_pickups)} expired book pickup(s) handled.",
        }


    def _find_user(self, user_id: str) -> dict | None:
        return next((user for user in users if user["id"] == user_id), None)

    def _find_seat(self, seat_id: str) -> dict | None:
        return next((seat for seat in seats if seat["id"] == seat_id), None)

    def _find_book(self, book_id: int) -> dict | None:
        return next((book for book in books if book["id"] == book_id), None)
