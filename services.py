
"""Availability queries through the common boarding-area interface."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

from models import (
    DuplicateReservationError,
    InvalidDateError,
    InvalidReservationError,
    Reservation,
    UnknownPetTypeError,
    stay_nights,
)


def _to_date(value):
    """Convert dates at the call entry
    1) date objects pass or 2) parse "YYYY-MM-DD" strings
    """
    if type(value) is date:
        return value

    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise InvalidDateError(f"invalid date string: {value!r}")

    raise InvalidDateError(
        "date must be a date object or a YYYY-MM-DD string, "
        f"got {value!r}"
    )


class BookingService:
    """Hold boarding-area objects and calls their methods

    Xinyi __init__ and availability
    Kyrie create_reservation 
    Yizheng cancel_reservation
    """

    def __init__(self, areas):
        # the service holds the area objects eg [CatArea(2), DogArea(2)]
        self._areas = list(areas)
        self._reservations = {}

    def add_area(self, area):
        """Add a boarding area"""
        self._areas.append(area)

    def availability(self, pet_type, check_in, check_out):
        """pet type plus check-in/check-out dates
        1) return the places left on each night
        2) Query reserves nothing. 
        3) When no area accepts the pet type, raise error
        """
        check_in = _to_date(check_in)
        check_out = _to_date(check_out)

        for area in self._areas:
            if area.accepts(pet_type):
                return area.availability(check_in, check_out)

        raise UnknownPetTypeError(f"no boarding area accepts pet type {pet_type!r}")

    # AI assistance: OpenAI Codex helped implement and verify the member 2 work.
    def create_reservation(self, owner_id, pet_id, pet_name, pet_type, check_in, check_out):
        """Book one pet for the entire stay and return its booking ID."""
        for field, value in (
            ("owner_id", owner_id),
            ("pet_id", pet_id),
            ("pet_name", pet_name),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InvalidReservationError(f"{field} must be a non-empty string")

        check_in = _to_date(check_in)
        check_out = _to_date(check_out)
        stay_nights(check_in, check_out)

        for area in self._areas:
            if area.accepts(pet_type):
                break
        else:
            raise UnknownPetTypeError(f"no boarding area accepts pet type {pet_type!r}")

        for existing in self._reservations.values():
            if existing.pet_id != pet_id or existing.status != "active":
                continue
            if check_in < existing.check_out and existing.check_in < check_out:
                raise DuplicateReservationError(
                    f"pet {pet_id!r} already has an overlapping reservation "
                    f"({existing.booking_id})"
                )

        booking_id = str(uuid4())
        while booking_id in self._reservations:
            booking_id = str(uuid4())

        reservation = Reservation(
            booking_id=booking_id,
            owner_id=owner_id,
            pet_id=pet_id,
            pet_name=pet_name,
            pet_type=pet_type,
            check_in=check_in,
            check_out=check_out,
        )

        # If any night is full, reserve raises before changing occupancy.
        area.reserve(check_in, check_out)
        self._reservations[booking_id] = reservation
        return booking_id

    def reservations_snapshot(self):
        """Return copies of the reservation records keyed by booking ID."""
        return {
            booking_id: replace(reservation)
            for booking_id, reservation in self._reservations.items()
        }
