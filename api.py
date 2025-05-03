import requests
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq import ApiEnvironmentType

from bunq.sdk.model.generated.endpoint import (
    MonetaryAccountBankApiObject,
    MonetaryAccountApiObject,
    PaymentApiObject,
    RequestInquiryApiObject,
    RequestResponseApiObject,
)
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject
import pprint
import time

BUNQ_HOST = "https://public-api.sandbox.bunq.com"  # or your desired default host

def create_user_and_save_context():
    """
    Creates a new sandbox user by requesting an API key, then creates installation, device registration,
    and saves the API context to a file named with the user id.
    Returns: user_id (int)
    """
    # Step 1: Get API key by creating a new sandbox user
    url = f"{BUNQ_HOST}/v1/sandbox-user-person"
    response = requests.post(url)
    response.raise_for_status()
    api_key = response.json()["Response"][0]["ApiKey"]["api_key"]
    user_id = response.json()["Response"][0]["ApiKey"]["user"]["UserPerson"]["id"]

    # Context filename depends on user id
    context_filename = f"contexts/{user_id}.json"

    # Step 2: Create API context for sandbox
    api_context = ApiContext.create(ApiEnvironmentType.SANDBOX, api_key, f"User {user_id}")
    api_context.save(context_filename)
    BunqContext.load_api_context(api_context)

    # Step 3: Get user context using BunqContext
    user_context = BunqContext.user_context()

    # Step 4: Save the context again after all operations
    api_context.save(context_filename)

    # Unload context to allow multiple independent calls
    BunqContext._api_context = None
    BunqContext._user_context = None

    return user_id

def create_monetary_account_for_user(user_id: int, currency: str = "EUR"):
    """
    Creates a monetary account for the user and returns its id.
    """
    context_filename = f"contexts/{user_id}.json"
    api_context = ApiContext.restore(context_filename)
    BunqContext.load_api_context(api_context)

    # Create the monetary account
    account = MonetaryAccountBankApiObject.create(
        currency
    )
    # Get the id of the newly created account
    account_id = account.value

    # Unload context after operation
    BunqContext._api_context = None
    BunqContext._user_context = None

    return account_id

def create_payment(
    user_id: int,
    monetary_account_id: int,
    amount_value: str,
    amount_currency: str,
    counterparty_alias,
    description: str = "Test Payment"
):
    """
    Creates and sends a payment from the given user's monetary account to the specified IBAN alias.
    Returns: payment id (int)
    """
    context_filename = f"contexts/{user_id}.json"
    api_context = ApiContext.restore(context_filename)
    BunqContext.load_api_context(api_context)

    payment = PaymentApiObject.create(
        {"value": amount_value, "currency": amount_currency},
        {
            "type": counterparty_alias.type_,
            "value": counterparty_alias.value,
            "name": counterparty_alias.name
        },
        description,
        monetary_account_id
    )
    # Get the id of the newly created payment
    payment_id = payment.value

    BunqContext._api_context = None
    BunqContext._user_context = None
    return payment_id

def create_payment_request(
    user_id: int,
    monetary_account_id: int,
    amount_value: str,
    amount_currency: str,
    counterparty_alias,
    description: str
):
    """
    Creates and sends a PaymentRequest (RequestInquiry) to the specified counterparty alias.
    Returns: request id (int)
    """
    context_filename = f"contexts/{user_id}.json"
    api_context = ApiContext.restore(context_filename)
    BunqContext.load_api_context(api_context)

    amount_obj = AmountObject(amount_value, amount_currency)

    request = RequestInquiryApiObject.create(
        amount_obj,
        counterparty_alias,
        description,
        False,  # allow_bunqme
        monetary_account_id
    )
    # Get the id of the newly created request
    request_id = request.value

    BunqContext._api_context = None
    BunqContext._user_context = None
    return request_id

def respond_to_payment_request(
    user_id: int,
    monetary_account_id: int,
    counterparty_iban: str,
    status: str
):
    """
    Responds to all pending payment requests received from a specific counterparty IBAN.
    :param user_id: The user id.
    :param monetary_account_id: The id of the monetary account.
    :param counterparty_iban: The IBAN of the counterparty who sent the request.
    :param status: The status to set ("ACCEPTED" or "REJECTED").
    :return: List of updated RequestResponse objects.
    """
    context_filename = f"contexts/{user_id}.json"
    api_context = ApiContext.restore(context_filename)
    BunqContext.load_api_context(api_context)
    request_responses = RequestResponseApiObject.list(monetary_account_id).value

    updated_requests = []
    for req in request_responses:
        # Extract the actual RequestResponse object
        rr = getattr(req, "RequestResponse", None)
        if not rr:
            continue
        # Check for PENDING status and matching counterparty IBAN
        if getattr(rr, "status", None) == "PENDING":
            counterparty = getattr(rr, "counterparty_alias", None)
            if (
                counterparty
                and getattr(counterparty, "type_", None) == "IBAN"
                and getattr(counterparty, "value", None) == counterparty_iban
            ):
                result = RequestResponseApiObject.update(
                    rr.id_,
                    monetary_account_id,
                    status=status
                )
                updated_requests.append(result)

    BunqContext._api_context = None
    BunqContext._user_context = None
    return updated_requests

def list_monetary_accounts_for_user(user_id: int):
    """
    Lists all monetary accounts for the given user.
    :param user_id: The user id.
    :return: List of monetary accounts.
    """
    context_filename = f"contexts/{user_id}.json"
    api_context = ApiContext.restore(context_filename)
    BunqContext.load_api_context(api_context)

    accounts = MonetaryAccountApiObject.list().value

    BunqContext._api_context = None
    BunqContext._user_context = None
    return accounts

def get_account(user_id: int, monetary_account_id: int):
    """
    Returns the details of a specific monetary account for the given user.
    :param user_id: The user id.
    :param monetary_account_id: The id of the monetary account.
    :return: The MonetaryAccountBank object.
    """
    context_filename = f"contexts/{user_id}.json"
    api_context = ApiContext.restore(context_filename)
    BunqContext.load_api_context(api_context)

    account = MonetaryAccountApiObject.get(monetary_account_id).value

    BunqContext._api_context = None
    BunqContext._user_context = None
    return account

def get_iban_alias(account):
    """
    Returns the IBAN alias object from a MonetaryAccountBank.
    Raises an exception if no IBAN alias is found.
    """
    for alias in account.MonetaryAccountBank.alias:
        if alias.type_ == "IBAN":
            return alias
    raise Exception("No IBAN alias found for account")

def workflow_test():
    # Create UserA and UserB
    user_a_id = create_user_and_save_context()
    user_b_id = create_user_and_save_context()

    # Get default monetary accounts for both users (should be one by default)
    accounts_a = list_monetary_accounts_for_user(user_a_id)
    accounts_b = list_monetary_accounts_for_user(user_b_id)

    account_a_id = accounts_a[0].MonetaryAccountBank.id_
    account_b_id = accounts_b[0].MonetaryAccountBank.id_

    print(f"UserA (id={user_a_id}) account id: {account_a_id}")
    print(f"UserB (id={user_b_id}) account id: {account_b_id}")

    # UserA requests 10 EUR from sugardaddy
    create_payment_request(user_a_id, account_a_id, "10.00", "EUR", PointerObject("EMAIL", "sugardaddy@bunq.com"), "Sugar money request")
    time.sleep(3)
    print ("Sugar money received!")

    # UserA sends 8 EUR to UserB's IBAN
    # Find UserB's IBAN alias
    iban_alias_b = get_iban_alias(accounts_b[0])
    print (f"UserB (id={user_b_id}) IBAN: {iban_alias_b.value}")
    create_payment(user_a_id, account_a_id, "8.00", "EUR", iban_alias_b)

    # Refresh account info
    accounts_a = list_monetary_accounts_for_user(user_a_id)
    accounts_b = list_monetary_accounts_for_user(user_b_id)
    balance_a = accounts_a[0].MonetaryAccountBank.balance.value
    balance_b = accounts_b[0].MonetaryAccountBank.balance.value

    print(f"UserA (id={user_a_id}) balance: {balance_a} EUR")
    print(f"UserB (id={user_b_id}) balance: {balance_b} EUR")


# workflow_test()