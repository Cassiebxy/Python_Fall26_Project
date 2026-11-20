"""Run PetStay client commands and check the results."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4


CLIENT = Path(__file__).with_name("client.py")
PET_TYPE = "dog"
CHECK_IN = "2026-12-01"
CHECK_OUT = "2026-12-03"
NIGHTS = {"2026-12-01", "2026-12-02"}


def check(label, passed, details=""):
    """Print one check result and stop if it failed."""
    print(f"  [{'OK' if passed else 'FAIL'}] {label}", flush=True)
    if not passed:
        raise RuntimeError(f"{label}. {details}".strip())


def run_client(*args):
    """Run the same CLI a user would run from the terminal."""
    return subprocess.run(
        [sys.executable, str(CLIENT), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def request(*args):
    """Run a client command and return its successful JSON reply."""
    result = run_client(*args)
    if result.returncode != 0:
        raise RuntimeError(f"{args[0]} failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def availability():
    reply = request("availability", PET_TYPE, CHECK_IN, CHECK_OUT)
    return reply["remaining"]


def booking_demo():
    print("== Yizhen: PetStay client workflow ==")

    before = availability()
    check("Availability returns the two stay nights", set(before) == NIGHTS)
    if any(before[night] < 1 for night in NIGHTS):
        raise RuntimeError(
            "The demo needs one dog space on each night. "
            "Use fresh test data or choose two available nights."
        )

    pet_id = f"demo-{uuid4()}"
    booking = request(
        "book", "demo-owner", pet_id, "Milo", PET_TYPE, CHECK_IN, CHECK_OUT
    )
    booking_id = booking.get("booking_id")
    check("Booking returns an ID", isinstance(booking_id, str) and bool(booking_id))

    # Release the demo booking even if the availability check fails.
    try:
        expected = {night: before[night] - 1 for night in NIGHTS}
        check("A separate client sees one fewer space each night",
              availability() == expected)
    finally:
        request("cancel", booking_id)
        print("  [OK] Cancellation succeeds", flush=True)

    check("Cancellation restores the original availability",
          availability() == before)


def connection_refused_demo():
    print("== Yizhen: Client connection error ==")
    result = run_client("availability", PET_TYPE, CHECK_IN, CHECK_OUT)
    check("Client exits with a nonzero status", result.returncode != 0)
    check("Client explains that the connection was refused",
          "Connection refused" in result.stderr,
          result.stderr.strip())


def main():
    parser = argparse.ArgumentParser(description="Run PetStay client demos")
    parser.add_argument("mode", choices=("workflow", "connection-refused"))
    args = parser.parse_args()

    try:
        if args.mode == "workflow":
            booking_demo()
        else:
            connection_refused_demo()
    except (RuntimeError, KeyError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"Demo failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
