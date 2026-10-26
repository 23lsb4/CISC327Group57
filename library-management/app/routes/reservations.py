from datetime import date

from flask import Blueprint, jsonify, request

from app import store
from app.models.reservation import Reservation

reservations_bp = Blueprint("reservations", __name__, url_prefix="/reservations")


def active_holds(book_id):
    """Unfulfilled holds on a book, oldest first (the waiting list)."""
    holds = [r for r in store.reservations.values()
             if r.book_id == book_id and not r.fulfilled]
    return sorted(holds, key=lambda r: r.id)


@reservations_bp.route("", methods=["GET"])
def list_reservations():
    results = list(store.reservations.values())
    book_id = request.args.get("book_id", type=int)
    member_id = request.args.get("member_id", type=int)
    if book_id is not None:
        results = [r for r in results if r.book_id == book_id]
    if member_id is not None:
        results = [r for r in results if r.member_id == member_id]
    return jsonify([r.to_dict() for r in results])


@reservations_bp.route("", methods=["POST"])
def create_reservation():
    data = request.get_json()
    book = store.books.get(data["book_id"])
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    member = store.members.get(data["member_id"])
    if member is None:
        return jsonify({"error": "Member not found"}), 404
    if any(r.member_id == data["member_id"] for r in active_holds(data["book_id"])):
        return jsonify({"error": "Member already has a hold on this book"}), 409

    reservation_id = store.next_id("reservation")
    reservation = Reservation(
        id=reservation_id,
        book_id=data["book_id"],
        member_id=data["member_id"],
        reservation_date=date.today(),
        fulfilled=False,
    )
    store.reservations[reservation_id] = reservation
    return jsonify(reservation.to_dict()), 201

    # NOTE: checkout_book() in loans.py does NOT check store.reservations before
    # allowing a checkout. This means any member can check out a book that another
    # member has reserved — the reservation is silently bypassed.
    # This is an intentional bug for students to discover through testing.


@reservations_bp.route("/<int:reservation_id>/position", methods=["GET"])
def get_position(reservation_id):
    reservation = store.reservations.get(reservation_id)
    if reservation is None:
        return jsonify({"error": "Reservation not found"}), 404
    if reservation.fulfilled:
        return jsonify({"error": "Hold already fulfilled"}), 400

    queue = active_holds(reservation.book_id)
    return jsonify({
        "reservation_id": reservation.id,
        "book_id": reservation.book_id,
        "member_id": reservation.member_id,
        "position": queue.index(reservation) + 1,
        "queue_length": len(queue),
    })
