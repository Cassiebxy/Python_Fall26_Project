"""Encode PetStay messages and dispatch one request at a time."""

import json
import re


# Kyrie: network protocol, request dispatch, and error replies
# AI assistance: OpenAI Codex helped implement and verify this module.
DATE_FIELDS = ("check_in", "check_out")
DATE_FORMAT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
STAY_FIELDS = ("pet_type",) + DATE_FIELDS
REQUEST_FIELDS = {
    "availability": STAY_FIELDS,
    "book": ("owner_id", "pet_id", "pet_name") + STAY_FIELDS,
    "cancel": ("booking_id",),
}


def encode_message(message):
    """Encode a JSON object as one UTF-8 line, including the final newline."""
    return (json.dumps(message, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _reject_constant(value):
    raise ValueError(f"{value} is not a JSON value")


def decode_message(line):
    """Decode one complete line and require a JSON object."""
    try:
        message = json.loads(line.decode("utf-8"), parse_constant=_reject_constant)
    except RecursionError as error:
        raise ValueError("The JSON message is nested too deeply.") from error
    if not isinstance(message, dict):
        raise ValueError("A PetStay message must be a JSON object.")
    return message


def send(conn, reply):
    """Send the complete encoded reply to a connected client."""
    conn.sendall(encode_message(reply))


def _error(message):
    return {"ok": False, "error": message}


def process_line(line, state):
    """Validate a framed request and use the server's current booking state."""
    # Only the server dispatches domain operations. The client uses the codecs.
    from models import BookingError, InvalidDateError, SaveFileError

    try:
        request = decode_message(line)
    except ValueError:
        return _error("bad request")

    operation = request.get("op")
    if not isinstance(operation, str):
        return _error("bad request")
    fields = REQUEST_FIELDS.get(operation)
    if fields is None:
        return _error("unknown op")
    if any(not isinstance(request.get(field), str) for field in fields):
        return _error("bad request")

    arguments = {field: request[field] for field in fields}
    try:
        if operation in ("availability", "book"):
            # The protocol fixes the date format. The service checks the dates and range.
            for field in DATE_FIELDS:
                value = arguments[field]
                if DATE_FORMAT.fullmatch(value) is None:
                    raise InvalidDateError(f"invalid date string: {value!r}")

        if operation == "availability":
            return {"ok": True, "remaining": state.service.availability(**arguments)}
        if operation == "book":
            return {"ok": True, "booking_id": state.book(**arguments)}
        state.cancel(**arguments)
        return {"ok": True}
    except SaveFileError:
        return _error("save failed")
    except BookingError as error:
        return _error(str(error))
