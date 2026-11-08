
# Part 1 demo 

import copy
import json
import os
import tempfile
from datetime import date, datetime

from models import (
    AreaFullError,
    BoardingArea,
    CatArea,
    DogArea,
    DuplicateReservationError,
    InsufficientOccupancyError,
    InvalidCapacityError,
    InvalidDateError,
    InvalidSaveDataError,
    UnknownPetTypeError,
    ReservationAlreadyCancelledError,
    ReservationNotFoundError,
    SaveFileError,
)
from services import BookingService

# Fixed demo inputs: November 2026
CHECK_IN = date(2026, 11, 10)
CHECK_OUT = date(2026, 11, 12)   # check-out excluded

# JSON file written by Anita's demo, next to this script
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "petstay_data.json")


def _check(name, passed):
    """Print one check result"""
    print(f"  [{'OK' if passed else 'FAIL'}] {name}")
    assert passed, name


def demo_xinyi():
    print("== Xinyi: boarding areas and availability queries ==")

    # cat/dog reach the right area
    try:
        BoardingArea(2)
        raised = False
    except TypeError:
        raised = True
    _check("abstract class cannot be instantiated", raised)

    areas = [CatArea(2), DogArea(2)]  
    picked = {}
    for pet_type in ["cat", "dog"]:
        for area in areas:
            if area.accepts(pet_type):
                picked[pet_type] = area
        _check(f" {pet_type} reaches the correct area",
               picked[pet_type].kind == pet_type)

    service = BookingService(areas)
    before = [area.to_dict() for area in areas]
    first = service.availability("dog", CHECK_IN, CHECK_OUT)
    second = service.availability("dog", CHECK_IN, CHECK_OUT)
    after = [area.to_dict() for area in areas]

    _check("two queries give the same result", first == second)
    _check("state unchanged across queries", before == after)
    _check("per-night availability returned",
           first == {"2026-11-10": 2, "2026-11-11": 2})

    # Cat and dog areas are independent
    dog = picked["dog"]
    cat = picked["cat"]
    cat_before = cat.to_dict()

    dog.reserve(CHECK_IN, date(2026, 11, 11))   # occupies the night of Nov 10 only
    _check("areas independent: cat area unaffected", cat.to_dict() == cat_before)
    _check("areas independent: dog area has 1 left on Nov 10", dog.remaining(CHECK_IN) == 1)

    # Date limited
    nights = dog.availability(CHECK_IN, CHECK_OUT)
    _check("date boundary: only Nov 10 and Nov 11",
           sorted(nights) == ["2026-11-10", "2026-11-11"])

    # one booking over two nights
    tight = DogArea(1)
    tight.reserve(CHECK_IN, CHECK_OUT)

    _check("multi-night success: both nights at 0",
           tight.remaining(CHECK_IN) == 0
           and tight.remaining(date(2026, 11, 11)) == 0)

    # later night
    partial = CatArea(1)
    partial.reserve(date(2026, 11, 11), date(2026, 11, 12))
    snapshot = partial.to_dict()

    try:
        partial.reserve(CHECK_IN, CHECK_OUT)
        raised = False
    except AreaFullError:
        raised = True

    _check("later night full: AreaFullError raised", raised)
    _check("no partial booking: snapshot unchanged", partial.to_dict() == snapshot)

    # release a booked two-night stay
    released = DogArea(1)
    released.reserve(CHECK_IN, CHECK_OUT)
    released.release(CHECK_IN, CHECK_OUT)
    _check("release success: one place back on each night",
           released.remaining(CHECK_IN) == 1
           and released.remaining(date(2026, 11, 11)) == 1)

    # Failed release changes nothing
    tight_release = DogArea(1)
    tight_release.reserve(CHECK_IN, date(2026, 11, 11))
    snapshot = tight_release.to_dict()

    try:
        tight_release.release(CHECK_IN, CHECK_OUT)
        raised = False
    except InsufficientOccupancyError:
        raised = True
    _check("release failure: InsufficientOccupancyError raised", raised)
    _check("failed release changes nothing: snapshot unchanged",
           tight_release.to_dict() == snapshot)

    # Invalid dates
    invalid = DogArea(2)
    snapshot = invalid.to_dict()
    try:
        invalid.reserve(CHECK_IN, CHECK_IN)
        raised_equal = False
    except InvalidDateError:
        raised_equal = True
    try:
        invalid.reserve(CHECK_OUT, CHECK_IN)
        raised_backwards = False
    except InvalidDateError:
        raised_backwards = True

    _check("invalid dates: check-in == check-out rejected", raised_equal)
    _check("invalid dates: check-out before check-in rejected", raised_backwards)
    _check("state unchanged after invalid dates", invalid.to_dict() == snapshot)

    # Capacity initialization
    zero = CatArea(0)
    _check("capacity 0 can be created", zero.remaining(CHECK_IN) == 0)
    try:
        zero.reserve(CHECK_IN, CHECK_OUT)
        raised_zero = False
    except AreaFullError:
        raised_zero = True
    _check("capacity 0 cannot be booked", raised_zero)

    for bad_capacity in [-1, 1.5, True, False]:
        try:
            CatArea(bad_capacity)
            raised_bad = False
        except InvalidCapacityError:
            raised_bad = True
        _check(f"invalid capacity {bad_capacity!r} rejected", raised_bad)

    # Copy isolation
    copy_area = CatArea(2)
    copy_area.reserve(CHECK_IN, date(2026, 11, 11))
    exported = copy_area.to_dict()
    exported["occupancy"]["2026-11-10"] = 99
    exported["capacity"] = 99

    _check("copy isolation: original object unaffected",
           copy_area.to_dict()["occupancy"] == {"2026-11-10": 1}
           and copy_area.capacity == 2)
    _check("to_dict has kind/capacity/occupancy",
           sorted(exported) == ["capacity", "kind", "occupancy"])

    # Unknown pet type
    try:
        service.availability("bird", CHECK_IN, CHECK_OUT)
        raised_unknown = False
    except UnknownPetTypeError:
        raised_unknown = True
    _check("unknown pet type raises an error", raised_unknown)

    # datetime includes a time 
    timed = datetime(2026, 11, 10, 12)
    date_area = DogArea(1)
    date_service = BookingService([date_area])
    snapshot = date_area.to_dict()
    for label, operation in [
        ("remaining", lambda: date_area.remaining(timed)),
        ("reserve", lambda: date_area.reserve(timed, CHECK_OUT)),
        ("release", lambda: date_area.release(CHECK_IN, timed)),
        ("service query", lambda: date_service.availability("dog", timed, CHECK_OUT)),
    ]:
        try:
            operation()
            rejected = False
        except InvalidDateError:
            rejected = True
        _check(f"datetime rejected by {label}", rejected)
    _check("datetime rejection leaves state unchanged", date_area.to_dict() == snapshot)

    print()


def demo_kyrie():
    print("== Kyrie: reservation creation ==")
    second_night = date(2026, 11, 11)
    next_check_out = date(2026, 11, 13)

    dog = DogArea(2)
    service = BookingService([dog])
    first_id = service.create_reservation(
        "owner-1", "pet-1", "Milo", "dog", CHECK_IN.isoformat(), CHECK_OUT.isoformat()
    )
    records = service.reservations_snapshot()
    _check(
        "A3: one active reservation created",
        len(records) == 1 and records[first_id].status == "active",
    )
    _check(
        "A3: both nights reserved and check-out day still free",
        service.availability("dog", CHECK_IN, next_check_out)
        == {"2026-11-10": 1, "2026-11-11": 1, "2026-11-12": 2},
    )

    tight_dog = DogArea(1)
    tight_service = BookingService([tight_dog])
    tight_service.create_reservation(
        "owner-1", "pet-1", "Milo", "dog", second_night, CHECK_OUT
    )
    records_before = tight_service.reservations_snapshot()
    area_before = tight_dog.to_dict()
    try:
        tight_service.create_reservation("owner-2", "pet-2", "Luna", "dog", CHECK_IN, CHECK_OUT)
        rejected = False
    except AreaFullError:
        rejected = True
    _check("A4: a full second night rejects the whole stay", rejected)
    _check(
        "A4: records and nightly occupancy unchanged",
        tight_service.reservations_snapshot() == records_before and tight_dog.to_dict() == area_before,
    )

    rejected_stays = [
        ("A8: same-day stay rejected", CHECK_IN, CHECK_IN, InvalidDateError),
        ("A8: reversed dates rejected", CHECK_OUT, CHECK_IN, InvalidDateError),
        ("A11: identical stay rejected", CHECK_IN, CHECK_OUT, DuplicateReservationError),
        ("A11: partially overlapping stay rejected", second_night, next_check_out, DuplicateReservationError),
    ]
    records_before = service.reservations_snapshot()
    area_before = dog.to_dict()
    for label, start, end, expected_error in rejected_stays:
        try:
            service.create_reservation("owner-1", "pet-1", "Milo", "dog", start, end)
            rejected = False
        except expected_error:
            rejected = True
        _check(label, rejected)
        _check(
            "records and nightly occupancy unchanged",
            service.reservations_snapshot() == records_before and dog.to_dict() == area_before,
        )

    adjacent_id = service.create_reservation(
        "owner-1", "pet-1", "Milo", "dog", CHECK_OUT, next_check_out
    )
    _check(
        "A12: the same pet can check in on its previous check-out day",
        adjacent_id != first_id and dog.remaining(CHECK_OUT) == 1,
    )

    other_id = service.create_reservation("owner-2", "pet-2", "Luna", "dog", CHECK_IN, CHECK_OUT)
    _check(
        "A13: a different pet can stay on the same nights when there is capacity",
        other_id not in (first_id, adjacent_id)
        and service.availability("dog", CHECK_IN, CHECK_OUT) == {"2026-11-10": 0, "2026-11-11": 0},
    )
    print()

def demo_yizhen():
    print("== Yizhen: reservation cancellation ==")

    dog = DogArea(1)
    service = BookingService([dog])

    booking_id = service.create_reservation(
        "owner-1",
        "pet-1",
        "Milo",
        "dog",
        CHECK_IN,
        CHECK_OUT,
    )

    service.cancel_reservation(booking_id)

    records = service.reservations_snapshot()
    _check(
        "A5: cancelled reservation is retained with cancelled status",
        records[booking_id].status == "cancelled",
    )
    _check(
        "A5: both nights become available again",
        service.availability("dog", CHECK_IN, CHECK_OUT)
        == {"2026-11-10": 1, "2026-11-11": 1},
    )

    records_before = service.reservations_snapshot()
    area_before = dog.to_dict()

    try:
        service.cancel_reservation(booking_id)
        rejected = False
    except ReservationAlreadyCancelledError:
        rejected = True

    _check("A6: cancelling the same reservation twice is rejected", rejected)
    _check(
        "A6: repeated cancellation does not change records or occupancy",
        service.reservations_snapshot() == records_before
        and dog.to_dict() == area_before,
    )

    try:
        service.cancel_reservation("missing-booking-id")
        rejected = False
    except ReservationNotFoundError:
        rejected = True

    _check("A7: an unknown booking ID is rejected", rejected)
    _check(
        "A7: unknown ID does not change records or occupancy",
        service.reservations_snapshot() == records_before
        and dog.to_dict() == area_before,
    )

    new_booking_id = service.create_reservation(
        "owner-1",
        "pet-1",
        "Milo",
        "dog",
        CHECK_IN,
        CHECK_OUT,
    )

    new_records = service.reservations_snapshot()
    _check(
        "A14: the same pet can rebook the dates after cancellation",
        new_booking_id != booking_id
        and new_records[new_booking_id].status == "active",
    )

    print()


def _raises(error_type, operation):
    """Run operation; return the error message if it raised error_type, else None."""
    try:
        operation()
    except error_type as error:
        return str(error)
    return None


def demo_anita():
    print("== Anita: saving and loading ==")
    second_night = date(2026, 11, 11)

    # Build a state with active and cancelled bookings in both areas
    service = BookingService([CatArea(2), DogArea(1)])
    milo_id = service.create_reservation("owner-1", "pet-1", "Milo", "dog", CHECK_IN, CHECK_OUT)
    luna_id = service.create_reservation("owner-2", "pet-2", "Luna", "cat", CHECK_IN, CHECK_OUT)
    kiki_id = service.create_reservation("owner-3", "pet-3", "Kiki", "cat", CHECK_IN, second_night)
    service.cancel_reservation(kiki_id)

    service.save(SAVE_FILE)
    print(f"  saved to {os.path.basename(SAVE_FILE)}")
    with open(SAVE_FILE, encoding="utf-8") as file:
        saved = json.load(file)

    _check("saved file stores area kinds, capacities and occupancy",
           [(a["kind"], a["capacity"]) for a in saved["areas"]] == [("cat", 2), ("dog", 1)]
           and saved["areas"][1]["occupancy"] == {"2026-11-10": 1, "2026-11-11": 1})
    _check("saved file stores dates as YYYY-MM-DD text and keeps the status",
           saved["reservations"][2]["check_in"] == "2026-11-10"
           and saved["reservations"][2]["status"] == "cancelled")

    # A9: save then load
    loaded = BookingService.load(SAVE_FILE)
    _check("A9: booking IDs, fields and statuses match after loading",
           loaded.reservations_snapshot() == service.reservations_snapshot())
    _check("A9: capacity and nightly occupancy match after loading",
           loaded.to_dict() == service.to_dict())
    _check("A9: availability matches for both pet types",
           all(loaded.availability(pet, CHECK_IN, CHECK_OUT)
               == service.availability(pet, CHECK_IN, CHECK_OUT) for pet in ["cat", "dog"]))
    _check("A9: saved kind restores the concrete subclass",
           type(BoardingArea.from_dict(saved["areas"][0])) is CatArea
           and type(BoardingArea.from_dict(saved["areas"][1])) is DogArea)
    _check("cancelled reservation still occupies nothing after loading",
           loaded.availability("cat", CHECK_IN, CHECK_OUT)
           == {"2026-11-10": 1, "2026-11-11": 1})

    before = loaded.to_dict()
    _check("cancelling a loaded cancelled reservation is still rejected",
           _raises(ReservationAlreadyCancelledError,
                   lambda: loaded.cancel_reservation(kiki_id)) is not None)
    _check("rejected cancellation leaves the loaded state unchanged", loaded.to_dict() == before)

    # A10: keep booking and cancelling on the loaded service
    old_ids = set(loaded.reservations_snapshot())
    bella_id = loaded.create_reservation("owner-4", "pet-4", "Bella", "cat", CHECK_IN, CHECK_OUT)
    _check("A10: a new booking after loading gets a new unique ID",
           bella_id not in old_ids and len(loaded.reservations_snapshot()) == 4)
    _check("A10: the new booking takes the last cat place",
           loaded.availability("cat", CHECK_IN, CHECK_OUT) == {"2026-11-10": 0, "2026-11-11": 0})

    before = loaded.to_dict()
    _check("A10: duplicate check still works for a loaded pet",
           _raises(DuplicateReservationError, lambda: loaded.create_reservation(
               "owner-1", "pet-1", "Milo", "dog", second_night, date(2026, 11, 13))) is not None)
    _check("A10: capacity check still works for a loaded area",
           _raises(AreaFullError, lambda: loaded.create_reservation(
               "owner-5", "pet-5", "Coco", "dog", CHECK_IN, CHECK_OUT)) is not None)
    _check("A10: rejected bookings leave the loaded state unchanged", loaded.to_dict() == before)

    loaded.cancel_reservation(milo_id)
    _check("A10: cancelling a loaded active booking frees both nights",
           loaded.availability("dog", CHECK_IN, CHECK_OUT) == {"2026-11-10": 1, "2026-11-11": 1})
    _check("A10: the loaded copy is independent of the original service",
           service.to_dict() == saved)

    reloaded_file = SAVE_FILE + ".second"
    loaded.save(reloaded_file)
    _check("A10: a second save and load round trip keeps the state",
           BookingService.load(reloaded_file).to_dict() == loaded.to_dict())
    os.remove(reloaded_file)

    # A15 and other invalid save data: each tampered copy must be refused
    def tampered(change):
        data = copy.deepcopy(saved)
        change(data)
        return data

    def set_occupancy(kind_index, night, count):
        return lambda data: data["areas"][kind_index]["occupancy"].__setitem__(night, count)

    def reactivate_kiki_as_luna(data):
        # Kiki's record becomes a second active stay for Luna (pet-2); the cat
        # occupancy is raised to match, so only the overlap rule is broken
        data["reservations"][2].update(pet_id="pet-2", status="active")
        data["areas"][0]["occupancy"]["2026-11-10"] = 2

    bad_cases = [
        ("A15: occupancy lower than the active bookings", tampered(set_occupancy(1, "2026-11-10", 0))),
        ("A15: cancelled booking still counted in occupancy", tampered(set_occupancy(0, "2026-11-10", 2))),
        ("A15: occupancy on a night with no booking", tampered(set_occupancy(1, "2026-11-20", 1))),
        ("occupancy above capacity", tampered(set_occupancy(1, "2026-11-10", 2))),
        ("duplicate booking ID", tampered(lambda d: d["reservations"][2].update(booking_id=luna_id))),
        ("overlapping active bookings for one pet", tampered(reactivate_kiki_as_luna)),
        ("unknown area kind", tampered(lambda d: d["areas"][0].update(kind="bird"))),
        ("invalid capacity", tampered(lambda d: d["areas"][0].update(capacity=-1))),
        ("invalid date", tampered(lambda d: d["reservations"][0].update(check_in="2026-13-01"))),
        ("check-out not after check-in",
         tampered(lambda d: d["reservations"][0].update(check_out="2026-11-10"))),
        ("unknown status", tampered(lambda d: d["reservations"][0].update(status="pending"))),
        ("pet type with no area", tampered(lambda d: d["reservations"][2].update(pet_type="bird"))),
        ("missing reservation field", tampered(lambda d: d["reservations"][0].pop("pet_name"))),
    ]

    before = loaded.to_dict()
    with tempfile.TemporaryDirectory() as folder:
        bad_file = os.path.join(folder, "bad.json")
        for label, data in bad_cases:
            with open(bad_file, "w", encoding="utf-8") as file:
                json.dump(data, file)
            message = _raises(InvalidSaveDataError, lambda: BookingService.load(bad_file))
            _check(f"load rejected: {label}", message is not None)
            if label.startswith("A15"):
                print(f"         reason: {message}")

        with open(bad_file, "w", encoding="utf-8") as file:
            file.write("{ this is not json")
        _check("load rejected: file is not JSON",
               _raises(InvalidSaveDataError, lambda: BookingService.load(bad_file)) is not None)

        _check("load rejected: missing file raises SaveFileError",
               _raises(SaveFileError, lambda: BookingService.load(
                   os.path.join(folder, "missing.json"))) is not None)

        # Saving onto a folder fails at the final replace step
        target = os.path.join(folder, "a-folder")
        os.mkdir(target)
        _check("failed save raises SaveFileError",
               _raises(SaveFileError, lambda: loaded.save(target)) is not None)
        _check("failed save leaves no temporary file behind",
               sorted(os.listdir(folder)) == ["a-folder", "bad.json"])

    _check("failed loads and saves leave the current service unchanged",
           loaded.to_dict() == before)
    print()


def main():
    demo_xinyi()
    demo_kyrie()
    demo_yizhen()
    demo_anita()
    print("All demos: all checks passed.")


if __name__ == "__main__":
    main()

