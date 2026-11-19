# PetStay M2 — Concept Map, Anita

Line numbers refer to the current `state.py`, `demo_state.py`, and the M2 copies of `services.py` and `server.py`.



| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Server owns the state | `state.py:19-67` (`ServerState`), `state.py:70-84` (`load_state`), called once at `server.py:41` | One `ServerState` object holds the only `BookingService`. The server creates it at startup and passes it to every request, so all clients see the same availability and clients can only change it by sending requests over the network. |
| Persistence with file I/O | `state.py:79-84`, reusing M1 `services.py:170-188` (`save`) and `services.py:189-202` (`load`) | On startup an existing save file is loaded with all M1 checks. A missing file starts the default cat and dog areas and is saved right away, so a restart reads the same capacities. M1's save writes a temporary file and then calls `os.replace`, so the previous save is never left half-written. |
| Validate before modifying (commit only after saving) | `state.py:40-67` (`book`, `cancel`, `_draft`, `_commit`) | Each booking or cancellation is tried on a copy of the service. The copy is saved first and becomes the current service only if the save worked. A rejected request or a failed save changes neither memory nor the file, so a reply never confirms a change that is not on disk, and each night's count always equals its active reservations. |
| Encapsulation with a read-only property | `state.py:29-38` (`_service`, `service` property) | Queries read `state.service`, but the service is kept in `_service` and replaced only by `_commit`. Writes have exactly two entry points, `book()` and `cancel()`, so no code path can change bookings without saving them. |
| Exception handling | `state.py:40-58` (docstrings list the errors), `state.py:66`, `state.py:70-78` | M1 booking errors pass through unchanged so the protocol can return their messages. A failed write raises M1's `SaveFileError`, which the protocol turns into `save failed`. A save file that cannot be read or is invalid raises an error at startup instead of being replaced, so a restart never wipes saved bookings. |
| JSON conversion (two uses) | `state.py:60-62` (`_draft`), M1 `to_dict`/`from_dict` at `services.py:161-169` and `services.py:203-274` | The save file stores the whole system as one JSON document, rebuilt with the M1 `to_dict`/`from_dict` methods. Protocol JSON (Kyrie) is different: one small JSON object per line for each request and reply. `_draft` also uses `to_dict`/`from_dict` to make an independent copy of the service. |
| Separation of layers | `state.py:1-6` (imports) | `state.py` imports only the M1 domain classes and has no sockets or JSON-line code. The network code calls it, so the same state object works with the real server, the demo, or a test. |
| Restart and failure checks | `demo_state.py:63-76` (restart in a new process), `demo_state.py:79-190` | Restarts run in a separate Python process that reads only the file, which proves the booking and the cancellation were saved. The demo also covers the capacity-1 dog area (a two-night request fails and the free night stays free), overlap and back-to-back stays, queries never writing to disk, a save failure that is not confirmed, and a bad file refused at startup. |

## Interface for the protocol (Kyrie)

```python
state.service.availability(pet_type, check_in, check_out)   # query, never saves
booking_id = state.book(owner_id, pet_id, pet_name, pet_type, check_in, check_out)
state.cancel(booking_id)                                     # returns None
```

- Read `state.service` again for each request, because `book()` and `cancel()` replace it.
- Never call `state.service.create_reservation` or `cancel_reservation` directly; those changes would not be saved.
- Catch `SaveFileError` **before** `BookingError`. `SaveFileError` is a subclass of `BookingError`, so catching `BookingError` first would send the file error text instead of `save failed`.

## Running

```bash
cd M2
python3 demo_state.py
```

The demo works in a temporary folder. The real server keeps its data in `M2/petstay_data.json`, which is created on the first start. Delete that file to start over with empty areas.

Contribution: Anita implemented `state.py` (the server-owned `ServerState`, `book`/`cancel` that commit only after saving, and `load_state` startup) and `demo_state.py` with the restart, save-failure, and bad-file checks. It was also tested end to end with `server.py` and a temporary protocol stub.  
