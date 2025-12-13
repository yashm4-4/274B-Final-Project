from banking_system import BankingSystem

DAY_MS = 24 * 60 * 60 * 1000


class BankingSystemImpl(BankingSystem):

    def __init__(self):
        self.accounts = {}
        self.pay_log = {}
        self._payment_counter = 0

    def cashback(self, timestamp: int, account_id: str):
        """
        Process cashback refunds due by `timestamp`.

        Refunds must be applied at the cashback timestamp (CB_timestamp),
        and the balance snapshot must be recorded at CB_timestamp.
        """
        if account_id not in self.accounts:
            return None

        acc = self.accounts[account_id]

        due = []
        for payment in acc["payments"]:
            pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]
            if (not CB_status) and CB_timestamp <= timestamp:
                due.append((CB_timestamp, payment, CB_amount, pay_account_id))

        due.sort()

        for CB_timestamp, payment, CB_amount, pay_account_id in due:
            acc["current_balance"] += int(CB_amount)
            acc["balance"][CB_timestamp] = acc["current_balance"]
            self.pay_log[payment] = (pay_account_id, CB_timestamp, int(CB_amount), True)

        return None

    def create_account(self, timestamp: int, account_id: str) -> bool:
        if account_id in self.accounts:
            return False

        self.accounts[account_id] = {
            "account_created": timestamp,
            "balance": {timestamp: 0},
            "current_balance": 0,
            "transfers": {},
            "payments": []
        }
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
        if account_id not in self.accounts:
            return None

        self.cashback(timestamp, account_id)

        acc = self.accounts[account_id]
        acc["current_balance"] += amount
        acc["balance"][timestamp] = acc["current_balance"]
        return acc["current_balance"]

    def transfer(self, timestamp: int, source_account_id: str, target_account_id: str, amount: int) -> int | None:
        if source_account_id not in self.accounts or target_account_id not in self.accounts:
            return None
        if source_account_id == target_account_id:
            return None

        self.cashback(timestamp, source_account_id)
        self.cashback(timestamp, target_account_id)

        src = self.accounts[source_account_id]
        dst = self.accounts[target_account_id]

        if src["current_balance"] - amount < 0:
            return None

        src["current_balance"] -= amount
        dst["current_balance"] += amount

        src["balance"][timestamp] = src["current_balance"]
        dst["balance"][timestamp] = dst["current_balance"]

        src["transfers"][timestamp] = src["transfers"].get(timestamp, 0) + amount

        return src["current_balance"]

    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        transfer_sum_log = []

        for account_id in self.accounts:
            total = 0
            for ts in self.accounts[account_id]["transfers"]:
                total += int(self.accounts[account_id]["transfers"][ts])
            transfer_sum_log.append((account_id, total))

        transfer_sum_log.sort(key=lambda x: (-x[1], x[0]))
        n_correct = min(n, len(transfer_sum_log))
        return [f"{acc}({total})" for acc, total in transfer_sum_log[:n_correct]]

    def pay(self, timestamp: int, account_id: str, amount: int) -> str | None:
        if account_id not in self.accounts:
            return None

        self.cashback(timestamp, account_id)

        acc = self.accounts[account_id]
        if amount > acc["current_balance"]:
            return None

        acc["current_balance"] -= amount
        acc["balance"][timestamp] = acc["current_balance"]

        acc["transfers"][timestamp] = acc["transfers"].get(timestamp, 0) + amount

        self._payment_counter += 1
        pay_str = "payment" + str(self._payment_counter)

        CB_timestamp = timestamp + DAY_MS
        CB_amount = (amount * 2) // 100
        CB_status = False

        self.pay_log[pay_str] = (account_id, CB_timestamp, CB_amount, CB_status)
        acc["payments"].append(pay_str)

        return pay_str

    def get_payment_status(self, timestamp: int, account_id: str, payment: str) -> str | None:
        if account_id not in self.accounts:
            return None
        if payment not in self.pay_log:
            return None

        self.cashback(timestamp, account_id)

        pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]
        if pay_account_id != account_id:
            return None

        return "CASHBACK_RECEIVED" if CB_status else "IN_PROGRESS"

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        if account_id not in self.accounts:
            return None

        acc = self.accounts[account_id]
        if acc["account_created"] > time_at:
            return None

        self.cashback(time_at, account_id)

        keys = [t for t in acc["balance"] if t <= time_at]
        return acc["balance"][max(keys)] if keys else 0


# Level 4:
