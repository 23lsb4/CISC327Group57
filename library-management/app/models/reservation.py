from datetime import date


class Reservation:
    def __init__(self, id, book_id, member_id, reservation_date=None, fulfilled=False):
        self.id = id
        self.book_id = book_id
        self.member_id = member_id
        self.reservation_date = reservation_date or date.today()
        self.fulfilled = fulfilled

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "member_id": self.member_id,
            "reservation_date": self.reservation_date.isoformat(),
            "fulfilled": self.fulfilled,
        }
