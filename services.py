
"""Availability queries through the common boarding-area interface."""

from datetime import date

from models import InvalidDateError, UnknownPetTypeError


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
