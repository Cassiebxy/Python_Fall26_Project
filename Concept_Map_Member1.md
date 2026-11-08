# PetStay M1 — Concept Map, Xinyi (Member 1)

Line numbers refer to the current code (2026-11-07): `models.py`, `services.py`, `demo.py`.
Team: member 1 — Xinyi; member 2 — Kyrie; member 3 — Yizheng; member 4 — Anita.

Handoff note: Yizheng (member 3) merges this table into README.md.

| Course concept | Code location (file:line) | Why it is used this way | Classroom reference |
|---|---|---|---|
| Plain class, object attributes | `models.py:69-83` (`BoardingArea.__init__` at 76-83; per-instance `_occupancy` dict at 83) | Each area object keeps its own capacity and per-night count dict; creating the dict per instance keeps cat and dog areas independent | Lab 2B `ExampleCourse` (cell 6): `__init__` + `self.capacity` |
| Encapsulation: check before modifying | `models.py:106-122` (`reserve`), `models.py:124-140` (`release`) | Two plain loops: the first checks every night, the second only then modifies; a failure raises before any data changes, so no partial booking survives; outside code never touches `_occupancy` | Lab 3 `ExampleBikeShare.take_bike` (cell 20) "change only after every check"; Lecture 4 "Keep the data behind the methods" |
| Abstract class and inheritance | `models.py:69` (`class BoardingArea(ABC)`), `models.py:85-88` (`@abstractmethod accepts`), subclasses at `models.py:157-163` (`CatArea`) and `models.py:166-172` (`DogArea`) | Cat and dog areas are both boarding areas, so shared capacity/occupancy rules live in the parent; subclasses only declare `kind` and their own acceptance rule; Python refuses to instantiate the ABC (demo check "abstract class cannot be instantiated") | Lab 3 `ExampleNotifier` (cell 10); Lecture 5 Bike / PedalBike / EBike |
| Polymorphism | `services.py:53-55` (service picks an area via `area.accepts(pet_type)`), `demo.py:40-47` (same loop over `[CatArea(2), DogArea(2)]`) | Call sites use one shared interface instead of `isinstance` or subclass-name branches; the per-subclass rule `pet_type == "cat"` stays inside each subclass | Lecture 5 Bike example; requirements A1 |
| Custom business exceptions | Hierarchy at `models.py:10-32` (base `BookingError`); raises at `models.py:44, 55, 79, 116, 134` and `services.py:20-24, 57`; caught in `demo.py:90, 112, 124, 129, 142, 150, 171, 189` | Named errors (invalid capacity / invalid date / area full / insufficient occupancy / unknown pet type) explain the failure reason and reject before data is modified; one shared module prevents same-name-different-class collisions between members; Yizheng (member 3) aggregates cancellation errors here | Lab 3 `ExampleBikeShareError` hierarchy (cell 20); Lecture 5 p.20 |
| Plain data conversion, data copy | `models.py:142-151` (`to_dict` returns `kind`, `capacity`, and `dict(self._occupancy)` copy) | Anita (member 4) gets JSON-serializable data without access to the internal dict; mutating the returned copy cannot corrupt the area (demo check "copy isolation") | Lecture 4 `to_dict` (p.19); Lab 2B Task 4 (cells 24-25) |
| Strict date validation (project addition) | `models.py:41-44` (`type(value) is not date`), `services.py:13` (`type(value) is date`) | `datetime` passes `isinstance(value, date)` and its `isoformat()` carries a time, which would create a second occupancy key for the same night and allow overbooking; strict type checks route timed input to `InvalidDateError` (demo checks at `demo.py:175-192`) | Not from the classroom examples — added for the project's "occupancy ≤ capacity" rule |

## Notes for Yizheng (member 3) (README aggregation)

- Date convention: check-in included, check-out excluded; occupancy keys are
  `YYYY-MM-DD` strings; a missing date means occupancy 0; zero counts keep
  their key with value 0.
- `BookingService(areas)` takes a list such as `[CatArea(2), DogArea(2)]`;
  exceptions are imported from `models.py`.
- Python 3.13.9, no third-party dependencies; run with `python3 demo.py`.
- AI usage: Xinyi’s files were drafted with Claude Code assistance and
  reviewed and corrected with OpenAI Codex assistance.
