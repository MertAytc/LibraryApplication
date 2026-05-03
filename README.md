# Library Communication Patterns Backend

This backend demonstrates communication patterns without WebSocket.

## Patterns

- Client-server: mobile app sends HTTP requests to this backend.
- Request-response: endpoints such as `GET /seats` and `POST /seats/{seat_id}/reserve`.
- Queue: each borrowed book has a `waiting_queue`.
- Publish-subscribe: users subscribe to a book, and only related subscribers are notified when it is returned.
- Event-driven communication: important actions are stored in `/events`.

## Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start server:

```bash
uvicorn main:app --reload
```

Open API docs:

```text
http://127.0.0.1:8000/docs
```

## Example Flow

1. `GET /books`
2. `POST /books/1/subscribe`

```json
{
  "user_id": "user1"
}
```

3. `POST /books/1/return`
4. `GET /notifications/user1`
5. `GET /events`
