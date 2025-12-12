
from banking_system import BankingSystem







MILLISECONDS_IN_1_DAY = 24 * 60 * 60 * 1000


class BankingSystemImpl(BankingSystem):
    """
    Implementation of the BankingSystem interface.

    This class uses a single internal dictionary `self.accounts`
    to store all accounts ever created. Each account keeps track of:
      - when it was created
      - its balance history over time
      - its current balance
      - all outgoing transfers / payments
      - associated payment ids
      - merge information (if it was merged into another account)

    The levels in the project build on top of the same data model.
    """

    def __init__(self):
        # accounts[account_id] -> dict with per-account data.
        #
        # For each account we store:
        #   "account_created": int
        #   "balance": dict[int, int]        # timestamp -> balance after that moment
        #   "current_balance": int
        #   "transfers": dict[int, int]      # timestamp -> outgoing amount
        #   "payments": list[str]            # ids of payments associated with this account
        #   "merged_into": str | None        # id of account this one is merged into
        #   "merged_at": int | None          # timestamp when merge happened
        #
        self.accounts: dict[str, dict] = {}

        # Global log of all payments:
        # pay_log[payment_id] = (original_account_id, cashback_timestamp,
        #                        cashback_amount, cashback_processed_bool)
        self.pay_log: dict[str, tuple[str, int, int, bool]] = {}

    # Helper methods (used by several levels)

    def _is_active_account(self, account_id: str) -> bool:
        """
        An active account is one that exists and has not been merged
        into another account. Only active accounts can be modified by
        deposit / transfer / pay / top_spenders / get_payment_status.
        """
        data = self.accounts.get(account_id)
        if data is None:
            return False
        return data.get("merged_into") is None

    def _find_root(self, account_id: str) -> str | None:
        """
        Follow the merged_into chain to find the root account for this id.
        The root is the account that has not been merged into another.
        If the account doesn't exist at all, return None.
        """
        if account_id not in self.accounts:
            return None

        curr = account_id
        # simple loop; no path compression needed at this scale
        while self.accounts[curr].get("merged_into") is not None:
            curr = self.accounts[curr]["merged_into"]
        return curr

    def _process_cashback_up_to(self, up_to_timestamp: int, account_id: str) -> None:
        """
        Process all pending cashback refunds for the given account
        whose cashback timestamps are <= up_to_timestamp.

        When a refund is processed:
          - the cashback amount is added to the account's current_balance
          - a new balance snapshot is recorded at the cashback timestamp
          - the payment is marked as processed in pay_log
        """
        if account_id not in self.accounts:
            return

        account = self.accounts[account_id]

        # No payments associated with this account, nothing to do.
        if "payments" not in account:
            return

        for payment_id in account["payments"]:
            orig_account_id, cb_timestamp, cb_amount, cb_processed = self.pay_log[payment_id]
            # Only process if not yet processed and cashback time has passed.
            if (not cb_processed) and cb_timestamp <= up_to_timestamp:
                # Add refund to this account (even if orig_account_id is different).
                account["current_balance"] += cb_amount
                # Record balance snapshot exactly at the cashback timestamp.
                account["balance"][cb_timestamp] = account["current_balance"]
                # Mark cashback as processed.
                self.pay_log[payment_id] = (orig_account_id, cb_timestamp, cb_amount, True)

    def _get_single_account_balance_at(self, account_id: str, time_at: int) -> int | None:
        """
        Helper to get the balance history for a *single* account id only
        (without considering merges). It assumes cashback has already
        been processed up to `time_at` for this account.

        Returns:
          - None if the account did not exist yet at time_at
          - integer balance otherwise
        """
        data = self.accounts.get(account_id)
        if data is None:
            return None

        created_at = data["account_created"]
        if time_at < created_at:
            # Account was not created yet.
            return None

        # Find the largest timestamp <= time_at where we have a balance snapshot.
        eligible_times = [t for t in data["balance"].keys() if t <= time_at]
        if not eligible_times:
            # Should not normally happen (we always store at creation),
            # but as a fallback, treat as zero.
            return 0

        last_t = max(eligible_times)
        return data["balance"][last_t]

    # Level 1: creating accounts, deposits, and transfers

    '''
    Level 1 
Initially, the banking system does not contain any accounts, so implement operations to allow account 
creation, deposits, and transfers between 2 different accounts. 
• create_account(self, timestamp: int, account_id: str) -> bool — should create a new account 
with the given identifier if it doesn't already exist. Returns True if the account was successfully 
created or False if an account with account_id already exists. 
• deposit(self, timestamp: int, account_id: str, amount: int) -> int | None — should deposit the 
given amount of money to the specified account account_id. Returns the balance of the account 
after the operation has been processed. If the specified account doesn't exist, should return None. 
• transfer(self, timestamp: int, source_account_id: str, target_account_id: str, amount: int) -> int 
| None — should transfer the given amount of money from account source_account_id to 
account target_account_id. Returns the balance of source_account_id if the transfer was 
successful or None otherwise. 
o Returns None if source_account_id or target_account_id doesn't exist. 
o Returns None if source_account_id and target_account_id are the same. 
o Returns None if account source_account_id has insufficient funds to perform the transfer. 
    '''
    
    def create_account(self, timestamp: int, account_id: str) -> bool:
        """
        Level 1:
        Create a new account with the given identifier if it does not already exist.

        Returns:
          True  - if the account was successfully created
          False - if an account with this id already exists
        """
        if account_id in self.accounts:
            return False

        # Initialize new account with zero balance at creation time.
        self.accounts[account_id] = {
            "account_created": timestamp,
            "balance": {timestamp: 0},
            "current_balance": 0,
            "transfers": {},
            "payments": [],
            "merged_into": None,
            "merged_at": None,
        }
        return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
        """
        Level 1:
        Deposit `amount` into the given account.

        Returns:
          New balance after the deposit, or
          None if the account does not exist or is no longer active.
        """
        if not self._is_active_account(account_id):
            return None

        # First, process any cashback that should have happened on or before this timestamp.
        self._process_cashback_up_to(timestamp, account_id)

        account = self.accounts[account_id]
        account["current_balance"] += amount
        account["balance"][timestamp] = account["current_balance"]

        return account["current_balance"]

    def transfer(
        self,
        timestamp: int,
        source_account_id: str,
        target_account_id: str,
        amount: int,
    ) -> int | None:
        """
        Level 1:
        Transfer `amount` from source_account_id to target_account_id.

        Returns:
          The source account's balance after the transfer, or
          None if:
            - either account does not exist or is not active
            - source and target are the same
            - source has insufficient funds.
        """
        # Both accounts must be active and distinct.
        if not self._is_active_account(source_account_id):
            return None
        if not self._is_active_account(target_account_id):
            return None
        if source_account_id == target_account_id:
            return None

        # Process any pending cashback for both accounts at this timestamp.
        self._process_cashback_up_to(timestamp, source_account_id)
        self._process_cashback_up_to(timestamp, target_account_id)

        source = self.accounts[source_account_id]
        target = self.accounts[target_account_id]

        if source["current_balance"] < amount:
            # Not enough money to perform the transfer.
            return None

        # Update balances.
        source["current_balance"] -= amount
        target["current_balance"] += amount

        # Record balance snapshots.
        source["balance"][timestamp] = source["current_balance"]
        target["balance"][timestamp] = target["current_balance"]

        # Record outgoing transfer for source (used later for top_spenders).
        source["transfers"][timestamp] = source["transfers"].get(timestamp, 0) + amount

        return source["current_balance"]

    # Level 2: top spenders (ranking by outgoing transactions)
   
    '''
    Level 2 
The bank wants to identify people who are not keeping money in their accounts, so implement operations 
to support ranking accounts based on outgoing transactions. 
• top_spenders(self, timestamp: int, n: int) -> list[str] — should return the identifiers of the 
top n accounts with the highest outgoing transactions - the total amount of money either 
transferred out of or paid/withdrawn (the pay operation will be introduced in level 3) - sorted in 
descending order, or in case of a tie, sorted alphabetically by account_id in ascending order. The 
result should be a list of strings in the following format: ["<account_id_1>(<total_outgoing_1>)", 
"<account_id_2>(<total_outgoing_2>)", ..., "<account_id_n>(<total_outgoing_n>)"]. 
o If less than n accounts exist in the system, then return all their identifiers (in the described 
format). 
o Cashback (an operation that will be introduced in level 3) should not be reflected in the 
calculations for total outgoing transactions.
    '''

    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        """
        Level 2:
        Return the identifiers of the top `n` accounts with the highest
        outgoing transactions so far. Outgoing means:
          - money transferred out
          - money withdrawn by `pay` (Level 3)

        Cashback does NOT reduce the outgoing total.

        The result format is:
          ["<account_id_1>(<total_outgoing_1>)", ..., "<account_id_n>(<total_outgoing_n>)"]

        If fewer than `n` active root accounts exist, return all of them.
        """
        # We aggregate totals by root account id so that merged accounts are
        # counted as a single entity.
        root_to_outgoing: dict[str, int] = {}

        for acc_id, data in self.accounts.items():
            root = self._find_root(acc_id)
            if root is None:
                continue

            # We only show totals for root accounts (merged_into is None).
            if not self._is_active_account(root):
                continue

            # Sum all outgoing transfers/payments stored on this particular account.
            local_outgoing = sum(data["transfers"].values())
            root_to_outgoing[root] = root_to_outgoing.get(root, 0) + local_outgoing

        # Build a list of (account_id, total_outgoing)
        items = list(root_to_outgoing.items())

        # Sort by:
        #   1) total_outgoing descending
        #   2) account_id ascending (alphabetical) for ties
        items.sort(key=lambda x: (-x[1], x[0]))

        # Limit to n entries.
        items = items[:n]

        # Convert to required string format.
        return [f"{acc}({total})" for acc, total in items]

    # Level 3: payments with cashback and payment status
    '''
    Level 3 
returns 500 
returns ["account1(2500)", "account3(1500)", 
"account2(0)"] 
The banking system should allow scheduling payments with some cashback and checking the status of 
scheduled payments. 
• pay(self, timestamp: int, account_id: str, amount: int) -> str | None — should withdraw the given 
amount of money from the specified account. All withdraw transactions provide a 2% cashback - 
2% of the withdrawn amount (rounded down to the nearest integer) will be refunded to the account 
24 hours after the withdrawal. If the withdrawal is successful (i.e., the account holds sufficient 
funds to withdraw the given amount), returns a string with a unique identifier for the payment 
transaction in this format: "payment[ordinal number of withdraws from all accounts]" - 
e.g., "payment1", "payment2", etc. Additional conditions: 
o Returns None if account_id doesn't exist. 
o Returns None if account_id has insufficient funds to perform the payment. 
o top_spenders should now also account for the total amount of money withdrawn from 
accounts. 
o The waiting period for cashback is 24 hours, equal to 24 * 60 * 60 * 1000 = 
86400000 milliseconds (the unit for timestamps). So, cashback will be processed at 
timestamp timestamp + 86400000. 
o When it's time to process cashback for a withdrawal, the amount must be refunded to the 
account before any other transactions are performed at the relevant timestamp. 
• get_payment_status(self, timestamp: int, account_id: str, payment: str) -> str | None — should 
return the status of the payment transaction for the given payment. Specifically: 
o Returns None if account_id doesn't exist. 
o Returns None if the given payment doesn't exist for the specified account. 
o Returns None if the payment transaction was for an account with a different identifier 
from account_id. 
o Returns a string representing the payment 
status: "IN_PROGRESS" or "CASHBACK_RECEIVED". 
     
    '''
    def pay(self, timestamp: int, account_id: str, amount: int) -> str | None:
        """
        Level 3:
        Withdraw `amount` from the specified account with 2% cashback.

        Cashback:
          - 2% of `amount` (rounded down) is refunded
          - refund happens at timestamp `timestamp + MILLISECONDS_IN_1_DAY`
          - refunds are applied before any other operations at the cashback timestamp

        Returns:
          - A unique payment id like "payment1", "payment2", ...
          - None if the account does not exist / is not active
          - None if there are insufficient funds
        """
        if not self._is_active_account(account_id):
            return None

        # Process any old cashback first.
        self._process_cashback_up_to(timestamp, account_id)

        account = self.accounts[account_id]

        if account["current_balance"] < amount:
            return None

        # Perform the withdrawal.
        account["current_balance"] -= amount
        account["balance"][timestamp] = account["current_balance"]

        # Record as outgoing for Level 2.
        account["transfers"][timestamp] = account["transfers"].get(timestamp, 0) + amount

        # Create a new unique payment id.
        payment_index = len(self.pay_log) + 1
        payment_id = f"payment{payment_index}"

        # Compute cashback details.
        cb_timestamp = timestamp + MILLISECONDS_IN_1_DAY
        cb_amount = (amount * 2) // 100  # 2% rounded down
        cb_processed = False

        # Log the payment globally.
        self.pay_log[payment_id] = (account_id, cb_timestamp, cb_amount, cb_processed)
        # Attach payment to this account.
        account["payments"].append(payment_id)

        return payment_id

    def get_payment_status(
        self, timestamp: int, account_id: str, payment: str
    ) -> str | None:
        """
        Level 3:
        Return the status of the given payment id for the given account.

        Returns:
          - None if account_id does not exist or is not active
          - None if the payment id does not exist
          - None if the payment was not associated (even indirectly) with this account
          - "IN_PROGRESS" or "CASHBACK_RECEIVED" otherwise
        """
        if not self._is_active_account(account_id):
            # After a merge, the old account id should be treated as non-existing
            # for status checks, which matches the spec example.
            return None

        if payment not in self.pay_log:
            return None

        orig_acc_id, cb_timestamp, cb_amount, cb_processed = self.pay_log[payment]

        # Determine the root account for the original payment owner.
        root_for_payment = self._find_root(orig_acc_id)
        if root_for_payment != account_id:
            # Payment does not belong to this (root) account.
            return None

        # For the root account, process cashback up to this timestamp so that
        # at cb_timestamp the cashback has already been applied.
        self._process_cashback_up_to(timestamp, account_id)

        # After processing, reload the status from pay_log.
        _, _, _, cb_processed_updated = self.pay_log[payment]

        if cb_processed_updated:
            return "CASHBACK_RECEIVED"
        else:
            return "IN_PROGRESS"

    # Level 4: merging accounts and historical balance
    '''
    Level 4 
The banking system should support merging two accounts while retaining both accounts' balance and 
transaction histories. 
• merge_accounts(self, timestamp: int, account_id_1: str, account_id_2: str) -> bool — should 
merge account_id_2 into the account_id_1. Returns True if accounts were successfully merged, 
or False otherwise. Specifically: 
o Returns False if account_id_1 is equal to account_id_2. 
o Returns False if account_id_1 or account_id_2 doesn't exist. 
o All pending cashback refunds for account_id_2 should still be processed, but refunded 
to account_id_1 instead. 
o After the merge, it must be possible to check the status of payment transactions 
for account_id_2 with payment identifiers by replacing account_id_2 with account_id_1. 
o The balance of account_id_2 should be added to the balance for account_id_1. 
o top_spenders operations should recognize merged accounts - the total outgoing 
transactions for merged accounts should be the sum of all money transferred and/or 
withdrawn in both accounts. 
o account_id_2 should be removed from the system after the merge. 
• get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None — should return the 
total amount of money in the account account_id at the given timestamp time_at. If the specified 
account did not exist at a given time time_at, returns None. 
o If queries have been processed at timestamp time_at, get_balance must reflect the 
account balance after the query has been processed. 
o If the account was merged into another account, the merged account should inherit its 
balance history. 

    '''
    def merge_accounts(self, timestamp: int, account_id_1: str, account_id_2: str):
        """
        Level 4:
        Merge account_id_2 into account_id_1.

        Returns:
          True  - if the merge succeeds
          False - otherwise.

        Conditions:
          - Fails if account_id_1 == account_id_2
          - Fails if either account does not exist or is already merged
          - After merge, account_id_2 is treated as removed for future operations
          - All pending cashback for payments originally from account_id_2
            will end up in account_id_1's balance
        """
        # Cannot merge an account into itself.
        if account_id_1 == account_id_2:
            return False

        # Both accounts must exist.
        if account_id_1 not in self.accounts or account_id_2 not in self.accounts:
            return False

        # Both must be active roots (not already merged).
        if not self._is_active_account(account_id_1):
            return False
        if not self._is_active_account(account_id_2):
            return False

        # First, process cashback up to this timestamp for both accounts
        # so that no earlier refunds remain pending.
        self._process_cashback_up_to(timestamp, account_id_1)
        self._process_cashback_up_to(timestamp, account_id_2)

        acc1 = self.accounts[account_id_1]
        acc2 = self.accounts[account_id_2]

        # Mark account_id_2 as merged into account_id_1.
        acc2["merged_into"] = account_id_1
        acc2["merged_at"] = timestamp

        # Move any remaining payments from acc2 to acc1 so that future cashback
        # for those payments goes into acc1.
        for payment_id in acc2["payments"]:
            acc1["payments"].append(payment_id)
        acc2["payments"].clear()

        # Add the full current_balance of acc2 to acc1.
        acc1["current_balance"] += acc2["current_balance"]
        # Record a combined balance snapshot on acc1 at the merge timestamp.
        acc1["balance"][timestamp] = acc1["current_balance"]

        # No need to touch acc2["balance"] or acc2["transfers"]; they are kept
        # for historical queries on old account ids and for root cluster sums.

        return True

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
        """
        Level 4:
        Return the total amount of money in `account_id` at the given
        timestamp `time_at`.

        Rules:
          - If the specified account did not exist at time_at, return None.
          - If queries have been processed at time_at, get_balance reflects
            the balance *after* those queries.
          - If the account was merged into another account, the merged
            account (the root) inherits its balance history, and calls to
            the root at earlier times should reflect combined balances.
        """
        # The account must at least be known; if we have never seen this id,
        # then it truly did not exist at any time.
      
        if account_id not in self.accounts:
            return None

        data = self.accounts[account_id]
        created_at = data["account_created"]
        merged_into = data.get("merged_into")
        merged_at = data.get("merged_at")

        # If this is an old, merged-out id, we treat it as a standalone account
        # only before its merge time.
      
        if merged_into is not None:
          
            # This account_id was merged into another; it "exists" as its own
            # id between [created_at, merged_at).
          
            if time_at < created_at:
                return None
            if merged_at is not None and time_at >= merged_at:
              
                # At and after the merge time, this id should not be queried
                # directly according to the spec examples.
              
                return None

            # For historical queries before merge, we need to ensure cashback
            # is processed up to time_at for this account.
          
            self._process_cashback_up_to(time_at, account_id)
            return self._get_single_account_balance_at(account_id, time_at)

        # Otherwise, this is a root account (possibly with merged children).
      
        root_id = account_id

        # If the root account itself did not exist yet at time_at, then
        # it definitely had no balance at that time.
      
        if time_at < created_at:
            return None

        # For the root and all accounts that eventually merged into it,
        # we process cashback up to time_at so that balance snapshots
        # include all refunds.
      
        for acc_id in self.accounts.keys():
            if self._find_root(acc_id) == root_id:
                self._process_cashback_up_to(time_at, acc_id)

        # Now compute the sum of balances over the entire "cluster" of
        # accounts that share this root, at time_at.
        total_balance = 0
        for acc_id, acc_data in self.accounts.items():
            if self._find_root(acc_id) != root_id:
                continue

            acc_created_at = acc_data["account_created"]
            if time_at < acc_created_at:
              
                # This particular account did not yet exist at time_at.
                continue

            # Get per-account balance at time_at (0 if no snapshots before time_at).
          
            single_balance = self._get_single_account_balance_at(acc_id, time_at)
            if single_balance is not None:
                total_balance += single_balance

        return total_balance
