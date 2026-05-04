seats = [
    {"id": "A1", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
    {"id": "A2", "is_available": False, "reserved_by": "user2","reserved_until":None, "qr_checked": False},
    {"id": "A3", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
    {"id": "A4", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
    {"id": "B1", "is_available": False, "reserved_by": "user3","reserved_until":None, "qr_checked": False},
    {"id": "B2", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
]

preference_options = {
    "categories": [
        "Computer Networks",
        "Software Engineering",
        "Operating Systems",
        "Database Systems",
        "Artificial Intelligence",
    ],
    "authors": [
        "Andrew S. Tanenbaum",
        "Robert C. Martin",
        "Silberschatz",
        "Martin Fowler",
        "Stuart Russell",
    ],
}


books = [
    {
        "id": 1,
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "category": "Software Engineering",
        "is_available": False,
        "borrowed_by": "user2",
        "due_date": None,
        "reserved_until": None,
        "waiting_queue": [],
        "due_reminder_sent": False,
        "notified_user": None
    },
    {
        "id": 2,
        "title": "Computer Networks",
        "author": "Andrew S. Tanenbaum",
        "category": "Computer Networks",
        "is_available": True,
        "borrowed_by": None,
        "due_date": None,
        "reserved_until": None,
        "waiting_queue": [],
        "due_reminder_sent": False,
        "notified_user": None
    },
    {
        "id": 3,
        "title": "Operating System Concepts",
        "author": "Silberschatz",
        "category": "Operating Systems",
        "is_available": False,
        "borrowed_by": "user3",
        "due_date": None,
        "reserved_until": None,
        "waiting_queue": [],
        "due_reminder_sent": False,
        "notified_user": None
    },
]


notifications = []

users = [
    {
        "id": "user1",
        "name": "User One",
        "favorite_categories": [],
        "favorite_authors": [],
    },
    {
        "id": "user2",
        "name": "User Two",
        "favorite_categories": [],
        "favorite_authors": [],
    },
]


seat_waiting_users = []


events = [
    {
        "type": "SYSTEM_STARTED",
        "message": "Library backend started without WebSocket usage.",
    }
]
