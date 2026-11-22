# PetStay M2 — Concept Map, Xinyi

Line numbers refer to the current `server.py` and `demo_server.py`.

Handoff note: Yizhen merges this table into README.md after integration.

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| TCP server and client connections | `server.py:21-32` (`serve`), `demo_server.py:34` (`framing_demo`) | The listening socket accepts each client and returns a separate socket for requests and replies. The server finishes handling that connection before accepting the next client. The demo opens real TCP connections to check this behavior. |
| TCP message framing | `server.py:10-18` (`handle`), `demo_server.py:34` (`framing_demo`) | Each JSON message ends with a newline. The server reads one line at a time so it can wait for the rest of a split request and read two requests sent together as separate messages. A trailing line without a newline is discarded when the client disconnects. |
| Connection error handling | `server.py:28-34` (`serve`), `demo_server.py:34` (`framing_demo`) | A connection error ends the current client session and the listening socket can accept another client. The framing demo verifies that a new client can connect after the previous client closes with an incomplete request. |
| Separation of networking and application logic | `server.py:17-18` (`handle`), `server.py:37-42` (`main`) | The server loads shared state once and passes it to the request handler for each client. The protocol functions handle request parsing and reply serialization. The same network code can run with echo functions during the demo. |

Contribution: Xinyi implemented the TCP server, newline framing, connection handling, and server demos. Both framing and query checks passed over TCP.
