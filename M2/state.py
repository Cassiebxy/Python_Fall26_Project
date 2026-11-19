"""Server-owned PetStay state: load once at startup, save after every write."""

import os

from models import CatArea, DogArea
from services import BookingService

# Anita: server state, loading and saving, restart checks 

# JSON save file, next to this script (created on the first start)
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "petstay_data.json")

# Capacities used only when no save file exists yet
CAT_CAPACITY = 2
DOG_CAPACITY = 1


class ServerState:
    """The one BookingService the server owns, kept in step with its save file.

    Queries read `service`. Bookings and cancellations must go through book()
    and cancel(): the change is made on a copy, the copy is saved, and only
    then does the copy become the current service. If the change is rejected
    or the save fails, the current service and the file both stay as they
    were, so a reply never confirms a change that is not on disk.
    """

    def __init__(self, service, path):
        self._service = service
        self.path = path

    @property
    def service(self):
        """Current BookingService, for queries such as availability().
        Read it again for each request: book() and cancel() replace it.
        """
        return self._service

    def book(self, owner_id, pet_id, pet_name, pet_type, check_in, check_out):
        """Create and save one reservation; return its booking ID.
        Raises the M1 booking errors when the request is rejected, or
        SaveFileError when the new state could not be written.
        """
        draft = self._draft()
        booking_id = draft.create_reservation(
            owner_id, pet_id, pet_name, pet_type, check_in, check_out
        )
        self._commit(draft)
        return booking_id

    def cancel(self, booking_id):
        """Cancel and save one reservation.
        Raises the M1 cancellation errors, or SaveFileError when saving fails.
        """
        draft = self._draft()
        draft.cancel_reservation(booking_id)
        self._commit(draft)

    def _draft(self):
        """Independent copy of the current service to try a change on."""
        return BookingService.from_dict(self._service.to_dict())

    def _commit(self, draft):
        """Save the changed copy, then make it current (only if the save worked)."""
        draft.save(self.path)   # SaveFileError leaves file and memory unchanged
        self._service = draft


def load_state(path=DATA_FILE):
    """Start the server's state from its save file.

    An existing file is loaded with all M1 checks; a missing file starts an
    empty system with the default capacities and saves it right away, so the
    next restart reads the same capacities. A file that exists but cannot be
    read or is invalid raises SaveFileError or InvalidSaveDataError instead of
    being replaced, so bookings on disk are never lost by a restart.
    """
    if os.path.exists(path):
        service = BookingService.load(path)
    else:
        service = BookingService([CatArea(CAT_CAPACITY), DogArea(DOG_CAPACITY)])
        service.save(path)
    return ServerState(service, path)
