# PetStay M1 — Concept Map, Yizhen

Member 3 implemented reservation cancellation and the related demo scenarios.
The line numbers below refer to the current code and should be checked again after final integration.

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Custom exceptions and inheritance | `models.py:47-52` | `ReservationNotFoundError` and `ReservationAlreadyCancelledError` inherit from the shared `BookingError`. They distinguish a missing booking ID from an attempt to cancel the same reservation twice. |
| Composition | `services.py:120-144` | `BookingService` coordinates the stored `Reservation` object and the matching boarding area, so cancellation updates both the reservation status and nightly occupancy. |
| Polymorphism | `services.py:135-141` | The cancellation method finds the correct area through the shared `accepts()` interface instead of checking whether the object is specifically a `CatArea` or `DogArea`. |
| Encapsulated state change | `services.py:120-144` | Callers cancel through `BookingService.cancel_reservation()` rather than changing the reservation status directly. This keeps the status and occupancy synchronized. |
| Validate before modifying | `services.py:123-144` | The method checks that the reservation exists and is still active before releasing occupancy. The area verifies all nights before modifying them, and the status changes only after release succeeds. |
| Runnable demo | `demo.py:275-348` | The demo covers successful cancellation, repeated-cancellation rejection, missing-ID rejection, restored availability, and rebooking after cancellation through scenarios A5, A6, A7, and A14. |