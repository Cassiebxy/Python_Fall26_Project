# PetStay M2

PetStay is a command-line pet boarding system. Users can check nightly availability, book a stay for one pet, and cancel a reservation. M2 builds on the M1 booking rules by adding a TCP client, a TCP server, and persistent state managed by the server.

## Run the project

Use Python 3.7 or later. No third-party packages are required.

Start the server from the repository root in terminal 1.

```bash
cd M2
python3 server.py
```

Open terminal 2 at the repository root and run the client commands.

```bash
cd M2
python3 client.py availability dog 2026-12-01 2026-12-03
python3 client.py book o1 p1 Milo dog 2026-12-01 2026-12-03
python3 client.py cancel YOUR_BOOKING_ID
```

Replace `YOUR_BOOKING_ID` with the ID returned by `book`. Dates use `YYYY-MM-DD`. A stay includes the check-in date and excludes the check-out date. Successful replies are printed as JSON. Errors are printed to standard error and the client exits with a nonzero status.

## Architecture

| File | Responsibility |
|---|---|
| `client.py` | Parses commands, sends requests, and displays replies. |
| `server.py` | Listens on `127.0.0.1:5050`, reads complete request lines, and passes them to the request handler. |
| `protocol.py` | Encodes and decodes network messages, validates requests, and dispatches operations. |
| `state.py` | Loads and manages the server's shared `BookingService`. It saves bookings and cancellations before publishing the updated state. |
| `models.py` and `services.py` | Provide the M1 boarding areas, reservations, booking rules, and JSON persistence. |

TCP provides reliable, ordered delivery. PetStay uses a newline to mark each message boundary in the TCP byte stream. The server handles connections sequentially and shares the same booking state across clients.

On its first start, the server creates `M2/petstay_data.json` with two cat spaces and one dog space per night. Availability queries read the current state. Booking and cancellation are applied to a copy of the service. After saving succeeds, that copy becomes the current state. The save file stores the full system state as one JSON document.

## Network protocol

Each request and reply is one UTF-8 JSON object followed by a newline. The fields shown for each request are required strings. Nightly availability counts are integers.

| Operation | Example request | Example successful reply |
|---|---|---|
| `availability` | `{"op":"availability","pet_type":"dog","check_in":"2026-12-01","check_out":"2026-12-03"}` | `{"ok":true,"remaining":{"2026-12-01":1,"2026-12-02":1}}` |
| `book` | `{"op":"book","owner_id":"o1","pet_id":"p1","pet_name":"Milo","pet_type":"dog","check_in":"2026-12-01","check_out":"2026-12-03"}` | `{"ok":true,"booking_id":"<id>"}` |
| `cancel` | `{"op":"cancel","booking_id":"<id>"}` | `{"ok":true}` |

Error replies contain `"ok":false` and an `error` string. Invalid UTF-8, malformed JSON, a non-object request, missing fields, or incorrect field types produce `{"ok":false,"error":"bad request"}`. An unsupported string `op` produces `{"ok":false,"error":"unknown op"}`. A failed save produces `{"ok":false,"error":"save failed"}`. Business-rule rejections preserve the M1 message, for example `{"ok":false,"error":"dog area has no place left on 2026-12-02"}`.

| Operation | Examples of business errors |
|---|---|
| `availability` | Unsupported pet type or invalid dates. |
| `book` | Unsupported pet type, invalid dates or identity fields, a full night, an overlapping active reservation, or a save failure. |
| `cancel` | Unknown booking ID, an already cancelled reservation, or a save failure. |

The client reports refused connections, timeouts, incomplete replies, and invalid responses. If a booking or cancellation cannot be confirmed after a connection or response error, the client asks the user to check the outcome before retrying.

## Demos

Run these commands from the `M2` directory.

| Command | Setup and expected behavior |
|---|---|
| `python3 demo_client.py connection-refused` | With the server stopped, checks that the CLI exits with a nonzero status and displays `Connection refused`. |
| `python3 demo_protocol.py` | Uses temporary data to check UTF-8 serialization, request validation, full-night and overlapping booking errors, cancellation, and failed-save replies. |
| `python3 demo_state.py` | Uses temporary data to verify persistence across process restarts, capacity and overlap rules, and failed saves. |
| `python3 demo_server.py framing` | First run `python3 demo_server.py echo-server` in another terminal. Checks split requests, multiple requests sent together, and reconnection after an incomplete request. Stop the echo server before starting the full server. |
| `python3 demo_server.py query` | With the full server running, checks availability and verifies that the same connection can process a valid query after malformed JSON. |
| `python3 demo_client.py workflow` | With the full server running, uses separate CLI processes to query, book, check reduced availability, cancel, and check restored availability. The demo needs one dog space on both demo nights. Use test data because the cancelled reservation record is retained. |

## Course concept map

Code locations refer to files inside `M2`.

| Contributor | Course concept | Code location | Why it is used |
|---|---|---|---|
| Xinyi | TCP server and connection lifecycle | `server.py:21-34` | The listening socket accepts clients and handles each on a separate connection. A connection error ends that session so the server can accept another client. |
| Xinyi | TCP message framing | `server.py:10-18`, `demo_server.py:34-53` | Reading one line at a time handles requests split across writes and multiple requests sent in one write. |
| Xinyi | Separation of networking and request handling | `server.py:10-18`, `server.py:37-42` | The server forwards complete requests to a handler. The framing demo can use the same server code with an echo handler. |
| Anita | Server-owned shared state | `state.py:18-66`, `state.py:69-83`, `server.py:41-42` | The server loads one state object and reuses it across connections, so clients see the same availability. |
| Anita | Persistence and JSON conversion | `state.py:59-66`, `services.py:161-273` | The state uses M1 serialization to make an independent copy and saves the copy before making it current. |
| Anita | Restart and failure handling | `demo_state.py:57-70`, `demo_state.py:73-184` | A separate process reloads saved data. The demo also checks that rejected bookings and failed saves preserve the previous state. |
| Yizhen | Command-line argument parsing | `client.py:15-38` | `argparse` collects the fields for each subcommand and puts the selected operation in the request's `op` field. |
| Yizhen | TCP client and JSON framing | `client.py:11-12`, `client.py:41-57` | The client opens a TCP connection with a timeout, sends one UTF-8 JSON line, and checks and decodes one complete reply. |
| Yizhen | Client error handling | `client.py:50-55`, `client.py:63-79` | The client reports connection and reply errors. If a booking or cancellation cannot be confirmed, the user is prompted to verify the outcome before retrying. |
| Yizhen | CLI workflow testing | `demo_client.py:25-32`, `demo_client.py:48-85` | The demo runs the actual CLI in separate processes to check shared availability, cancellation, and the connection-refused message. |
| Kyrie | Documented protocol and request validation | [Network protocol](#network-protocol), `protocol.py:9-16`, `protocol.py:53-74` | The examples match the fields the handler requires. Checking the message shape before dispatch lets the server reject malformed requests before touching the booking state. |
| Kyrie | Shared JSON serialization | `protocol.py:19-41`, `client.py:41-57` | Both programs use the same UTF-8 JSON codecs and agree on the trailing newline. |
| Kyrie | Request dispatch and layer separation | `server.py:10-18`, `protocol.py:76-81`, `state.py:39-57` | The protocol reads availability from the current service and routes bookings and cancellations through methods that save before returning. M1 still decides whether a requested stay is valid. |
| Kyrie | Request and domain error handling | `protocol.py:44-65`, `protocol.py:82-85`, `demo_protocol.py:37-86` | Invalid requests and rejected operations receive the same error shape. The save error tells the client that the change was never confirmed. |

## Team contributions

| Contributor | Contribution |
|---|---|
| Xinyi | TCP server, message framing, connection handling, and server demos. OpenAI Codex helped implement and verify this work. |
| Anita | Server-owned state, persistence, and restart and failure demos. |
| Yizhen | Command-line client, client demos, and README and concept-map consolidation. OpenAI Codex helped implement and verify this work. |
| Kyrie | Network protocol, shared JSON codecs, request dispatch, error responses, protocol demo, and protocol documentation. OpenAI Codex helped implement and verify this work. |
