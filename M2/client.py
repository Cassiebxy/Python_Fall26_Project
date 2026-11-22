"""Command-line client for the PetStay TCP server."""

import argparse
import json
import socket
import sys

from protocol import decode_message, encode_message


SERVER_ADDRESS = ("127.0.0.1", 5050)
TIMEOUT = 5


def parse_request():
    """Turn command-line arguments into a PetStay request."""
    parser = argparse.ArgumentParser(description="PetStay command-line client")
    commands = parser.add_subparsers(dest="op", required=True)

    availability = commands.add_parser(
        "availability", help="Check the remaining spaces for each night"
    )
    availability.add_argument("pet_type")
    availability.add_argument("check_in", metavar="YYYY-MM-DD")
    availability.add_argument("check_out", metavar="YYYY-MM-DD")

    book = commands.add_parser("book", help="Book a stay for one pet")
    book.add_argument("owner_id")
    book.add_argument("pet_id")
    book.add_argument("pet_name")
    book.add_argument("pet_type")
    book.add_argument("check_in", metavar="YYYY-MM-DD")
    book.add_argument("check_out", metavar="YYYY-MM-DD")

    cancel = commands.add_parser("cancel", help="Cancel a booking")
    cancel.add_argument("booking_id")

    return vars(parser.parse_args())


def exchange(request):
    """Send one UTF-8 JSON line and read one complete reply."""
    message = encode_message(request)

    with socket.create_connection(SERVER_ADDRESS, timeout=TIMEOUT) as conn:
        conn.sendall(message)
        with conn.makefile("rb") as replies:
            line = replies.readline()

    if not line.endswith(b"\n"):
        raise ConnectionError("The server closed the connection before a complete reply.")

    reply = decode_message(line)
    if type(reply.get("ok")) is not bool:
        raise ValueError("The response must include a boolean 'ok' field.")

    return reply


def main():
    request = parse_request()

    try:
        reply = exchange(request)
    except ConnectionRefusedError:
        print("Connection refused. Start the PetStay server and try again.", file=sys.stderr)
        return 1
    except (TimeoutError, OSError, ValueError) as error:
        print(f"Could not confirm the result: {error}", file=sys.stderr)
        if request["op"] in ("book", "cancel"):
            print("Check whether the operation succeeded before retrying.", file=sys.stderr)
        return 1

    if not reply["ok"]:
        print(f"Error: {reply.get('error', 'Request failed')}", file=sys.stderr)
        return 1

    print(json.dumps(reply, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
