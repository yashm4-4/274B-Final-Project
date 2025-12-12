from banking_system import BankingSystem
import numpy as np

DAY_MS = 24 * 60 * 60 * 1000
# Added constant so the cashback delay (24 hours) is defined once and reused.
# This avoids hard-coding 86400000 in multiple places and reduces mistakes.


class BankingSystemImpl(BankingSystem):

    def __init__(self):
        self.accounts = {}
        self.pay_log = {}

    def cashback(self, timestamp: int, account_id: str) -> None:
        """
        Process cashback refunds due by `timestamp`.

        Key fix:
        - Refunds must be applied at the cashback timestamp (CB_timestamp),
          and the balance snapshot must be recorded at CB_timestamp, not
          at the current operation timestamp.
        """
        if account_id not in self.accounts:
            return None

        acc = self.accounts[account_id]

        for payment in acc["payments"]:
            pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]

            # Only process cashback if it is due AND not already processed.
            if (not CB_status) and CB_timestamp <= timestamp:
                acc["current_balance"] += CB_amount

                # IMPORTANT: record the snapshot at the cashback timestamp itself.
                # This is needed for correct historical get_balance queries (Level 4).
                acc["balance"][CB_timestamp] = acc["current_balance"]

                # Mark cashback as processed so it will not be applied again.
                self.pay_log[payment] = (pay_account_id, CB_timestamp, CB_amount, True)

        return None

    def create_account(self, timestamp: int, account_id: str) -> bool:
        """
        Create a new account if it doesn't already exist.
        """
        if account_id in self.accounts:
            return False
        else:
            self.accounts[account_id] = {}
            self.accounts[account_id]["account_created"] = timestamp

            # balance[timestamp] = balance after operations at that timestamp
            self.accounts[account_id]["balance"] = {}
            self.accounts[account_id]["balance"][timestamp] = 0

            self.accounts[account_id]["current_balance"] = 0
            self.accounts[account_id]["transfers"] = {}   # outgoing amounts (transfers + pay)
            self.accounts[account_id]["payments"] = []

            # Added to support Level 4 historical queries after merges:
            # store histories of deleted (merged) accounts under the surviving account.
            self.accounts[account_id]["merged_balance_histories"] = {}
            # Optional bookkeeping to keep merged payment lists by old account id.
            self.accounts[account_id]["merged_payments"] = {}

            return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
        """
        Deposit money into an account. Returns new balance or None if account doesn't exist.
        """
        if account_id in self.accounts:
            # Process any cashback due before doing the deposit.
            self.cashback(timestamp, account_id)

            self.accounts[account_id]["current_balance"] += amount
            self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"]
            return self.accounts[account_id]["current_balance"]
        else:
            return None

    def transfer(self, timestamp: int, source_account_id: str, target_account_id: str, amount: int) -> int | None:
        """
        Transfer money from source to target. Returns new source balance or None if invalid.
        """
        if source_account_id not in self.accounts or target_account_id not in self.accounts:
            return None
        if source_account_id == target_account_id:
            return None
        else:
            # Cashback must be processed first for both accounts at this timestamp.
            self.cashback(timestamp, source_account_id)
            self.cashback(timestamp, target_account_id)

            if self.accounts[source_account_id]["current_balance"] - amount >= 0:
                self.accounts[source_account_id]["current_balance"] -= amount
                self.accounts[target_account_id]["current_balance"] += amount

                self.accounts[source_account_id]["balance"][timestamp] = self.accounts[source_account_id]["current_balance"]
                self.accounts[target_account_id]["balance"][timestamp] = self.accounts[target_account_id]["current_balance"]

                # FIX: accumulate outgoing at the same timestamp instead of overwriting.
                # Multiple transactions can occur at the same timestamp.
                self.accounts[source_account_id]["transfers"][timestamp] = (
                    self.accounts[source_account_id]["transfers"].get(timestamp, 0) + amount
                )

                return self.accounts[source_account_id]["current_balance"]
            else:
                return None

    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        """
        Rank accounts by total outgoing transactions (transfers + pay).
        Cashback does not reduce outgoing totals.
        """
        transfer_sum_log = []

        for account_id in self.accounts:
            transfer_sum = 0
            for ts in self.accounts[account_id]["transfers"]:
                # ensure int (avoid numpy/float confusion)
                transfer_sum += int(self.accounts[account_id]["transfers"][ts])
            transfer_sum_log.append((account_id, transfer_sum))

        transfer_sum_log.sort(key=lambda x: (-x[1], x[0]))

        n_correct = min(n, len(transfer_sum_log))

        transfer_sum_log_str = []
        for i in range(n_correct):
            transfer_sum_str = transfer_sum_log[i][0] + "(" + str(transfer_sum_log[i][1]) + ")"
            transfer_sum_log_str.append(transfer_sum_str)

        return transfer_sum_log_str

    def pay(self, timestamp: int, account_id: str, amount: int) -> str | None:
        """
        Withdraw money with 2% cashback after 24 hours.
        Returns payment id or None if invalid.
        """
        if account_id not in self.accounts:
            return None

        # Cashback is processed before any other operations at this timestamp.
        self.cashback(timestamp, account_id)

        if amount > self.accounts[account_id]["current_balance"]:
            return None

        # Withdraw now.
        self.accounts[account_id]["current_balance"] -= amount
        self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"]

        # Outgoing includes pay (withdrawals).
        self.accounts[account_id]["transfers"][timestamp] = (
            self.accounts[account_id]["transfers"].get(timestamp, 0) + amount
        )

        pay_count = len(self.pay_log) + 1
        pay_str = "payment" + str(pay_count)

        CB_timestamp = timestamp + DAY_MS

        # FIX: use integer math so cashback is an int and rounded down.
        CB_amount = (amount * 2) // 100

        CB_status = False

        self.pay_log[pay_str] = (account_id, CB_timestamp, CB_amount, CB_status)
        self.accounts[account_id]["payments"].append(pay_str)

        return pay_str

    def get_payment_status(self, timestamp: int, account_id: str, payment: str) -> str | None:
        """
        Return IN_PROGRESS or CASHBACK_RECEIVED.
        """
        if account_id not in self.accounts:
            return None
        if payment not in self.pay_log:
            return None

        # Process cashback up to this timestamp so status is accurate.
        self.cashback(timestamp, account_id)

        pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]

        # Payment must belong to this account id (after merges, ownership may be updated).
        if pay_account_id != account_id:
            return None

        return "CASHBACK_RECEIVED" if CB_status else "IN_PROGRESS"

    def merge_accounts(self, timestamp: int, account_id_1: str, account_id_2: str) -> bool:
        """
        Merge account_id_2 into account_id_1.
        account_id_2 is removed, but its history is preserved for get_balance queries.
        """
        if account_id_1 == account_id_2:
            return False

        if account_id_1 not in self.accounts or account_id_2 not in self.accounts:
            return False

        # Process cashbacks up to merge time so pre-merge histories are consistent.
        self.cashback(timestamp, account_id_1)
        self.cashback(timestamp, account_id_2)

        acc1 = self.accounts[account_id_1]
        acc2 = self.accounts[account_id_2]

        # Store account2 balance history for historical queries on deleted id (Level 4).
        acc1["merged_balance_histories"][account_id_2] = (
            acc2["balance"].copy(),
            acc2["account_created"],
            timestamp
        )

        # If account2 had merged accounts before, inherit those histories too.
        if "merged_balance_histories" in acc2:
            for old_id, tup in acc2["merged_balance_histories"].items():
                acc1["merged_balance_histories"][old_id] = tup

        # Move payments so future cashback from account2 refunds into account1.
        acc1["payments"].extend(acc2["payments"])

        # Optional: store payment list by merged id (helps debugging / tracing).
        acc1["merged_payments"][account_id_2] = list(acc2["payments"])
        if "merged_payments" in acc2:
            for old_id, plist in acc2["merged_payments"].items():
                acc1["merged_payments"][old_id] = list(plist)

        # Update pay_log ownership ONLY for payments that truly belonged to account2.
        # Avoid string replace because it can accidentally change other ids.
        for pid in acc2["payments"]:
            pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[pid]
            if pay_account_id == account_id_2:
                self.pay_log[pid] = (account_id_1, CB_timestamp, CB_amount, CB_status)

        # Merge balances (add current balance of account2 into account1).
        acc1["current_balance"] += acc2["current_balance"]
        acc1["balance"][timestamp] = acc1["current_balance"]

        # Merge outgoing transfer histories by summing timestamps.
        for ts, amt in acc2["transfers"].items():
            acc1["transfers"][ts] = acc1["transfers"].get(ts, 0) + int(amt)

        # Remove account2 after merge (spec says it is removed).
        self.accounts.pop(account_id_2)

        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        """
        Return balance at time_at.
        - If account_id is deleted due to merge, it is valid only before its merge time.
        - Root account inherits merged accounts history (sum balances for time_at < merge time).
        """
        # If this account id was deleted, search in merged histories.
        if account_id not in self.accounts:
            for root_id, root_acc in self.accounts.items():
                hist = root_acc.get("merged_balance_histories", {})
                if account_id in hist:
                    bal_dict, created_at, merged_at = hist[account_id]

                    if time_at < created_at:
                        return None
                    if time_at >= merged_at:
                        # After merge time, the deleted id is not queryable.
                        return None

                    keys = [t for t in bal_dict if t <= time_at]
                    return bal_dict[max(keys)] if keys else 0

            return None

        acc = self.accounts[account_id]

        if acc["account_created"] > time_at:
            return None

        # Apply cashback first so balance reflects state after processing at that timestamp.
        self.cashback(time_at, account_id)

        keys = [key for key in acc["balance"] if key <= time_at]
        base = acc["balance"][max(keys)] if keys else 0

        # Root account inherits merged balances BEFORE each merge timestamp.
        total = base
        hist = acc.get("merged_balance_histories", {})
        for old_id, (bal_dict, created_at, merged_at) in hist.items():
            if time_at < created_at:
                continue
            if time_at >= merged_at:
                continue
            old_keys = [t for t in bal_dict if t <= time_at]
            total += bal_dict[max(old_keys)] if old_keys else 0

        return total
