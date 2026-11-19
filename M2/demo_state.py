import json
import os
import subprocess
import sys
import tempfile

from models import (
    AreaFullError,
    DuplicateReservationError,
    InvalidDateError,
    InvalidSaveDataError,
    ReservationAlreadyCancelledError,
    ReservationNotFoundError,
    SaveFileError,
    UnknownPetTypeError,
)
from services import BookingService
from state import CAT_CAPACITY, DOG_CAPACITY, load_state

# Anita: state, save and restart checks
# AI assistance: Claude helped implement and verify.

HERE = os.path.dirname(os.path.abspath(__file__))
DEC_1, DEC_2, DEC_3, DEC_5 = "2026-12-01", "2026-12-02", "2026-12-03", "2026-12-05"


def _check(name, passed):
    """Print one check result"""
    print(f"  [{'OK' if passed else 'FAIL'}] {name}")
    assert passed, name


def _scenario(title, expect):
    print()
    print(f"  --- {title}")
    print(f"      expect: {expect}")


def _raises(error_type, operation):
    """Return the error message if operation raised error_type, else None."""
    try:
        operation()
    except error_type as error:
        return str(error)
    return None


def _file_bytes(path):
    with open(path, "rb") as file:
        return file.read()


def _dogs_left(state):
    return state.service.availability("dog", DEC_1, DEC_3)


def _restart_in_new_process(path):
    """Start a separate Python process that loads the save file and reports
    dog availability and booking statuses, like a server restart would."""
    code = (
        "import json, sys\n"
        "from state import load_state\n"
        "state = load_state(sys.argv[1])\n"
        f"left = state.service.availability('dog', '{DEC_1}', '{DEC_3}')\n"
        "statuses = {i: r.status for i, r in state.service.reservations_snapshot().items()}\n"
        "print(json.dumps({'left': left, 'statuses': statuses}))\n"
    )
    result = subprocess.run([sys.executable, "-c", code, path], cwd=HERE,
                            capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def demo_anita_state():
    print("== Anita: server state, saving and restart ==")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "petstay_data.json")

        _scenario("First start", "no file yet: start empty with default capacities and save at once")
        state = load_state(path)
        _check("first start creates the save file", os.path.exists(path))
        saved = json.loads(_file_bytes(path))
        _check("saved capacities are the defaults",
               [(a["kind"], a["capacity"]) for a in saved["areas"]]
               == [("cat", CAT_CAPACITY), ("dog", DOG_CAPACITY)])
        _check("all dog nights are free", _dogs_left(state) == {DEC_1: 1, DEC_2: 1})

        _scenario("Book, then restart", "the booking is on disk before it is confirmed")
        milo = state.book("o1", "p1", "Milo", "dog", DEC_1, DEC_3)
        _check("booking takes both dog nights", _dogs_left(state) == {DEC_1: 0, DEC_2: 0})
        restarted = _restart_in_new_process(path)
        _check("a new process sees the booking after restart",
               restarted["left"] == {DEC_1: 0, DEC_2: 0}
               and restarted["statuses"] == {milo: "active"})

        _scenario("Cancel, then restart", "the cancellation is on disk and frees both nights")
        state.cancel(milo)
        restarted = _restart_in_new_process(path)
        _check("a new process sees the cancellation after restart",
               restarted["left"] == {DEC_1: 1, DEC_2: 1}
               and restarted["statuses"] == {milo: "cancelled"})
        state = load_state(path)
        _check("reloaded state matches the state before restart",
               _dogs_left(state) == {DEC_1: 1, DEC_2: 1})

        _scenario("Queries", "availability never writes to disk")
        before_bytes, before_time = _file_bytes(path), os.stat(path).st_mtime_ns
        for _ in range(3):
            state.service.availability("dog", DEC_1, DEC_3)
            state.service.availability("cat", DEC_1, DEC_3)
        _check("file unchanged after six queries",
               _file_bytes(path) == before_bytes and os.stat(path).st_mtime_ns == before_time)

        _scenario("Capacity-1 dog area",
                  "a two-night request fails if one night is full, and the other night stays free")
        rex = state.book("o2", "p2", "Rex", "dog", DEC_2, DEC_3)
        before_bytes, before_state = _file_bytes(path), state.service.to_dict()
        message = _raises(AreaFullError, lambda: state.book("o3", "p3", "Coco", "dog", DEC_1, DEC_3))
        _check("two-night request is rejected because the second night is full", message is not None)
        print(f"         reason: {message}")
        _check("first night is still free", _dogs_left(state) == {DEC_1: 1, DEC_2: 0})
        _check("rejected booking leaves file and memory unchanged",
               _file_bytes(path) == before_bytes and state.service.to_dict() == before_state)

        _scenario("Overlap and adjacent stays", "overlapping stays are rejected, back-to-back stays are allowed")
        before_bytes = _file_bytes(path)
        _check("overlapping stay for the same pet is rejected",
               _raises(DuplicateReservationError,
                       lambda: state.book("o2", "p2", "Rex", "dog", DEC_1, DEC_3)) is not None)
        _check("rejected overlap leaves the file unchanged", _file_bytes(path) == before_bytes)
        state.book("o2", "p2", "Rex", "dog", DEC_3, DEC_5)
        _check("stay starting on the previous check-out day is accepted and saved",
               BookingService.load(path).availability("dog", DEC_3, DEC_5)
               == {DEC_3: 0, "2026-12-04": 0})

        _scenario("Other rejected requests", "each raises its M1 error and leaves the file unchanged")
        before_bytes, before_state = _file_bytes(path), state.service.to_dict()
        rejected = [
            ("cancel an already cancelled booking", ReservationAlreadyCancelledError,
             lambda: state.cancel(milo)),
            ("cancel an unknown booking", ReservationNotFoundError,
             lambda: state.cancel("no-such-id")),
            ("book an unsupported pet type", UnknownPetTypeError,
             lambda: state.book("o4", "p4", "Tweety", "bird", DEC_1, DEC_3)),
            ("book with check-out before check-in", InvalidDateError,
             lambda: state.book("o4", "p4", "Kiki", "cat", DEC_3, DEC_1)),
        ]
        for label, error_type, operation in rejected:
            _check(f"rejected: {label}", _raises(error_type, operation) is not None)
        _check("rejected requests leave file and memory unchanged",
               _file_bytes(path) == before_bytes and state.service.to_dict() == before_state)

        _scenario("Save failure", "if the file cannot be written, the change is not confirmed")
        os.rename(path, path + ".backup")
        os.mkdir(path)   # a folder where the save file should be: writing must fail
        before_state = state.service.to_dict()
        message = _raises(SaveFileError, lambda: state.book("o5", "p5", "Luna", "cat", DEC_1, DEC_3))
        _check("booking raises SaveFileError when saving fails", message is not None)
        _check("cancellation raises SaveFileError when saving fails",
               _raises(SaveFileError, lambda: state.cancel(rex)) is not None)
        _check("failed saves leave the in-memory state unchanged",
               state.service.to_dict() == before_state)
        _check("Luna's unconfirmed booking is not in memory",
               state.service.availability("cat", DEC_1, DEC_3) == {DEC_1: 2, DEC_2: 2})
        os.rmdir(path)
        os.rename(path + ".backup", path)
        _check("after a restart the server still matches the last confirmed save",
               load_state(path).service.to_dict() == before_state)

        _scenario("Bad save file at startup", "the server refuses to start instead of overwriting bookings")
        good = json.loads(_file_bytes(path))
        bad = json.loads(_file_bytes(path))
        bad["areas"][1]["occupancy"][DEC_1] = 1   # Milo is cancelled: no dog on Dec 1
        with open(path, "w", encoding="utf-8") as file:
            json.dump(bad, file)
        bad_bytes = _file_bytes(path)
        message = _raises(InvalidSaveDataError, lambda: load_state(path))
        _check("inconsistent file is rejected at startup", message is not None)
        print(f"         reason: {message}")
        _check("rejected file is left untouched", _file_bytes(path) == bad_bytes)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(good, file)
        _check("restoring the good file lets the server start again",
               load_state(path).service.to_dict() == state.service.to_dict())
    print()


def main():
    demo_anita_state()
    print("Anita state checks: all passed.")


if __name__ == "__main__":
    main()
