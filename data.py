seats = [
    {"id": "A1", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
    {"id": "A2", "is_available": False, "reserved_by": "user2","reserved_until":None, "qr_checked": False},
    {"id": "A3", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
    {"id": "A4", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
    {"id": "B1", "is_available": False, "reserved_by": "user3","reserved_until":None, "qr_checked": False},
    {"id": "B2", "is_available": True, "reserved_by": None,"reserved_until":None, "qr_checked": False},
]

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
    },
]


notifications = []

users = ["user1", "user2", "user3", "user4"]

seat_waiting_users = []


events = [
    {
        "type": "SYSTEM_STARTED",
        "message": "Library backend started without WebSocket usage.",
    }
]
