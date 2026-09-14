from datetime import date


class Transaction:
    def __init__(self, id, product_id, type, quantity, supplier_id=None, transaction_date=None):
        self.id = id
        self.product_id = product_id
        self.supplier_id = supplier_id
        self.type = type  # "IN" or "OUT"
        self.quantity = quantity
        self.transaction_date = transaction_date or date.today()

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "supplier_id": self.supplier_id,
            "type": self.type,
            "quantity": self.quantity,
            "transaction_date": self.transaction_date.isoformat(),
        }
