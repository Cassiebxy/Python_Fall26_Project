"""Availability queries through the common boarding-area interface."""

import json
import os
from dataclasses import replace
from datetime import date
from uuid import uuid4

from models import (
    BoardingArea,
    DuplicateReservationError,
    InvalidDateError,
    InvalidReservationError,
    InvalidSaveDataError,
    Reservation,
    ReservationAlreadyCancelledError,
    ReservationNotFoundError,
    SaveFileError,
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
    Yizhen cancel_reservation
    Anita to_dict, save, from_dict, load
    """

    def __init__(self, areas):
        # the service holds the area objects eg [CatArea(2), DogArea(2)]
        self._areas = list(areas)
        self._reservations = {}

    def add_area(self, area):
        """Add a boarding area"""
        self._areas.append(area)

    # AI assistance: OpenAI Codex helped implement
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

    def cancel_reservation(self, booking_id):
        """Cancel one active reservation and release all of its nights."""

        reservation = self._reservations.get(booking_id)

        if reservation is None:
            raise ReservationNotFoundError(
                f"reservation {booking_id!r} was not found"
            )

        if reservation.status == "cancelled":
            raise ReservationAlreadyCancelledError(
                f"reservation {booking_id!r} has already been cancelled"
            )

        for area in self._areas:
            if area.accepts(reservation.pet_type):
                break
        else:
            raise UnknownPetTypeError(
                f"no boarding area accepts pet type {reservation.pet_type!r}"
            )

        area.release(reservation.check_in, reservation.check_out)
        reservation.status = "cancelled"        

    def reservations_snapshot(self):
        """Return copies of the reservation records keyed by booking ID."""
        return {
            booking_id: replace(reservation)
            for booking_id, reservation in self._reservations.items()
        }

    # --- Part 4(Anita): saving and loading ---

    def to_dict(self):
        """The whole system state as plain JSON-ready data."""
        return {
            "areas": [area.to_dict() for area in self._areas],
            "reservations": [
                reservation.to_dict() for reservation in self._reservations.values()
            ],
        }

    def save(self, path):
        """Write the system state to a JSON file.
        The data goes to a temporary file first and replaces the target only
        after the write finished, so a failed save never leaves a half-written
        file in place of the previous save.
        """
        data = self.to_dict()
        temp_path = f"{path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
            os.replace(temp_path, path)
        except OSError as error:
            try:
                os.remove(temp_path)
            except OSError:
                pass  # the temporary file was never created
            raise SaveFileError(f"could not save to {str(path)!r}: {error}") from error

    @classmethod
    def load(cls, path):
        """Read a JSON save file and return a new, fully checked BookingService.
        Any service object that already exists is never touched by loading.
        """
        try:
            with open(path, encoding="utf-8") as file:
                data = json.load(file)
        except ValueError as error:  # not JSON, or not UTF-8 text
            raise InvalidSaveDataError(f"{str(path)!r} is not a valid JSON file: {error}") from error
        except OSError as error:
            raise SaveFileError(f"could not read {str(path)!r}: {error}") from error
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        """Rebuild a service from to_dict() output.
        Every object is rebuilt and every business rule is checked on local
        variables first; the service object is only created once all checks
        pass, so invalid data never becomes a usable service.
        """
        if not isinstance(data, dict) or set(data) != {"areas", "reservations"}:
            raise InvalidSaveDataError("save data must have exactly 'areas' and 'reservations'")
        if not isinstance(data["areas"], list) or not isinstance(data["reservations"], list):
            raise InvalidSaveDataError("'areas' and 'reservations' must both be lists")

        # 1) Areas: the saved kind restores CatArea or DogArea (capacity and
        #    0 <= occupancy <= capacity are checked inside BoardingArea.from_dict)
        areas = [BoardingArea.from_dict(area_data) for area_data in data["areas"]]

        # 2) Reservations: valid fields, unique booking IDs, and an area that
        #    accepts the pet type (picked the same way create_reservation does)
        reservations = {}
        area_of = {}
        for record in data["reservations"]:
            reservation = Reservation.from_dict(record)
            if reservation.booking_id in reservations:
                raise InvalidSaveDataError(f"duplicate booking ID {reservation.booking_id!r}")
            for area in areas:
                if area.accepts(reservation.pet_type):
                    break
            else:
                raise InvalidSaveDataError(
                    f"reservation {reservation.booking_id!r}: "
                    f"no area accepts pet type {reservation.pet_type!r}"
                )
            reservations[reservation.booking_id] = reservation
            area_of[reservation.booking_id] = area

        # 3) The same pet cannot have overlapping active reservations
        active = [r for r in reservations.values() if r.status == "active"]
        for index, first in enumerate(active):
            for second in active[index + 1:]:
                if (first.pet_id == second.pet_id
                        and first.check_in < second.check_out
                        and second.check_in < first.check_out):
                    raise InvalidSaveDataError(
                        f"pet {first.pet_id!r} has overlapping active reservations "
                        f"{first.booking_id!r} and {second.booking_id!r}"
                    )

        # 4) Each night's saved occupancy must equal the number of active
        #    reservations covering it (cancelled ones occupy nothing)
        for area in areas:
            expected = {}
            for reservation in active:
                if area_of[reservation.booking_id] is not area:
                    continue
                for night in stay_nights(reservation.check_in, reservation.check_out):
                    key = night.isoformat()
                    expected[key] = expected.get(key, 0) + 1

            saved = area.to_dict()["occupancy"]
            for night in sorted(set(saved) | set(expected)):
                if saved.get(night, 0) != expected.get(night, 0):
                    raise InvalidSaveDataError(
                        f"{area.kind} area on {night}: saved occupancy "
                        f"{saved.get(night, 0)} but {expected.get(night, 0)} "
                        f"active reservation(s) cover that night"
                    )

        # 5) All checks passed: only now build the usable service
        service = cls(areas)
        service._reservations = reservations
        return service

