"""In-memory data store.

Each "table" is just a dict mapping id -> object, kept in memory for the
lifetime of the running app. Data is lost when the app restarts. This keeps
the project approachable before students cover databases later in the
program, while still separating storage from the route/model code.
"""

books = {}
members = {}
loans = {}
reservations = {}

_next_ids = {"book": 1, "member": 1, "loan": 1, "reservation": 1}


def next_id(kind):
    id_ = _next_ids[kind]
    _next_ids[kind] += 1
    return id_


def reset():
    """Clear all data. Handy for resetting state between tests."""
    books.clear()
    members.clear()
    loans.clear()
    reservations.clear()
    _next_ids.update(book=1, member=1, loan=1, reservation=1)
