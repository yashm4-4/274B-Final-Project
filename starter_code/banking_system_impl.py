from banking_system import BankingSystem
import numpy as np

class BankingSystemImpl(BankingSystem):

    def __init__(self):
        self.accounts = {}
        self.pay_log = {}
    
    #helper function for CB
    def cashback(self, timestamp: int, account_id: str) -> None:
        """
        Process cashback refunds due by `timestamp`.

        Refunds must be applied at the cashback timestamp (CB_timestamp),
        and the balance snapshot must be recorded at timestamp.
        """
        CB = 0
        #if timestamp >= CB timestamp and CB has not been payed
        for payment in self.accounts[account_id]["payments"]:
              pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]
              if CB_timestamp <= timestamp and CB_status == False:
                  CB += CB_amount
                  self.pay_log[payment] = (pay_account_id, CB_timestamp, CB_amount, True)
        
        #update balance by CB
        if CB >0:
            self.accounts[account_id]["current_balance"] += CB
            if timestamp not in self.accounts[account_id]["balance"]:
                self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"]
    
        return None
    
    def create_account(self, timestamp: int, account_id: str) -> bool:
        """
        Parameters
        ----------
        timestamp: current datetime (account creation)
        account_id: unique account identifier
        Returns
        -------
        bool: `True` if the account was successfully created or
        `False` if an account with `account_id` already exists.
        """
        #check if account already exists
        if account_id in self.accounts:
            return False
        #create account
        else:
            self.accounts[account_id] = {}
            self.accounts[account_id]["account_created"] = timestamp 
            self.accounts[account_id]["balance"] = {}
            self.accounts[account_id]["balance"][timestamp] = 0
            self.accounts[account_id]["current_balance"] = 0
            self.accounts[account_id]["transfers"] = {}
            self.accounts[account_id]["payments"] = []
            return True

    def deposit(self, timestamp: int, account_id: str, amount: int) ->  None:
        """
        Parameters
        ----------
        timestamp: current datetime (deposit timing)
        account_id: unique account identifier
        amount: monetary deposit value
        Returns
        -------
        account balance, or 'None' if account does not exist
        """
        if account_id in self.accounts:  
          #cashback
          self.cashback(timestamp, account_id)

          #update current balance and balance history
          self.accounts[account_id]["current_balance"] += amount
          self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"]
    
          return self.accounts[account_id]["current_balance"]
        
        else:
          return None

    def transfer(self, timestamp: int, source_account_id: str, target_account_id: str, amount: int) -> None:
        """
        Parameters
        ----------
        timestamp: current datetime (transfer timing)
        source_account_id: unique account identifier for transfer outflow
        target_account_id: unique account identifier for transfer inflow
        amount: monetary deposit value
        Returns
        -------
        balance of source_account_id, or 'None' if source_account_id or target_account_id do not exist
        or if source and target accounts are the same, or if insufficient funds for transfer.
        """
        #check if accounts exist or if self-transfer
        if source_account_id not in self.accounts or target_account_id not in self.accounts:
            return None
        if source_account_id == target_account_id:
            return None
        else:
            self.cashback(timestamp, source_account_id)
            self.cashback(timestamp, target_account_id)

            #update balance and transfer history
            if self.accounts[source_account_id]["current_balance"] - amount >= 0:
              self.accounts[source_account_id]["current_balance"] -= amount
              self.accounts[target_account_id]["current_balance"] += amount
              self.accounts[source_account_id]["balance"][timestamp] = self.accounts[source_account_id]["current_balance"]
              self.accounts[target_account_id]["balance"][timestamp] = self.accounts[target_account_id]["current_balance"]
              self.accounts[source_account_id]["transfers"][timestamp] = amount
              return self.accounts[source_account_id]["current_balance"]
            else:
              return None
            

    def top_spenders(self, timestamp: int, n: int) -> list[str]:
        """
        Should return the identifiers of the top `n` accounts with
        the highest outgoing transactions - the total amount of
        money either transferred out of or paid/withdrawn (the
        **pay** operation will be introduced in level 3) - sorted in
        descending order, or in case of a tie, sorted alphabetically
        by `account_id` in ascending order.
        The result should be a list of strings in the following
        format: `["<account_id_1>(<total_outgoing_1>)", "<account_id
        _2>(<total_outgoing_2>)", ..., "<account_id_n>(<total_outgoi
        ng_n>)"]`.
          * If less than `n` accounts exist in the system, then return
          all their identifiers (in the described format).
          * Cashback (an operation that will be introduced in level 3)
          should not be reflected in the calculations for total
          outgoing transactions.
        """
        transfer_sum_log = []
        #sum all transactions for each account
        for account_id in self.accounts:
            transfer_sum = 0
            for timestamp in self.accounts[account_id]["transfers"]:
                transfer_sum += self.accounts[account_id]["transfers"][timestamp]
            transfer_sum_log.append((account_id, transfer_sum))
        
        #sort by decreasing transfer sum, then increasing account name if tie
        transfer_sum_log.sort(key=lambda x: (-x[1], x[0]))

        #ensure n top spenders is at most equal to number of accounts
        if n > len(transfer_sum_log):
            n_correct = len(transfer_sum_log)
        else:
            n_correct = n
        
        #build final list of strings
        transfer_sum_log_str = []
        for i in range(n_correct):
            transfer_sum_str = transfer_sum_log[i][0] + "(" + str(transfer_sum_log[i][1]) +")"
            transfer_sum_log_str.append(transfer_sum_str)
        return transfer_sum_log_str


    def pay(self, timestamp: int, account_id: str, amount: int) -> str :
        """
        Should withdraw the given amount of money from the specified
        account.
        All withdraw transactions provide a 2% cashback - 2% of the
        withdrawn amount (rounded down to the nearest integer) will
        be refunded to the account 24 hours after the withdrawal.
        If the withdrawal is successful (i.e., the account holds
        sufficient funds to withdraw the given amount), returns a
        string with a unique identifier for the payment transaction
        in this format:
        `"payment[ordinal number of withdraws from all accounts]"` -
        e.g., `"payment1"`, `"payment2"`, etc.
        Additional conditions:
          * Returns `None` if `account_id` doesn't exist.
          * Returns `None` if `account_id` has insufficient funds to
          perform the payment.
          * **top_spenders** should now also account for the total
          amount of money withdrawn from accounts.
          * The waiting period for cashback is 24 hours, equal to
          `24 * 60 * 60 * 1000 = 86400000` milliseconds (the unit for
          timestamps).
          So, cashback will be processed at timestamp
          `timestamp + 86400000`.
          * When it's time to process cashback for a withdrawal, the
          amount must be refunded to the account before any other
          transactions are performed at the relevant timestamp.
        """

        if account_id not in self.accounts:
            return None
        
        #apply CB if needed
        self.cashback(timestamp, account_id)

        #account does not have sufficient balance for payment
        if amount > self.accounts[account_id]["current_balance"]:
            return None
        
        #update balances and transfers
        self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"] - amount
        self.accounts[account_id]["current_balance"] -= amount
        self.accounts[account_id]["transfers"][timestamp] = amount
        
        pay_count = len(self.pay_log) + 1
        pay_str = "payment" + str(pay_count)

        #create CB
        CB_timestamp = timestamp + 86400000
        CB_amount = np.floor(0.02 * amount) #round down to nearest int, per instructions
        CB_status = False

        #update pay_log
        self.pay_log[pay_str] = (account_id, CB_timestamp, CB_amount, CB_status)
        self.accounts[account_id]["payments"].append(pay_str)

        return pay_str


    def get_payment_status(self, timestamp: int, account_id: str, payment: str) -> str :
        """
        Should return the status of the payment transaction for the
        given `payment`.
        Specifically:
          * Returns `None` if `account_id` doesn't exist.
          * Returns `None` if the given `payment` doesn't exist for
          the specified account.
          * Returns `None` if the payment transaction was for an
          account with a different identifier from `account_id`.
          * Returns a string representing the payment status:
          `"IN_PROGRESS"` or `"CASHBACK_RECEIVED"`.
        """
        #check if account exists and if payment was made from inputted account
        if account_id not in self.accounts:
            return None
        if payment not in self.pay_log:
            return None
        
        #check pay log
        payment_info = self.pay_log[payment]
        #payment_info = (account_id, CB_timestamp, CB_amount, CB_status)
        
        #check payment status from payment info in pay log
        if payment_info[0] != account_id:
            return None
        else:
            if timestamp < payment_info[1]:
                return "IN_PROGRESS"
            else:
                return "CASHBACK_RECEIVED"

    def merge_accounts(self, timestamp: int, account_id_1: str, account_id_2: str) -> bool:
        """
        Should merge `account_id_2` into the `account_id_1`.
        Returns `True` if accounts were successfully merged, or
        `False` otherwise.
        Specifically:
          * Returns `False` if `account_id_1` is equal to
          `account_id_2`.
          * Returns `False` if `account_id_1` or `account_id_2`
          doesn't exist.
          * All pending cashback refunds for `account_id_2` should
          still be processed, but refunded to `account_id_1` instead.
          * After the merge, it must be possible to check the status
          of payment transactions for `account_id_2` with payment
          identifiers by replacing `account_id_2` with `account_id_1`.
          * The balance of `account_id_2` should be added to the
          balance for `account_id_1`.
          * `top_spenders` operations should recognize merged accounts
          - the total outgoing transactions for merged accounts should
          be the sum of all money transferred and/or withdrawn in both
          accounts.
          * `account_id_2` should be removed from the system after the
          merge.
        """
        
        if account_id_1 == account_id_2:
            return False
        
        if account_id_1 not in self.accounts or account_id_2 not in self.accounts:
            return False

        # process pending payments
        self.cashback(timestamp, account_id_1)
        self.cashback(timestamp, account_id_2)
       
        # merged_account_history
        self.accounts[account_id_1].setdefault("merged_account_history", set()).update(
            {account_id_2}.union(self.accounts[account_id_2].get("merged_account_history", set())))
        
        # now merge by updating individual account variables/data structures
        self.accounts[account_id_1]["current_balance"] += self.accounts[account_id_2]["current_balance"]

        #storing deleted acc's balance history separately, did not combine the balance 
        #histories because then we overwrite and lose time stamps
        if "merged_balance_histories" not in self.accounts[account_id_1]:
            self.accounts[account_id_1]["merged_balance_histories"] = {}
        
        #stores (balance history, merge_timestamp)
        self.accounts[account_id_1]["merged_balance_histories"][account_id_2] = (self.accounts[account_id_2]["balance"].copy(), timestamp)
        
        #to check if account_id_2 has any previous merged histories
        if "merged_balance_histories" in self.accounts[account_id_2]:
            for inside, inside_data in self.accounts[account_id_2]["merged_balance_histories"].items():
                self.accounts[account_id_1]["merged_balance_histories"][inside] = inside_data
        
        #new balance at merge timestamp with new/combined current_balance
        self.accounts[account_id_1]["balance"][timestamp] = self.accounts[account_id_1]["current_balance"]
        
        #merge transfers and payments
        merged_transfers = {**self.accounts[account_id_1]["transfers"], **self.accounts[account_id_2]["transfers"]}
        self.accounts[account_id_1]["transfers"] = dict(sorted(merged_transfers.items()))
        
        merged_payments = sorted(self.accounts[account_id_1]["payments"] + self.accounts[account_id_2]["payments"])
        self.accounts[account_id_1]["payments"] = merged_payments

        # update master pay_log to reflect new account synonyms
        for payment, payment_record in self.pay_log.items():
            self.pay_log[payment] = (payment_record[0].replace(account_id_2, account_id_1), *payment_record[1:])

        # remove account_id_2 from accounts
        self.accounts.pop(account_id_2)

        return True
    

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int :
        """
        Should return the total amount of money in the account
        `account_id` at the given timestamp `time_at`.
        If the specified account did not exist at a given time
        `time_at`, returns `None`.
          * If queries have been processed at timestamp `time_at`,
          `get_balance` must reflect the account balance **after** the
          query has been processed.
          * If the account was merged into another account, the merged
          account should inherit its balance history.
        Parameters
        ----------
        timestamp: current datetime
        account_id: unique account identifier
        time_at: query timestamp to look up account balance
        """
        
        if account_id not in self.accounts:
            #search for the deleted account in existing accounts merge histories
            for existing_account in self.accounts:
                if account_id in self.accounts[existing_account].get("merged_account_history", set()):
                    #get balance history
                    merged_histories = self.accounts[existing_account].get("merged_balance_histories", {})
                    deleted_balance, merge_timestamp = merged_histories[account_id]
                        
                    #check when we are querying: before or after merger
                    if time_at >= merge_timestamp:
                        return None
                        
                    time_account_created = min(deleted_balance.keys())
                    if time_account_created > time_at:
                        return None
                        
                    #balance at time_at or earlier
                    time_at_or_before = [x for x in deleted_balance if x <= time_at]
                    if len(time_at_or_before) == 0:
                        return 0
                    return deleted_balance[max(time_at_or_before)] 
            
            #account never existed if not found
            return None
            
        #check if querying before account was created
        if self.accounts[account_id]["account_created"] > time_at:
            return None 
        
        # apply cashback if needed
        self.cashback(time_at, account_id)
        
        # get timestamp keys corresponding to balances logged at or before time_at
        time_at_or_earlier_timestamps = [key for key in self.accounts[account_id]["balance"] if key <= time_at]
        if len(time_at_or_earlier_timestamps) == 0:
            return 0  # no account activity since creation
        else:
            return self.accounts[account_id]["balance"][max(time_at_or_earlier_timestamps)]


