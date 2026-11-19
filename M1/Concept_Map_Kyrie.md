# PetStay M1 — Concept Map, Kyrie

Member 2 implemented the reservation record and creation flow. Yizhen can merge this table into the README.

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Data class | `models.py:256-320` (`Reservation`) | `Reservation` groups a stay's booking ID, pet and owner details, dates, and status. The data class generates the initializer and lets the demo compare snapshots by value. |
| Composition | `services.py:52-55` (`BookingService.__init__`) | `BookingService` holds the boarding areas and reservation records, so one service coordinates the nightly occupancy and booking record. |
| Polymorphism | `services.py:78-124` (`BookingService.create_reservation`) | The service finds the right area through `accepts()` and calls `reserve()` through the common boarding-area interface. |
| Encapsulated state changes | `services.py:78-124` (`BookingService.create_reservation`), `models.py:147-163` (`BoardingArea.reserve`) | Creation checks overlapping stays before calling `reserve()`, which checks all nights before updating occupancy. The service stores the record only after `reserve()` succeeds. |
| Custom exceptions | `models.py:38-39` (`InvalidReservationError`), `models.py:42-43` (`DuplicateReservationError`), `services.py:78-124` (`BookingService.create_reservation`) | Invalid reservation fields and overlapping stays raise distinct `BookingError` subclasses so callers can handle each reason. Date, pet type, and capacity errors use the existing team exceptions. |
| Runnable demo | `demo.py:205-278` (`demo_kyrie`) | The demo covers A3, A4, A8, A11, A12, and A13 through `BookingService`. Rejected bookings compare both reservation records and occupancy against a snapshot. |

Run `python3 -B demo.py` from the project directory to run the demo.

- `create_reservation(owner_id, pet_id, pet_name, pet_type, check_in, check_out)` returns a booking ID string. Owner ID, pet ID, and pet name must be nonblank strings. Dates are stored as `datetime.date` objects and check-out is exclusive.
- `BookingService` stores `Reservation` objects in `_reservations`, keyed by booking ID. `reservations_snapshot()` returns copies for inspection or serialization. Use the stored record's `status` of `active` or `cancelled` when implementing cancellation and loading.
- When loading a valid saved state, restore the original IDs, including those of cancelled records, as the keys in the service's reservation collection. Creation checks new IDs against all existing keys, so loading does not require a separate ID counter. A10 and A14 can be run once loading and cancellation are integrated.

