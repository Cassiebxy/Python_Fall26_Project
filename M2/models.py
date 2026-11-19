
"""Boarding areas, shared date validation, and business exceptions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, timedelta


# Team-wide business exceptions (Yizhen aggregate, Xinyi lists the errors first)

class BookingError(Exception):
    """Common base class for all PetStay business errors."""


# --- Part1: boarding areas and availability queries ---
# AI assistance: OpenAI Codex helped implement
class InvalidCapacityError(BookingError):
    """Capacity is not a non-negative integer (or is a bool)"""


class InvalidDateError(BookingError):
    """A date has the wrong type, or check-out is not strictly after check-in"""


class AreaFullError(BookingError):
    """No place left in this area for some night in the stay"""


class InsufficientOccupancyError(BookingError):
    """Releasing would take occupancy below zero on some night"""


class UnknownPetTypeError(BookingError):
    """No boarding area accepts this pet type"""


# --- Part 2: reservation creation ---
class InvalidReservationError(BookingError):
    """A required reservation field is missing or invalid."""


class DuplicateReservationError(BookingError):
    """The same pet already has an active reservation for overlapping nights."""


# --- Part 3: reservation cancellation ---

class ReservationNotFoundError(BookingError):
    """No reservation exists for the supplied booking ID."""


class ReservationAlreadyCancelledError(BookingError):
    """The reservation has already been cancelled."""


# --- Part 4 (Anita): saving and loading ---

class SaveFileError(BookingError):
    """The save file cannot be read or written (missing file, bad path, no permission)."""


class InvalidSaveDataError(BookingError):
    """The save file is not valid JSON, or its data breaks a business rule."""

# Date helper (provided by Xinyi; shared by query, reserve and release)

def _validate_date(value):
    """Dates must be datetime.date objects, bad types become the shared error"""
    if type(value) is not date:
        raise InvalidDateError(f"date must be a date object, got {value!r}")

def _parse_saved_date(value, field):
    """Turn a saved "YYYY-MM-DD" string back into a date (used only when loading).
    Only the exact form written by isoformat() is accepted, so "20261110" or
    "2026-11-10T12:00" cannot sneak in as a second key for the same night.
    """
    if not isinstance(value, str):
        raise InvalidSaveDataError(f"{field} must be a YYYY-MM-DD string, got {value!r}")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise InvalidSaveDataError(f"{field} is not a valid date: {value!r}")
    if parsed.isoformat() != value:
        raise InvalidSaveDataError(f"{field} must use the YYYY-MM-DD form, got {value!r}")
    return parsed


def stay_nights(check_in, check_out):
    """Return the list of nights from check_in up to the day before check_out
    Check-out day is not included:
    checking in on Nov 10 and out on Nov 12 overs only the nights of Nov 10 and Nov 11
    """
    _validate_date(check_in)
    _validate_date(check_out)
    if check_out <= check_in:
        raise InvalidDateError(
            f"check-out must be strictly after check-in: "
            f"{check_in.isoformat()} -> {check_out.isoformat()}"
        )
    nights = []
    night = check_in
    while night < check_out:
        nights.append(night)
        night = night + timedelta(days=1)
    return nights


# Boarding areas: abstract parent + cat / dog subclasses

class BoardingArea(ABC):
    """Shared boarding-area rules: capacity, per-night occupancy, queries.
    Subclasses only implement accepts(pet_type) and declare kind.
    """

    kind = None  # each subclass has its own: cat and dog

    def __init__(self, capacity):
        # Non-negative integer capacity, bool is a subclass of int
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
            raise InvalidCapacityError(f"capacity must be a non-negative int, got {capacity!r}")
        self.capacity = capacity

        # Create own dict for each instances
        self._occupancy = {}

    @abstractmethod
    def accepts(self, pet_type):
        """Return T/F for if the area takes cat or dog"""
        ...

    def remaining(self, night):
        """Places left on one night"""
        _validate_date(night)

        # A date missing from the dict counts as occupancy 0
        return self.capacity - self._occupancy.get(night.isoformat(), 0)

    def availability(self, check_in, check_out):
        """Per-night availability for a stay: a new {"YYYY-MM-DD": remaining} dict."""
        nights = stay_nights(check_in, check_out)

        result = {}
        for night in nights:
            result[night.isoformat()] = self.remaining(night)
        return result

    def reserve(self, check_in, check_out):
        """Add 1 to occupancy on every night of the stay
        Returns None on success, raises on failure
        All nights are checked first, then modified together
        if any night is short, raise before touching the data so no partial booking is left behind
        """
        nights = stay_nights(check_in, check_out)

        for night in nights:
            if self.remaining(night) < 1:
                raise AreaFullError(
                    f"{self.kind} area has no place left on {night.isoformat()}"
                )

        for night in nights:
            key = night.isoformat()
            self._occupancy[key] = self._occupancy.get(key, 0) + 1

    def release(self, check_in, check_out):
        """Subtract 1 from occupancy on every night of the stay
        Same shape as reserve
        first check every night has at least 1, then decrement each night

        Entries reduced to 0 keep their date key with value 0 (team's shared convention for saving, loading and comparing).
        """
        nights = stay_nights(check_in, check_out)
        for night in nights:
            if self._occupancy.get(night.isoformat(), 0) < 1:
                raise InsufficientOccupancyError(
                    f"{self.kind} area has nothing to release on {night.isoformat()}"
                )

        for night in nights:
            key = night.isoformat()
            self._occupancy[key] = self._occupancy[key] - 1

    def to_dict(self):
        """data for the save feature (Anita): kind, capacity, occupancy copy
        occupancy is copied with dict(...)
        the internal dict is never handed out
        """
        return {
            "kind": self.kind,
            "capacity": self.capacity,
            "occupancy": dict(self._occupancy),
        }

    
    @classmethod
    def from_dict(cls, data):
        """Rebuild an area from to_dict() output (Anita's load feature)
        The saved kind picks the subclass, the constructor re-checks capacity,
        and every saved night must hold 0..capacity before the copy is stored
        """
        if not isinstance(data, dict) or set(data) != {"kind", "capacity", "occupancy"}:
            raise InvalidSaveDataError(
                f"an area must have exactly kind, capacity and occupancy, got {data!r}"
            )

        area_class = AREA_CLASSES.get(data["kind"]) if isinstance(data["kind"], str) else None
        if area_class is None:
            raise InvalidSaveDataError(f"unknown area kind {data['kind']!r}")

        try:
            area = area_class(data["capacity"])
        except InvalidCapacityError as error:
            raise InvalidSaveDataError(f"{data['kind']} area: {error}") from error

        occupancy = data["occupancy"]
        if not isinstance(occupancy, dict):
            raise InvalidSaveDataError(f"{area.kind} area occupancy must be an object")
        for night, count in occupancy.items():
            _parse_saved_date(night, f"{area.kind} area night")
            if type(count) is not int or not 0 <= count <= area.capacity:
                raise InvalidSaveDataError(
                    f"{area.kind} area occupancy on {night} must be an int "
                    f"from 0 to {area.capacity}, got {count!r}"
                )

        # Everything checked: store a copy so the caller's dict stays separate
        area._occupancy = dict(occupancy)
        return area

    def __repr__(self):
        return f"{type(self).__name__}(capacity={self.capacity}, occupancy={self._occupancy})"


class CatArea(BoardingArea):
    """Cat area, cats only"""

    kind = "cat"

    def accepts(self, pet_type):
        return pet_type == "cat"


class DogArea(BoardingArea):
    """Dog area, dogs only"""

    kind = "dog"

    def accepts(self, pet_type):
        return pet_type == "dog"


# Saved "kind" to area class, used by BoardingArea.from_dict when loading
AREA_CLASSES = {CatArea.kind: CatArea, DogArea.kind: DogArea}


@dataclass
class Reservation:
    """Record one pet's stay using an exclusive check-out date."""

    booking_id: str
    owner_id: str
    pet_id: str
    pet_name: str
    pet_type: str
    check_in: date
    check_out: date
    status: str = "active"

    # --- Part 4: convert to and from JSON-ready dictionaries ---
    TEXT_FIELDS = ("booking_id", "owner_id", "pet_id", "pet_name", "pet_type")
    STATUSES = ("active", "cancelled")

    def to_dict(self):
        """JSON-ready copy of this record, dates written as "YYYY-MM-DD"."""
        return {
            "booking_id": self.booking_id,
            "owner_id": self.owner_id,
            "pet_id": self.pet_id,
            "pet_name": self.pet_name,
            "pet_type": self.pet_type,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild one record from to_dict() output, checking every field first."""
        expected = set(cls.TEXT_FIELDS) | {"check_in", "check_out", "status"}
        if not isinstance(data, dict) or set(data) != expected:
            raise InvalidSaveDataError(
                f"a reservation must have exactly the fields {sorted(expected)}, got {data!r}"
            )

        for field in cls.TEXT_FIELDS:
            if not isinstance(data[field], str) or not data[field].strip():
                raise InvalidSaveDataError(f"reservation {field} must be a non-empty string")

        check_in = _parse_saved_date(data["check_in"], "check_in")
        check_out = _parse_saved_date(data["check_out"], "check_out")
        if check_out <= check_in:
            raise InvalidSaveDataError(
                f"reservation {data['booking_id']!r}: check-out must be after check-in"
            )

        if data["status"] not in cls.STATUSES:
            raise InvalidSaveDataError(
                f"reservation {data['booking_id']!r}: unknown status {data['status']!r}"
            )

        return cls(
            booking_id=data["booking_id"],
            owner_id=data["owner_id"],
            pet_id=data["pet_id"],
            pet_name=data["pet_name"],
            pet_type=data["pet_type"],
            check_in=check_in,
            check_out=check_out,
            status=data["status"],
        )

