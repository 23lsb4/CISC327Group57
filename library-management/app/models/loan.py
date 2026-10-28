from datetime import date, timedelta

LOAN_PERIOD_DAYS = 14


class Loan:
    def __init__(self, id, book_id, member_id, due_date, loan_date=None, return_date=None):
        self.id = id
        self.book_id = book_id
        self.member_id = member_id
        self.loan_date = loan_date or date.today()
        self.due_date = due_date
        self.return_date = return_date
        
    def is_overdue(self, today=None):
            today = today or date.today()
            overdue_status = (self.return_date is None) and (self.due_date < today)
            return overdue_status

    def days_overdue(self, today=None):
        today = today or date.today()
        if not self.is_overdue(today):
            return 0
        return (today - self.due_date).days

    def to_dict(self):
        return {
            "id": self.id,
            "book_id": self.book_id,
            "member_id": self.member_id,
            "loan_date": self.loan_date.isoformat(),
            "due_date": self.due_date.isoformat(),
            "return_date": self.return_date.isoformat() if self.return_date else None,
            "overdue": self.is_overdue(),
            "days_overdue": self.days_overdue(),
        }

    @staticmethod
    def default_due_date():
        return date.today() + timedelta(days=LOAN_PERIOD_DAYS)
