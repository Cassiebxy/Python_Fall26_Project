# Python_Fall26_Project

# PetStay M1

## Project Overview

PetStay M1 is a Python reservation system for a single pet boarding facility. The facility has separate boarding areas and nightly capacity pools for cats and dogs.

The system supports:
1. Checking nightly availability
2. Creating reservations
3. Preventing overlapping active reservations for the same pet
4. Cancelling reservations and restoring capacity
5. Saving and loading system data through JSON

Each reservation represents one pet. A reservation stores a unique booking ID, owner ID, pet ID, pet name, pet type, check-in date, check-out date, and reservation status.

## Requirements

- Python 3
- No external packages are required

- ## How to Run

Open a terminal in the project directory and run:

```bash
python demo.py
```
## Business Rules

1. Cats and dogs use separate boarding areas and separate capacity pools.
2. Check-in is inclusive and check-out is exclusive.
3. For example, a reservation from November 10 to November 12 occupies the nights of November 10 and November 11.
4. The check-out date must be later than the check-in date.
5. Nightly occupancy must remain between zero and the area's capacity.
6. A multi-night operation must either succeed for every night or make no changes.
7. Each booking ID must be unique.
8. The same pet cannot have overlapping active reservations.
9. Adjacent reservations are allowed when the first check-out date equals the next check-in date.
10. Different pets may reserve the same dates when sufficient capacity is available.
11. Cancelled reservations remain in the system but do not occupy capacity.
12. Each reservation may release its capacity only once.
13. Invalid operations raise specific custom exceptions and must not change the system state.

## Date Convention

Dates are stored internally as `datetime.date` objects. Public service methods may accept either a `date` object or a string in `YYYY-MM-DD` format.

The stay interval follows the convention:

```text
[check-in, check-out)
```

## Concept Map

> Line numbers will be verified after all four members' code is integrated.

### Member 1 — Xinyi
| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Plain class, object attributes | `models.py:69-83` (`BoardingArea.__init__` at 76-83; per-instance `_occupancy` dict at 83) | Each area object keeps its own capacity and per-night count dict; creating the dict per instance keeps cat and dog areas independent |
| Encapsulation: check before modifying | `models.py:106-122` (`reserve`), `models.py:124-140` (`release`) | Two plain loops: the first checks every night, the second only then modifies; a failure raises before any data changes, so no partial booking survives; outside code never touches `_occupancy` |
| Abstract class and inheritance | `models.py:69` (`class BoardingArea(ABC)`), `models.py:85-88` (`@abstractmethod accepts`), subclasses at `models.py:157-163` (`CatArea`) and `models.py:166-172` (`DogArea`) | Cat and dog areas are both boarding areas, so shared capacity/occupancy rules live in the parent; subclasses only declare `kind` and their own acceptance rule; Python refuses to instantiate the ABC (demo check "abstract class cannot be instantiated") |
| Polymorphism | `services.py:53-55` (service picks an area via `area.accepts(pet_type)`), `demo.py:40-47` (same loop over `[CatArea(2), DogArea(2)]`) | Call sites use one shared interface instead of `isinstance` or subclass-name branches; the per-subclass rule `pet_type == "cat"` stays inside each subclass |
| Custom business exceptions | Hierarchy at `models.py:10-32` (base `BookingError`); raises at `models.py:44, 55, 79, 116, 134` and `services.py:20-24, 57`; caught in `demo.py:90, 112, 124, 129, 142, 150, 171, 189` | Named errors (invalid capacity / invalid date / area full / insufficient occupancy / unknown pet type) explain the failure reason and reject before data is modified; one shared module prevents same-name-different-class collisions between members; Yizheng (member 3) aggregates cancellation errors here |
| Plain data conversion, data copy | `models.py:142-151` (`to_dict` returns `kind`, `capacity`, and `dict(self._occupancy)` copy) | Anita gets JSON-serializable data without access to the internal dict; mutating the returned copy cannot corrupt the area (demo check "copy isolation") |
| Strict date validation (project addition) | `models.py:41-44` (`type(value) is not date`), `services.py:13` (`type(value) is date`) | `datetime` passes `isinstance(value, date)` and its `isoformat()` carries a time, which would create a second occupancy key for the same night and allow overbooking; strict type checks route timed input to `InvalidDateError` (demo checks at `demo.py:175-192`) |

### Member 2 — Kyrie
| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Data class | `models.py:184–195` | `Reservation` groups a stay's booking ID, pet and owner details, dates, and status. The data class generates the initializer and lets the demo compare snapshots by value. |
| Composition | `services.py:45–48` | `BookingService` holds the boarding areas and reservation records, so one service coordinates the nightly occupancy and booking record. |
| Polymorphism | `services.py:84–88`, `services.py:114` | The service finds the right area through `accepts()` and calls `reserve()` through the common boarding-area interface. |
| Encapsulated state changes | `services.py:90–116`, `models.py:115–131` | Creation checks overlapping stays before calling `reserve()`, which checks all nights before updating occupancy. The service stores the record only after `reserve()` succeeds. |
| Custom exceptions | `models.py:37–42`, `services.py:72–97` | Invalid reservation fields and overlapping stays raise distinct `BookingError` subclasses so callers can handle each reason. Date, pet type, and capacity errors use the existing team exceptions. |
| Runnable demo | `demo.py:198–271` | The demo covers A3, A4, A8, A11, A12, and A13 through `BookingService`. Rejected bookings compare both reservation records and occupancy against a snapshot. |

Run `python3 -B demo.py` from the project directory to run the demo.

- `create_reservation(owner_id, pet_id, pet_name, pet_type, check_in, check_out)` returns a booking ID string. Owner ID, pet ID, and pet name must be nonblank strings. Dates are stored as `datetime.date` objects and check-out is exclusive.
- `BookingService` stores `Reservation` objects in `_reservations`, keyed by booking ID. `reservations_snapshot()` returns copies for inspection or serialization. Use the stored record's `status` of `active` or `cancelled` when implementing cancellation and loading.
- When loading a valid saved state, restore the original IDs, including those of cancelled records, as the keys in the service's reservation collection. Creation checks new IDs against all existing keys, so loading does not require a separate ID counter. A10 and A14 can be run once loading and cancellation are integrated.

### Member 3 — Yizhen
| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Custom exceptions and inheritance | `models.py:47-52` | `ReservationNotFoundError` and `ReservationAlreadyCancelledError` inherit from the shared `BookingError`. They distinguish a missing booking ID from an attempt to cancel the same reservation twice. |
| Composition | `services.py:120-144` | `BookingService` coordinates the stored `Reservation` object and the matching boarding area, so cancellation updates both the reservation status and nightly occupancy. |
| Polymorphism | `services.py:135-141` | The cancellation method finds the correct area through the shared `accepts()` interface instead of checking whether the object is specifically a `CatArea` or `DogArea`. |
| Encapsulated state change | `services.py:120-144` | Callers cancel through `BookingService.cancel_reservation()` rather than changing the reservation status directly. This keeps the status and occupancy synchronized. |
| Validate before modifying | `services.py:123-144` | The method checks that the reservation exists and is still active before releasing occupancy. The area verifies all nights before modifying them, and the status changes only after release succeeds. |
| Runnable demo | `demo.py:275-348` | The demo covers successful cancellation, repeated-cancellation rejection, missing-ID rejection, restored availability, and rebooking after cancellation through scenarios A5, A6, A7, and A14. |

### Member 4 — Anita

To be added after the save and load feature is integrated.
