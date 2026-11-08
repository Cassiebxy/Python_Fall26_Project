
"""Boarding areas, shared date validation, and business exceptions."""

from abc import ABC, abstractmethod
from datetime import date, timedelta


# Team-wide business exceptions (Yizheng aggregate, Xinyi lists the errors first)

class BookingError(Exception):
    """Common base class for all PetStay business errors."""


# --- Part1: boarding areas and availability queries ---
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


# --- Kyrie adds its exceptions here (e.g. DuplicateReservationError) ---
# --- Yizheng adds cancellation errors here (missing ID, double cancel) ---


# Date helper (provided by Xinyi; shared by query, reserve and release)

def _validate_date(value):
    """Dates must be datetime.date objects, bad types become the shared error"""
    if type(value) is not date:
        raise InvalidDateError(f"date must be a date object, got {value!r}")


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
