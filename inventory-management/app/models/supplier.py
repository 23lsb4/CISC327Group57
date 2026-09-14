class Supplier:
    def __init__(self, id, name, contact_email):
        self.id = id
        self.name = name
        self.contact_email = contact_email

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "contact_email": self.contact_email,
        }
