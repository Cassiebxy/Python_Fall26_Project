# PetStay M1 — Concept Map, Xinyi

Line numbers refer to the current code: `models.py`, `services.py`, `demo.py`.

Team:

member 1 — Xinyi

member 2 — Kyrie

member 3 — Yizhen

member 4 — Anita.

Handoff note: Yizhen merges this table into README.md.

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Plain class, object attributes | `models.py:117-124` (`BoardingArea.__init__`) | Each area object keeps its own capacity and per-night count dict; creating the dict per instance keeps cat and dog areas independent |
| Encapsulation: check before modifying | `models.py:147-163` (`BoardingArea.reserve`), `models.py:165-181` (`BoardingArea.release`) | Two plain loops: the first checks every night, the second only then modifies; a failure raises before any data changes, so no partial booking survives; outside code never touches `_occupancy` |
| Abstract class and inheritance | `models.py:126-129` (`BoardingArea.accepts`), `models.py:234-240` (`CatArea`), `models.py:243-249` (`DogArea`) | Cat and dog areas are both boarding areas, so shared capacity/occupancy rules live in the parent; subclasses only declare `kind` and their own acceptance rule; Python refuses to instantiate the ABC (demo check "abstract class cannot be instantiated") |
| Polymorphism | `services.py:62-75` (`BookingService.availability`), `demo.py:42-207` (`demo_xinyi`) | Call sites use one shared interface instead of `isinstance` or subclass-name branches; the per-subclass rule `pet_type == "cat"` stays inside each subclass |
| Custom business exceptions | `models.py:11-12` (`BookingError`), `models.py:17-18` (`InvalidCapacityError`), `models.py:21-22` (`InvalidDateError`), `models.py:25-26` (`AreaFullError`), `models.py:29-30` (`InsufficientOccupancyError`), `models.py:33-34` (`UnknownPetTypeError`) | Named errors (invalid capacity / invalid date / area full / insufficient occupancy / unknown pet type) explain the failure reason and reject before data is modified; one shared module prevents same-name-different-class collisions between members; Yizhen (member 3) aggregates cancellation errors here |
| Plain data conversion, data copy | `models.py:183-192` (`BoardingArea.to_dict`) | Anita gets JSON-serializable data without access to the internal dict; mutating the returned copy cannot corrupt the area (demo check "copy isolation") |
| Strict date validation (project addition) | `models.py:67-70` (`_validate_date`), `services.py:24-40` (`_to_date`) | `datetime` passes `isinstance(value, date)` and its `isoformat()` carries a time, which would create a second occupancy key for the same night and allow overbooking; strict type checks route timed input to `InvalidDateError` (demo checks at `demo.py:175-192`) |

