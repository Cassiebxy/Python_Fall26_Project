# PetStay M2 — Concept Map, Yizhen

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Command-line argument parsing | `client.py:13-36` (`parse_request`) | `argparse` defines three subcommands: `availability`, `book`, and `cancel`. Each takes the fields required for that operation. The selected subcommand becomes the request's `op` field. |
| TCP client connection | `client.py:9-10`, `client.py:43-46` (`exchange`) | The client connects to `127.0.0.1:5050` with a five-second timeout. Each command opens one connection, sends one request, reads one reply, and closes the connection. |
| JSON serialization and message framing | `client.py:39-55` (`exchange`) | The client encodes the request as UTF-8 JSON followed by a newline. It reads one response line, checks that it ends with a newline, and decodes it as JSON. This matches the server's one-message-per-line protocol. |
| Error handling | `client.py:48-53`, `client.py:61-74` | The client reports refused connections, timeouts, incomplete or invalid replies, and errors returned by the server. If a booking or cancellation cannot be confirmed, it tells the user to check the outcome before retrying. |
| Separation of client and server responsibilities | `client.py:13-36`, `client.py:39-55`, `client.py:58-77` | The client collects input, exchanges messages, and displays the result. The server owns the booking rules, reservation state, and persistence. |

Contribution: Yizhen implemented the PetStay command-line client for checking nightly availability, booking a stay, and cancelling a reservation.

AI assistance: OpenAI Codex helped draft `client.py` and this concept map.
