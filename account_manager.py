import json
from typing import List, Dict
import os

class AccountManager:
    def __init__(self):
        self.accounts: Dict = {}
        self.disabled_accounts: List[str] = []
        self.current_account_index = 0
        self.active_accounts: List[str] = []
        
        self.load_accounts()
        self.load_disabled_accounts()
        self.update_active_accounts()

    def load_accounts(self):
        try:
            with open('accounts.json', 'r') as f:
                self.accounts = json.load(f)
        except FileNotFoundError:
            self.accounts = {}

    def load_disabled_accounts(self):
        try:
            with open('disabled_accounts.json', 'r') as f:
                data = json.load(f)
                self.disabled_accounts = data.get('disabled_accounts', [])
        except FileNotFoundError:
            self.disabled_accounts = []

    def update_active_accounts(self):
        self.active_accounts = [
            account for account in self.accounts.keys()
            if account not in self.disabled_accounts
        ]

    def save_disabled_accounts(self):
        with open('disabled_accounts.json', 'w') as f:
            json.dump({'disabled_accounts': self.disabled_accounts}, f, indent=2)

    def disable_account(self, account_email: str):
        if account_email not in self.disabled_accounts:
            self.disabled_accounts.append(account_email)
            self.update_active_accounts()
            self.save_disabled_accounts()

    def get_next_account(self) -> tuple[str, dict]:
        if not self.active_accounts:
            raise Exception("No active accounts available")

        account_email = self.active_accounts[self.current_account_index]
        account_data = self.accounts[account_email]
        
        return account_email, account_data 