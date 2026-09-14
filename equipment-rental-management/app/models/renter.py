from datetime import date


class Renter:
    def __init__(self, id, name, email, membership_date=None):
        self.id = id
        self.name = name
        self.email = email
        self.membership_date = membership_date or date.today()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "membership_date": self.membership_date.isoformat(),
        }
