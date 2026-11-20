# PetStay M2

PetStay is a command-line pet boarding system. Users can check nightly availability, book a stay for one pet, and cancel a reservation. M2 builds on the M1 booking rules by adding a TCP client, a TCP server, and persistent state managed by the server.

## Run the project

Use Python 3.7 or later. No third-party packages are required.

The full client-server workflow requires `protocol.py`. The state, connection-refusal, and echo-framing demos can run independently.

Once the protocol module is available, start the server from the repository root in terminal 1:

```bash
cd M2
python3 server.py
```

In terminal 2:

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
| `state.py` | Loads and manages the server's shared `BookingService`. It saves bookings and cancellations before publishing the updated state. |
| `models.py` and `services.py` | Provide the M1 boarding areas, reservations, booking rules, and JSON persistence. |

TCP provides reliable, ordered delivery. PetStay uses a newline to mark each message boundary in the TCP byte stream. The server handles connections sequentially and shares the same booking state across clients.

On its first start, the server creates `M2/petstay_data.json` with two cat spaces and one dog space per night. Availability queries read the current state. Booking and cancellation are applied to a copy of the service. After saving succeeds, that copy becomes the current state. The save file stores the full system state as one JSON document.

## Planned network protocol

Each request is one UTF-8 JSON object followed by a newline. Each reply is also one newline-terminated JSON object. The examples below show the team's planned interface.

| Operation | Example request | Example successful reply |
|---|---|---|
| `availability` | `{"op":"availability","pet_type":"dog","check_in":"2026-12-01","check_out":"2026-12-03"}` | `{"ok":true,"remaining":{"2026-12-01":1,"2026-12-02":1}}` |
| `book` | `{"op":"book","owner_id":"o1","pet_id":"p1","pet_name":"Milo","pet_type":"dog","check_in":"2026-12-01","check_out":"2026-12-03"}` | `{"ok":true,"booking_id":"<id>"}` |
| `cancel` | `{"op":"cancel","booking_id":"<id>"}` | `{"ok":true}` |

The planned error format is `{"ok":false,"error":"bad request"}`. The contract uses `bad request` for invalid UTF-8, malformed JSON, a non-object request, missing fields, or incorrect field types. It uses `unknown op` for unsupported operations and `save failed` for failed saves. Business-rule rejections use the corresponding M1 error message.

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
| `python3 demo_state.py` | Uses temporary data to verify persistence across process restarts, capacity and overlap rules, and failed saves. |
| `python3 demo_server.py framing` | First run `python3 demo_server.py echo-server` in another terminal. Checks split requests, multiple requests sent together, and reconnection after an incomplete request. Stop the echo server before starting the full server. |
| `python3 demo_server.py query` | With the full server running, checks availability and verifies that the same connection can process a valid query after malformed JSON. |
| `python3 demo_client.py workflow` | With the full server running, uses separate CLI processes to query, book, check reduced availability, cancel, and check restored availability. The demo needs one dog space on both demo nights. Use test data because the cancelled reservation record is retained. |

The standalone state and client connection-refusal demos passed. The full-server query and client workflow are pending protocol integration.

## Course concept map

Code locations refer to files inside `M2`.

| Contributor | Course concept | Code location | Why it is used |
|---|---|---|---|
| Xinyi | TCP server and connection lifecycle | `server.py:21-34` | The listening socket accepts clients and handles each on a separate connection. A connection error ends that session so the server can accept another client. |
| Xinyi | TCP message framing | `server.py:10-18`, `demo_server.py:34-54` | Reading one line at a time handles requests split across writes and multiple requests sent in one write. |
| Xinyi | Separation of networking and request handling | `server.py:10-18`, `server.py:37-42` | The server forwards complete requests to a handler. The framing demo can use the same server code with an echo handler. |
| Anita | Server-owned shared state | `state.py:19-67`, `state.py:69-83`, `server.py:41-42` | The server loads one state object and reuses it across connections, so clients see the same availability. |
| Anita | Persistence and JSON conversion | `state.py:59-67`, `services.py:161-202` | The state uses M1 serialization to make an independent copy and saves the copy before making it current. |
| Anita | Restart and failure handling | `demo_state.py:57-70`, `demo_state.py:73-184` | A separate process reloads saved data. The demo also checks that rejected bookings and failed saves preserve the previous state. |
| Yizhen | Command-line argument parsing | `client.py:13-36` | `argparse` collects the fields for each subcommand and puts the selected operation in the request's `op` field. |
| Yizhen | TCP client and JSON framing | `client.py:9-10`, `client.py:39-55` | The client opens a TCP connection with a timeout, sends one UTF-8 JSON line, and checks and decodes one complete reply. |
| Yizhen | Client error handling | `client.py:48-53`, `client.py:61-77` | The client reports connection and reply errors. If a booking or cancellation cannot be confirmed, the user is prompted to verify the outcome before retrying. |
| Yizhen | CLI workflow testing | `demo_client.py:25-32`, `demo_client.py:48-85` | The demo runs the actual CLI in separate processes to check shared availability, cancellation, and the connection-refused message. |
| Kyrie |  |  |  |

## Team contributions

| Contributor | Contribution |
|---|---|
| Xinyi | TCP server, message framing, connection handling, and server demos. |
| Anita | Server-owned state, persistence, and restart and failure demos. |
| Yizhen | Command-line client, client demos, and README and concept-map consolidation. |
| Kyrie |  |
