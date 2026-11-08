
# Part 1 demo 

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
    UnknownPetTypeError,
)
from services import BookingService

# Fixed demo inputs: November 2026
CHECK_IN = date(2026, 11, 10)
CHECK_OUT = date(2026, 11, 12)   # check-out excluded


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


def main():
    demo_xinyi()
    demo_kyrie()
    # Yizheng: demo_yizheng() - cancel, double-cancel rejection, restored availability
    # Anita: demo_Anita() - save, load, and verification after restore
    print("Xinyi demo: all checks passed.")


if __name__ == "__main__":
    main()
