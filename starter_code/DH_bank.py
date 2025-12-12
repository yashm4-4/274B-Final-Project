from banking_system import BankingSystem
import numpy as np

DAY_MS = 24 * 60 * 60 * 1000
# Added constant so the cashback delay (24 hours) is defined once and reused.
# This avoids hard-coding 86400000 in multiple places and reduces mistakes.


class BankingSystemImpl(BankingSystem):

    def __init__(self):
        self.accounts = {}
        self.pay_log = {}
        self._payment_counter = 0

        self.merged_into = {}
        # This lets get_balance work even when the user queries an old id after a merge.

    def cashback(self, timestamp: int, account_id: str):
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

        # process due refunds in increasing CB_timestamp order for consistent history snapshots
        due = []
        for payment in acc["payments"]:
            pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]
            if (not CB_status) and CB_timestamp <= timestamp:
                due.append((CB_timestamp, payment, CB_amount, pay_account_id))

        due.sort()  # sorting for a chronological processing

        for CB_timestamp, payment, CB_amount, pay_account_id in due:
            acc["current_balance"] += int(CB_amount)

            # record the snapshot at the cashback timestamp itself.
            acc["balance"][CB_timestamp] = acc["current_balance"]

            # Mark cashback as processed so it will not be applied again.
            self.pay_log[payment] = (pay_account_id, CB_timestamp, int(CB_amount), True)

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
            self.accounts[account_id]["transfers"] = {}
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

                # accumulate outgoing at the same timestamp instead of overwriting.
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
                transfer_sum += int(self.accounts[account_id]["transfers"][ts])
            transfer_sum_log.append((account_id, transfer_sum))

        transfer_sum_log.sort(key=lambda x: (-x[1], x[0]))
        n_correct = min(n, len(transfer_sum_log))

        return [f"{acc}({total})" for acc, total in transfer_sum_log[:n_correct]]

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

        # Outgoing includes pay (withdrawals). Accumulate per timestamp.
        self.accounts[account_id]["transfers"][timestamp] = (
            self.accounts[account_id]["transfers"].get(timestamp, 0) + amount
        )

        # use a dedicated counter so ids are always unique and sequential.
        self._payment_counter += 1  # ADDED: stable ordinal even if pay_log size changes indirectly
        pay_str = "payment" + str(self._payment_counter)

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

        # Payment must belong to this account id (after merges, we update ownership to the surviving id).
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

        merge_time = timestamp

        self.merged_into[account_id_2] = account_id_1

        # If account2 had merged accounts before, make those old ids also redirect to account_id_1.
        for old_id in acc2.get("merged_balance_histories", {}).keys():
            self.merged_into[old_id] = account_id_1
       
        
        
        acc1["merged_balance_histories"][account_id_2] = (
            acc2["balance"].copy(),
            acc2["account_created"],
            merge_time
        )

        # If account2 had merged accounts before, inherit those histories too.
        if "merged_balance_histories" in acc2:
            for old_id, tup in acc2["merged_balance_histories"].items():
                acc1["merged_balance_histories"][old_id] = tup

        # Move payments so future cashback from account2 refunds into account1
        acc1["payments"].extend(acc2["payments"])

        acc1["merged_payments"][account_id_2] = list(acc2["payments"])
        if "merged_payments" in acc2:
            for old_id, plist in acc2["merged_payments"].items():
                acc1["merged_payments"][old_id] = list(plist)

        # Update pay_log ownership ONLY for payments that truly belonged to account2.
        for pid in acc2["payments"]:
            pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[pid]
            if pay_account_id == account_id_2:
                self.pay_log[pid] = (account_id_1, CB_timestamp, CB_amount, CB_status)

        # Merge balances (add current balance of account2 into account1).
        acc1["current_balance"] += acc2["current_balance"]
        acc1["balance"][merge_time] = acc1["current_balance"]

        # Merge outgoing transfer histories by summing timestamps.
        for ts, amt in acc2["transfers"].items():
            acc1["transfers"][ts] = acc1["transfers"].get(ts, 0) + int(amt)

        # Remove account2 after merge.
        self.accounts.pop(account_id_2)

        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        """
        Return balance at time_at.

        UPDATED for Level 4 tests:
        - If account_id was merged and removed, and time_at is AFTER the merge,
          redirect to the surviving account and return that balance.
        - If time_at is BEFORE the merge, return the old account’s historical balance.
        """
        original_id = account_id  # ADDED: keep the original id so we can still use its history if needed
        while account_id not in self.accounts and account_id in self.merged_into:
            account_id = self.merged_into[account_id]
            # ADDED: chase merge pointers until we reach an existing account

        if original_id not in self.accounts:
            for root_id, root_acc in self.accounts.items():
                hist = root_acc.get("merged_balance_histories", {})
                if original_id in hist:
                    bal_dict, created_at, merged_at = hist[original_id]

                    if time_at < created_at:
                        return None

                    if time_at < merged_at:
                        # BEFORE merge: return old account’s own balance.
                        keys = [t for t in bal_dict if t <= time_at]
                        return bal_dict[max(keys)] if keys else 0

                    break  

        # Now account_id should be a live account id (or not exist at all).

        
        if account_id not in self.accounts:
            return None

        acc = self.accounts[account_id]

        if acc["account_created"] > time_at:
            return None

        # Apply cashback first so the balance reflects "after processing" at time_at.
        
        self.cashback(time_at, account_id)

        keys = [key for key in acc["balance"] if key <= time_at]
        return acc["balance"][max(keys)] if keys else 0
