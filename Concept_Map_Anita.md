# PetStay M1 — Concept Map, Anita

Member 4 implemented JSON saving and loading, the load-time consistency checks, and the A9, A10 and A15 demo scenarios.
Line numbers refer to the integrated code.

| Course concept | Code location (file:line) | Why it is used this way |
|---|---|---|
| Custom exceptions and inheritance | `models.py:58-59` (`SaveFileError`), `models.py:62-63` (`InvalidSaveDataError`), `services.py:170-187` (`BookingService.save`), `services.py:189-201` (`BookingService.load`) | Both inherit from the shared `BookingError`. `SaveFileError` means the file itself cannot be read or written; `InvalidSaveDataError` means the content is not JSON or breaks a business rule. The demo catches each one by name. |
| Exception handling and chaining | `services.py:170-187` (`BookingService.save`), `services.py:189-201` (`BookingService.load`), `models.py:195-228` (`BoardingArea.from_dict`) | Low-level `OSError` and `ValueError` are caught and re-raised as team exceptions with `raise ... from error`, so callers handle one business error while the original cause stays visible. A bad capacity on load reuses Xinyi's constructor check and is turned into `InvalidSaveDataError`. |
| File I/O with context managers | `services.py:170-187` (`BookingService.save`), `services.py:189-201` (`BookingService.load`) | `with open(...)` closes the file even when writing or parsing fails. Saving writes to a temporary file and only then calls `os.replace`, so a failed save never leaves a half-written file where the previous save was. |
| Data conversion for JSON | `models.py:273-284` (`Reservation.to_dict`), `models.py:72-85` (`_parse_saved_date`), `services.py:161-168` (`BookingService.to_dict`) | JSON has no date type, so dates are written as `YYYY-MM-DD` text and parsed back into `date` objects. Only the exact `isoformat()` form is accepted, so a string such as `20261110` cannot create a second key for the same night. |
| Class methods as restore constructors | `models.py:195-228` (`BoardingArea.from_dict`), `models.py:286-320` (`Reservation.from_dict`), `services.py:189-201` (`BookingService.load`), `services.py:203-273` (`BookingService.from_dict`) | Each class rebuilds its own objects, so `_occupancy` and `_reservations` are only set inside their own class and outside code never edits internal collections. `load` returns a new service, so an existing service is never changed by loading. |
| Inheritance and polymorphism on restore | `models.py:195-228` (`BoardingArea.from_dict`), `services.py:203-273` (`BookingService.from_dict`) | The saved `kind` selects `CatArea` or `DogArea`. Each reservation is matched to its area through `accepts()`, the same way `create_reservation` picks an area, instead of comparing class names. |
| Validate before modifying (load consistency) | `services.py:203-273` (`BookingService.from_dict`) | Areas, record fields, unique booking IDs, accepted pet types, same-pet overlap and nightly occupancy are all checked on local variables first. The occupancy consistency check in `BookingService.from_dict` requires every night's saved count to equal the number of active reservations covering it (scenario A15). |
| Data copy | `models.py:195-228` (`BoardingArea.from_dict`), `services.py:161-168` (`BookingService.to_dict`) | The loaded occupancy is stored as a copy, so changing the input dict afterwards cannot change the restored area. Saving uses the existing `to_dict()` copies and never reads the internal dicts directly. |
| Runnable demo | `demo.py:370-506` (`demo_anita`) | The demo saves `petstay_data.json`, loads it, compares records, occupancy and availability, then keeps booking and cancelling on the loaded service. Thirteen tampered files plus a non-JSON file, a missing file and a failed save are each rejected with a specific exception and leave the current service unchanged. |

## Save file format (agreed with members 1–3)

```json
{
  "areas": [
    {"kind": "cat", "capacity": 2, "occupancy": {"2026-11-10": 1, "2026-11-11": 1}},
    {"kind": "dog", "capacity": 1, "occupancy": {"2026-11-10": 1, "2026-11-11": 1}}
  ],
  "reservations": [
    {"booking_id": "…", "owner_id": "owner-1", "pet_id": "pet-1", "pet_name": "Milo",
     "pet_type": "dog", "check_in": "2026-11-10", "check_out": "2026-11-12", "status": "active"}
  ]
}
```

- `areas` uses Xinyi's `BoardingArea.to_dict()` output unchanged. Nights released back to 0 may stay as keys with value 0.
- `reservations` keeps the original booking IDs, pet IDs and `active` / `cancelled` status, in creation order.

## Interface

- `service.save(path)` writes the whole state. Raises `SaveFileError` if the file cannot be written.
- `BookingService.load(path)` returns a new, checked `BookingService`. Raises `SaveFileError` if the file cannot be read, or `InvalidSaveDataError` if the content is invalid.
- `BookingService.from_dict(data)` / `service.to_dict()` do the same without a file.

