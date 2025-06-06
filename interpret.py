import time
import api
from queue import Queue

class BunqInterpreter:
    def __init__(self):
        # Maps UI index to Bunq user id
        self.user_map = {}
        # Maps UI index to Bunq account id
        self.account_map = {}
        self.user_for_account = {}
        self.iban_alias_for_account = {}

    def interpret(self, actions, event_queue):
        for action_i, action in enumerate(actions):
            action_type = action.get("action_type", event_queue)
            if action_type == "CreateUserPerson":
                try:
                    start = time.time()
                    self._create_user_person(action, event_queue)
                    elapsed = time.time() - start
                    event_queue.put({ "action_index": action_i, "type": "success", "message": f"User created successfully in {elapsed:.3f}s"})
                except Exception as e:
                    event_queue.put({ "action_index": action_i, "type": "error", "message": f"Error creating user: {e}" })
            elif action_type == "LoginUserPerson":
                try:
                    start = time.time()
                    self._login_user_person(action, event_queue)
                    elapsed = time.time() - start
                    event_queue.put({ "action_index": action_i, "type": "success", "message": f"User logged in successfully in {elapsed:.3f}s" })
                except Exception as e:
                    event_queue.put({ "action_index": action_i, "type": "error", "message": f"Error logging in user: {e}" })
            elif action_type == "CreateMonetaryAccount":
                try:
                    start = time.time()
                    self._create_monetary_account(action, event_queue)
                    elapsed = time.time() - start
                    event_queue.put({ "action_index": action_i, "type": "success", "message": f"Monetary account created successfully in {elapsed:.3f}s" })
                except Exception as e:
                    event_queue.put({ "action_index": action_i, "type": "error", "message": f"Error creating monetary account: {e}" })
            elif action_type == "GetAccountOverview":
                try:
                    start = time.time()
                    self._get_account_overview(action, event_queue, action_i)
                    elapsed = time.time() - start
                    event_queue.put({"action_index": action_i, "type": "success", "message": f"Account overview retrieved successfully in {elapsed:.3f}s"})
                except Exception as e:
                    event_queue.put({"action_index": action_i, "type": "error", "message": f"Error retrieving account overview: {e}"})
            elif action_type == "MakePayment":
                try:
                    start = time.time()
                    self._make_payment(action, event_queue)
                    elapsed = time.time() - start
                    event_queue.put({ "action_index": action_i, "type": "success", "message": f"Payment made successfully in {elapsed:.3f}s" })
                except Exception as e:
                    event_queue.put({ "action_index": action_i, "type": "error", "message": f"Error making payment: {e}" })
            elif action_type == "RequestPayment":
                try:
                    start = time.time()
                    self._request_payment(action, event_queue)
                    elapsed = time.time() - start
                    event_queue.put({ "action_index": action_i, "type": "success", "message": f"Payment request sent successfully in {elapsed:.3f}s" })
                except Exception as e:
                    event_queue.put({ "action_index": action_i, "type": "error", "message": f"Error sending payment request: {e}" })
            elif action_type == "RespondToPaymentRequest":
                try:
                    start = time.time()
                    self._respond_to_payment_request(action, event_queue, action_i)
                    elapsed = time.time() - start
                    event_queue.put({ "action_index": action_i, "type": "success", "message": f"Responded to payment request successfully in {elapsed:.3f}s" })
                except Exception as e:
                    event_queue.put({ "action_index": action_i, "type": "error", "message": f"Error responding to payment request: {e}" })
            elif action_type == "Sleep":  # Let me sleep please Im so tired
                sleep_time = action.get("seconds", 1)
                event_queue.put({"type": "success", "message": f"Sleeping for {sleep_time} seconds"})
                time.sleep(sleep_time)
            else:
                event_queue.put({"action_index": action_i, "type": "error", "message": f"Unknown action type: {action_type}"})


    def _create_user_person(self, action, event_queue):
        user_id = action.get("user_id")
        user_id_bunq = api.create_user_and_save_context()
        self.user_map[user_id] = user_id_bunq
    
    def _login_user_person(self, action, event_queue):
        api_key = action.get("api_key")
        user_id_bunq = api.login_user_and_save_context(api_key)
        self.user_map[action["user_id"]] = user_id_bunq

    def _create_monetary_account(self, action, event_queue):
        user_id = self.user_map[action["user_id"]]
        account_id = action["account_id"]
        currency = action.get("currency", "EUR")
        account_id_bunq = api.create_monetary_account_for_user(user_id, currency)
        self.account_map[account_id] = account_id_bunq
        self.user_for_account[account_id_bunq] = user_id

        account = api.get_account(user_id, account_id_bunq)
        self.iban_alias_for_account[account_id_bunq] = api.get_iban_alias(account)

    def _get_account_overview(self, action, event_queue, action_i):
        account_id = self.account_map[action["account_id"]]
        user_id = self.user_for_account[account_id]
        
        overview = api.get_account(user_id, account_id)
        balance = overview.MonetaryAccountBank.balance.value
        event_queue.put({ "action_index": action_i, "type": "log", "message": f"Account {action['account_id']} balance: {balance}"})

    def _make_payment(self, action, event_queue):
        account_id = self.account_map[action["account_id"]]
        user_id = self.user_for_account[account_id]
        amount_value = str(action["amount_value"])
        amount_currency = action["amount_currency"]
        counterparty_account_id = self.account_map[action["counterparty_account_id"]]
        counterparty_alias = self.iban_alias_for_account[counterparty_account_id]
        description = action.get("description", "No description")
        api.create_payment(user_id, account_id, amount_value, amount_currency, counterparty_alias, description)

    def _request_payment(self, action, event_queue):
        account_id = self.account_map[action["account_id"]]
        user_id = self.user_for_account[account_id]
        amount_value = str(action["amount_value"])
        amount_currency = action["amount_currency"]
        
        counterparty_alias = {}
        if action["counterparty_account_id"].lower() == "sugardaddy":
            counterparty_alias = {
                "type": "EMAIL",
                "value": "sugardaddy@bunq.com",
                "name": "sugardaddy@bunq.com",
            }
        else:
            counterparty_account_id = self.account_map[action["counterparty_account_id"]]
            counterparty_alias = self.iban_alias_for_account[counterparty_account_id]

        description = action.get("description", "No description")
        api.create_payment_request(user_id, account_id, amount_value, amount_currency, counterparty_alias, description)

    def _respond_to_payment_request(self, action, event_queue, action_i):
        account_id = self.account_map[action["account_id"]]
        user_id = self.user_for_account[account_id]
        status = action.get("status", "REJECTED")
        counterparty_account_id = self.account_map[action["counterparty_account_id"]]
        counterparty_iban_alias = self.iban_alias_for_account[counterparty_account_id]
        updated_requests_id = api.respond_to_payment_request(user_id, account_id, counterparty_iban_alias, status)
        event_queue.put( {"action_index": action_i, "type": "log", "message": f"Responded to  {len(updated_requests_id)} requests for the user {action['account_id']}" })


def test_create_user_and_accounts():
    actions = [
        {"action_type": "CreateUserPerson", "user_id": 0},
        {"action_type": "CreateUserPerson", "user_id": 1},
        {"action_type": "Sleep", "seconds": 1},
        {"action_type": "CreateMonetaryAccount", "user_id": 0, "account_id": "A", "currency": "EUR"},
        {"action_type": "CreateMonetaryAccount", "user_id": 1, "account_id": "B", "currency": "EUR"},
        {"action_type": "RequestPayment", "user_id": 0, "account_id": "A", "amount_value": 10.00, "amount_currency": "EUR", "counterparty_account_id": "sugardaddy"},
        {"action_type": "Sleep", "seconds": 5},
        {"action_type": "RequestPayment", "user_id": 1, "account_id": "B", "amount_value": 5.00, "amount_currency": "EUR", "counterparty_account_id": "A"},
        {"action_type": "Sleep", "seconds": 1},
        {"action_type": "RespondToPaymentRequest", "user_id": 0, "account_id": "A", "counterparty_account_id": "B", "status": "ACCEPTED"},
        {"action_type": "Sleep", "seconds": 1},
        {"action_type": "GetAccountOverview", "user_id": 1, "account_id": "B"},
    ]
    event_queue = Queue()
    interpreter = BunqInterpreter()
    interpreter.interpret(actions, event_queue)
    while not event_queue.empty():
        print(event_queue.get())