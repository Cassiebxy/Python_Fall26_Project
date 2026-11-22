# PetStay M2 — Concept Map, Kyrie

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Documented protocol and validation | [Network protocol](README.md#network-protocol), `protocol.py:9-16`, `protocol.py:53-74` | The same required fields appear in the README and the server's validation. The protocol checks field types and the date spelling before passing the dates to M1 for calendar and range validation. |
| Shared JSON serialization | `protocol.py:19-41`, `client.py:41-57` | Both programs call the same codecs for UTF-8 JSON objects. The encoder appends the newline and the server sends the full reply with `sendall()`. |
| Request dispatch and layer separation | `server.py:10-18`, `protocol.py:76-81`, `state.py:39-57` | The handler queries the current service and calls the state methods for writes. Those methods save before returning so the handler confirms only persisted changes. |
| Error handling | `protocol.py:44-65`, `protocol.py:82-85` | Invalid input is returned as an error reply so the server can continue processing lines. The handler returns `save failed` for failed saves and uses the M1 message for a rejected business operation. |
| Runnable protocol demo | `demo_protocol.py:24-86`, `demo_server.py:57-77` | The protocol demo uses a temporary save file and checks reply shapes, booking rejection, and save failure. The server demo sends malformed JSON followed by a valid query over one TCP connection. |

Kyrie implemented the request protocol, integrated the shared codecs into the CLI, and added the protocol demo and README examples. Run `python3 demo_protocol.py` from `M2`.

OpenAI Codex helped implement and verify the protocol and update its documentation.
