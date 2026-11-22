"""Verify the PetStay request and response contract with temporary data."""

from pathlib import Path
from tempfile import TemporaryDirectory

from protocol import decode_message, encode_message, process_line
from state import ServerState, load_state


# Kyrie: protocol checks, implemented and verified with OpenAI Codex.
DEC_1, DEC_2, DEC_3 = "2026-12-01", "2026-12-02", "2026-12-03"


def check(label, actual, expected):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
    print(f"  [OK] {label}")


def request(state, message):
    return process_line(encode_message(message), state)


def main():
    with TemporaryDirectory() as folder:
        path = Path(folder) / "petstay_data.json"
        state = load_state(path)
        query = {"op": "availability", "pet_type": "dog", "check_in": DEC_1, "check_out": DEC_3}
        book = dict(query, op="book", owner_id="o1", pet_id="p1", pet_name="米洛", check_in=DEC_2)

        frame = encode_message(book)
        check("The UTF-8 message ends with exactly one newline",
              frame.endswith(b"\n") and frame.count(b"\n") == 1
              and book["pet_name"].encode("utf-8") in frame, True)
        check("A non-ASCII pet name survives the JSON round trip", decode_message(frame), book)

        bad_requests = {
            "Invalid UTF-8": b"\xff\n",
            "Invalid JSON": b'{"op":\n',
            "Non-object request": b"[]\n",
            "Missing operation": b"{}\n",
            "Non-string operation": b'{"op":[]}\n',
            "Missing required field": b'{"op":"book","pet_type":"dog"}\n',
            "Incorrect field type": b'{"op":"cancel","booking_id":123}\n',
            "Non-JSON number": b'{"op":"cancel","booking_id":"missing","extra":NaN}\n',
        }
        for label, line in bad_requests.items():
            check(label, process_line(line, state), {"ok": False, "error": "bad request"})
        check("Unknown operation", request(state, {"op": "other"}),
              {"ok": False, "error": "unknown op"})
        check("Compact ISO dates are rejected", request(state, dict(query, check_in="20261201")),
              {"ok": False, "error": "invalid date string: '20261201'"})
        available = {"ok": True, "remaining": {DEC_1: 1, DEC_2: 1}}
        check("A valid query succeeds after malformed requests", request(state, query), available)

        booked = request(state, book)
        booking_id = booked.get("booking_id")
        check("A successful booking returns a booking ID",
              booked.get("ok") is True and isinstance(booking_id, str) and bool(booking_id), True)
        check("A full night rejects the entire stay",
              request(state, dict(book, pet_id="p2", check_in=DEC_1)),
              {"ok": False, "error": f"dog area has no place left on {DEC_2}"})
        check("The other night is still free", request(state, query),
              {"ok": True, "remaining": {DEC_1: 1, DEC_2: 0}})
        check("An overlapping booking returns the M1 error",
              request(state, dict(book, check_in=DEC_1)),
              {"ok": False, "error": f"pet 'p1' already has an overlapping reservation ({booking_id})"})
        adjacent = request(state, dict(book, check_in=DEC_3, check_out="2026-12-04"))
        check("An adjacent stay for the same pet succeeds", adjacent["ok"], True)

        cancel = {"op": "cancel", "booking_id": booking_id}
        # The parent directory does not exist, so the real save must fail.
        unavailable_file = ServerState(state.service, Path(folder) / "missing" / path.name)
        before = unavailable_file.service.to_dict()
        save_error = {"ok": False, "error": "save failed"}
        check("Booking save failure returns the protocol error",
              request(unavailable_file, dict(book, pet_type="cat", pet_id="p3")), save_error)
        check("Cancellation save failure returns the protocol error",
              request(unavailable_file, cancel), save_error)
        check("Failed saves leave the current state unchanged",
              unavailable_file.service.to_dict(), before)

        check("Cancellation has an ok-only response", request(state, cancel), {"ok": True})
        check("Repeat cancellation returns the M1 error", request(state, cancel),
              {"ok": False, "error": f"reservation {booking_id!r} has already been cancelled"})
        check("Cancellation restores both nights' availability", request(state, query), available)
    print("Kyrie protocol checks: all passed.")


if __name__ == "__main__":
    main()
