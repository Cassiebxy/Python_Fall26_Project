# PetStay M2 — Concept Map, Yizhen

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Command-line argument parsing | `client.py:15-38` (`parse_request`) | `argparse` defines three subcommands: `availability`, `book`, and `cancel`. Each takes the fields required for that operation. The selected subcommand becomes the request's `op` field. |
| TCP client connection | `client.py:11-12`, `client.py:45-48` (`exchange`) | The client connects to `127.0.0.1:5050` with a five-second timeout. Each command opens one connection, sends one request, reads one reply, and closes the connection. |
| JSON serialization and message framing | `client.py:41-57` (`exchange`), `protocol.py:19-36` | The client uses the shared protocol functions to encode the request and decode the response. It reads one response line and checks that it ends with a newline. This matches the server's one-message-per-line protocol. |
| Error handling | `client.py:50-55`, `client.py:63-76` | The client reports refused connections, timeouts, incomplete or invalid replies, and errors returned by the server. If a booking or cancellation cannot be confirmed, it tells the user to check the outcome before retrying. |
| Separation of client and server responsibilities | `client.py:15-38`, `client.py:41-57`, `client.py:60-79` | The client collects input, exchanges messages, and displays the result. The server owns the booking rules, reservation state, and persistence. |

Contribution: Yizhen implemented the PetStay command-line client for checking nightly availability, booking a stay, and cancelling a reservation.

AI assistance: OpenAI Codex helped draft `client.py` and this concept map.
