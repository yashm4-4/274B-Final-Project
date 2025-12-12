from banking_system import BankingSystem
import numpy as np

class BankingSystemImpl(BankingSystem):

    def __init__(self):
        self.accounts = {}
        self.pay_log = {}

    def cashback(self, timestamp: int, account_id: str) -> None:
        CB = 0
        for payment in self.accounts[account_id]["payments"]:
              pay_account_id, CB_timestamp, CB_amount, CB_status = self.pay_log[payment]
              if CB_timestamp <= timestamp and CB_status == False:
                  CB += CB_amount
                  self.pay_log[payment] = (pay_account_id, CB_timestamp, CB_amount, True)
        #balance structure needs to be changed to store balance + timestamp
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
        if account_id in self.accounts:
            return False
        else:
            self.accounts[account_id] = {}
            self.accounts[account_id]["account_created"] = timestamp 
            #balance structure needs to be changed to store balance + timestamp. Done here
            self.accounts[account_id]["balance"] = {}
            self.accounts[account_id]["balance"][timestamp] = 0
            self.accounts[account_id]["current_balance"] = 0
            #self.accounts[account_id]["deposits"] = {} #i think we can get rid of this
            self.accounts[account_id]["transfers"] = {}
            self.accounts[account_id]["payments"] = []
            return True

    def deposit(self, timestamp: int, account_id: str, amount: int) -> int | None:
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

          #self.accounts[account_id]["deposits"][timestamp] = amount #i think we can get rid of this. its unused later and complicates CB
          #balance structure needs to be changed to store balance + timestamp
          self.accounts[account_id]["current_balance"] += amount
          self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"]
    
          return self.accounts[account_id]["current_balance"]
        
        else:
          return None

    def transfer(self, timestamp: int, source_account_id: str, target_account_id: str, amount: int) -> int | None:
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
        
        if source_account_id not in self.accounts or target_account_id not in self.accounts:
            return None
        if source_account_id == target_account_id:
            return None
        else:
            self.cashback(timestamp, source_account_id)
            self.cashback(timestamp, target_account_id)

            #balance structure needs to be changed to store balance + timestamp
            if self.accounts[source_account_id]["current_balance"] - amount >= 0:
              self.accounts[source_account_id]["current_balance"] -= amount
              self.accounts[target_account_id]["current_balance"] += amount
              self.accounts[source_account_id]["balance"][timestamp] = self.accounts[source_account_id]["current_balance"]
              self.accounts[target_account_id]["balance"][timestamp] = self.accounts[target_account_id]["current_balance"]
    
              #self.accounts[target_account_id]["deposits"][timestamp] = amount #i think we can get rid of this
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
                transfer_sum += np.sum(self.accounts[account_id]["transfers"][timestamp])
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


    def pay(self, timestamp: int, account_id: str, amount: int) -> str | None:
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
        
        self.cashback(timestamp, account_id)

        if amount > self.accounts[account_id]["current_balance"]:
            return None
        
        #balance structure needs to be changed to store balance + timestamp
        self.accounts[account_id]["balance"][timestamp] = self.accounts[account_id]["current_balance"] - amount
        self.accounts[account_id]["current_balance"] -= amount
        self.accounts[account_id]["transfers"][timestamp] = amount
        
        pay_count = len(self.pay_log) + 1
        pay_str = "payment" + str(pay_count)

        CB_timestamp = timestamp + 86400000
        CB_amount = np.floor(0.02 * amount) #round down to nearest int, per instructions
        CB_status = False

        self.pay_log[pay_str] = (account_id, CB_timestamp, CB_amount, CB_status)
        self.accounts[account_id]["payments"].append(pay_str)

        return pay_str


    def get_payment_status(self, timestamp: int, account_id: str, payment: str) -> str | None:
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
        if account_id not in self.accounts:
            return None
        if payment not in self.pay_log:
            return None
        
        payment_info = self.pay_log[payment]
        #payment_info = (account_id, CB_timestamp, CB_amount, CB_status)
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


        """
        do these checks:
        Returns `False` if `account_id_1` is equal to
          `account_id_2`.
          * Returns `False` if `account_id_1` or `account_id_2`
          doesn't exist.
        
        call cashback on each account - this is just so they are accurate prior to merge

        All pending cashback refunds for `account_id_2` should
        still be processed, but refunded to `account_id_1` instead.
        this is for cashbacks for CB_timestamp > timestamp
        to do this, look at payment list for account 2. search pay log for account 2 payments
        and replace account id with account 1

        Need to merge balance history and transaction history
        timesteps may not match, so add (transaction, timestamp), (balance, timestamp) for
        each account into transaction list and balance list, then sort by timestamp
        update new account with transaction list and balance list by feeding it to their dicts

        (transaction1, 1) (transaction2, 2) (transaction 1, 1)
        
        top spenders will work if the above is done correctly

        remove everything for account 2 

        return True

        """
        
        if account_id_1 == account_id_2:
            return False
        
        if account_id_1 not in self.accounts or account_id_2 not in self.accounts:
            return False

        # process pending payments
        self.cashback(timestamp, account_id_1)
        self.cashback(timestamp, account_id_2)
       
        # create or update merged_account_history as account_id_1 dictionary key:value
        # merged_account_history stores a set of merged account ids, adding both the
        # merged account_id_2 and the merger history of account_id_2 to account_id_1's
        # merged_account_history
        self.accounts[account_id_1].setdefault("merged_account_history", set()).update(
            {account_id_2}.union(self.accounts[account_id_2].get("merged_account_history", set())))

        # now merge by updating individual account variables/data structures
        self.accounts[account_id_1]["current_balance"] += self.accounts[account_id_2]["current_balance"]
        
        # only add the new balance to account_id_1 (do not transfer over account_id_2 balance history)
        self.accounts[account_id_1]["balance"][timestamp] = self.accounts[account_id_1]["current_balance"]
        
        #implement merged_balance similar to below.
        #account 1: (1, balance 1) , (3, balance 1.1)
        #account2: (1, balance2), (2, balance 2.1)
        #mergedaccount: (1, balance 1 + balance 2) (2, balance2.1 + increase in earlier balance)
        
        merged_transfers = {**self.accounts[account_id_1]["transfers"], **self.accounts[account_id_2]["transfers"]}
        self.accounts[account_id_1]["transfers"] = dict(sorted(merged_transfers.items()))
        
        merged_payments = sorted(self.accounts[account_id_1]["payments"] + self.accounts[account_id_2]["payments"])
        self.accounts[account_id_1]["payments"] = merged_payments

        # update master pay_log to reflect new account synonyms
        for payment, payment_record in self.pay_log.items():
            self.pay_log[payment] = (payment_record[0].replace(account_id_2, account_id_1), *payment_record[1:])

        #need to update CB payments?

        # remove account_id_2 from accounts
        self.accounts.pop(account_id_2)

        return True
    

    def get_balance(self, timestamp: int, account_id: str, time_at: int) -> int | None:
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
        #this may be wrong if we need to access balance history for account that was deleted
        #this is causing a failure - confirmed
        #self.assertEqual(self.system.get_balance(28, 'account3', 13), 600) - we return None
        #account 3 was merged into different account previously. need to be able to search by deleted... 
        #...account to get history of new account it was merged into.
        
        #self.assertEqual(self.system.get_balance(86400043, 'acc2', 19), 8094)- we return None
        #again we are failing because acc2 was merged into acc1 already, so acc2 doesnt exist
        #we need some way to search by deleted accounts. maybe store a merge log or something

        #search in merge log if input account has been merged, then check call get_balance on correct account?
        if account_id not in self.accounts:
            #search merged account history set to see if input arg has been merged
                #if you find that its been merged into new account: get_balance(new account, time_at)
                    #what balance? combined balance of acc1 + acc2? only acc2?
            return None
        
        if self.accounts[account_id]["account_created"] > time_at:
            break
        
        # apply cashback if needed
        
        self.cashback(time_at, account_id)
        
        # get timestamp keys corresponding to balances logged at or before time_at
        time_at_or_earlier_timestamps = [key for key in self.accounts[account_id]["balance"] if key <= time_at]
        if len(time_at_or_earlier_timestamps) == 0:
            return 0  # no account activity since creation
        else:
            return self.accounts[account_id]["balance"][max(time_at_or_earlier_timestamps)]



