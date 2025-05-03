Getting Started
Tools
Software Development Kits (SDKs)
Python
Usage
Installation
Install the bunq Python SDK using pip:

Copy
pip install bunq_sdk --upgrade
Getting Started
Creating an API Context
Before you can make any API calls, you need to create an API context. This involves registering your API key and device, and creating a session.

Copy
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq import ApiEnvironmentType

# Create an API context for production
api_context = ApiContext.create(
    ApiEnvironmentType.PRODUCTION, # SANDBOX for testing
    "YOUR_API_KEY",
    "My Device Description"
)

# Save the API context to a file for future use
api_context.save("bunq_api_context.conf")

# Load the API context into the SDK
BunqContext.load_api_context(api_context)
Note: Initializing an API context is a heavy operation and should only be done once per device.

Saving and Restoring the API Context
After creating an API context, you can save it to a file and restore it in future sessions:

Copy
# Save API context
api_context.save("bunq_api_context.conf")

# Restore API context
api_context = ApiContext.restore("bunq_api_context.conf")
BunqContext.load_api_context(api_context)
PSD2 Integration
The SDK supports PSD2 (Payment Services Directive 2) integration, allowing you to act as a PSD2 Service Provider:

Copy
api_context = ApiContext.create_for_psd2(
    ApiEnvironmentType.SANDBOX,
    certificate,             # Your eIDAS certificate
    private_key,             # Your private key
    certificate_chain,       # Your certificate chain
    "PSD2 Device Description"
)

api_context.save("bunq_psd2_api_context.conf")
Note: For sandbox environments, any certificate meeting basic criteria will be accepted. For production, you'll need a valid eIDAS certificate.

Safety Considerations
The file storing your API context (e.g., bunq_api_context.conf) contains sensitive information that provides access to your bunq account. Store this file in a secure location and ensure it's not accessible to unauthorized users.

Core Concepts
API Context
The API context contains your authentication credentials and session information for interacting with the bunq API. It includes:

API key

Installation token

Session token

Server public key

Environment type (Sandbox or Production)

User Context
The user context represents the user you're authenticated as and provides access to account-specific operations:

Copy
# Access the user context
user_context = BunqContext.user_context()

# Get the user ID
user_id = user_context.user_id

# Get the primary monetary account
primary_account = user_context.primary_monetary_account
Monetary Accounts
Monetary accounts are banking accounts within bunq. A user can have multiple monetary accounts, with one designated as the primary account.

Making API Calls
The SDK follows a consistent pattern for API calls. Each endpoint has a corresponding class with methods for supported operations.

Creating Objects
To create a new resource:

Copy
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject

# Create a payment
payment_id = PaymentApiObject.create(
    amount=AmountObject("10.00", "EUR"),
    counterparty_alias=PointerObject("EMAIL", "recipient@example.com"),
    description="Payment for services"
).value
Reading Objects
To retrieve a specific resource:

Copy
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject

# Get a monetary account
monetary_account = MonetaryAccountBankApiObject.get(account_id).value
Updating Objects
To update an existing resource:

Copy
from bunq.sdk.model.generated.endpoint import CardApiObject

# Update a card's settings
CardApiObject.update(
    card_id=123,
    monetary_account_current_id=456
)
Deleting Objects
To delete a resource:

Copy
from bunq.sdk.model.generated.endpoint import SessionApiObject

# Delete a session
SessionApiObject.delete(session_id)
Listing Objects
To retrieve a list of resources:

Copy
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq import Pagination

# Create pagination settings
pagination = Pagination()
pagination.count = 10  # Number of items per page

# List payments with pagination
payments = PaymentApiObject.list(params=pagination.url_params_count_only).value
Working with Resources
Payments
Make payments between accounts:

Copy
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject

# Make a payment to another user
payment_id = PaymentApiObject.create(
    amount=AmountObject("5.00", "EUR"),
    counterparty_alias=PointerObject("EMAIL", "recipient@example.com"),
    description="Lunch payment"
).value

# Make a payment to another account of the same user
payment_id = PaymentApiObject.create(
    amount=AmountObject("5.00", "EUR"),
    counterparty_alias=PointerObject("IBAN", "NL12BUNQ1234567890"),
    description="Transfer to savings"
).value

# Create a batch of payments
from typing import List

def create_payment_batch(payments_list: List[PaymentApiObject]):
    return PaymentBatchApiObject.create(payments_list).value
Monetary Accounts
Create and manage monetary accounts:

Copy
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject

# Create a new monetary account
account_id = MonetaryAccountBankApiObject.create(
    currency="EUR",
    description="Savings Account"
).value

# Close a monetary account
MonetaryAccountBankApiObject.update(
    monetary_account_id=account_id,
    status="CANCELLED",
    sub_status="REDEMPTION_VOLUNTARY",
    reason="OTHER",
    reason_description="No longer needed"
)
Cards
Manage debit cards:

Copy
from bunq.sdk.model.generated.endpoint import CardDebitApiObject
from bunq.sdk.model.generated.object_ import CardPinAssignmentObject
from bunq.sdk.context.bunq_context import BunqContext

# Get allowed card name
card_name = CardNameApiObject.list().value[0].possible_card_name_array[0]

# Create a pin code assignment
pin_code_assignment = CardPinAssignmentObject(
    "PRIMARY",
    "MANUAL",
    "1234",
    BunqContext.user_context().primary_monetary_account.id_
)

# Order a new debit card
card_id = CardDebitApiObject.create(
    second_line="MY CARD",
    name_on_card=card_name,
    type_="MASTERCARD",
    product_type="MASTERCARD_DEBIT",
    alias=primary_alias,
    pin_code_assignment=[pin_code_assignment]
).value

# Update a card
from bunq.sdk.model.generated.endpoint import CardApiObject

CardApiObject.update(
    card_id=card_id,
    monetary_account_current_id=account_id
)
Attachments and Avatars
Work with attachments and avatars:

Copy
from bunq.sdk.model.generated.endpoint import AttachmentPublicApiObject
from bunq.sdk.model.generated.endpoint import AttachmentPublicContentApiObject
from bunq.sdk.model.generated.endpoint import AvatarApiObject
from bunq.sdk.http.api_client import ApiClient

# Upload a public attachment
custom_headers = {
    ApiClient.HEADER_CONTENT_TYPE: "image/jpeg",
    ApiClient.HEADER_ATTACHMENT_DESCRIPTION: "Profile picture",
}

# Read file contents
with open("picture.jpg", "rb") as file:
    attachment_contents = file.read()

# Create attachment
attachment_uuid = AttachmentPublicApiObject.create(
    attachment_contents, 
    custom_headers
).value

# Create an avatar using the attachment
avatar_uuid = AvatarApiObject.create(attachment_uuid).value

# Retrieve attachment content
attachment_content = AttachmentPublicContentApiObject.list(attachment_uuid).value
Requests
Create and respond to payment requests:

Copy
from bunq.sdk.model.generated.endpoint import RequestInquiryApiObject
from bunq.sdk.model.generated.endpoint import RequestResponseApiObject
from bunq.sdk.model.generated.object_ import AmountObject

# Create a payment request
request_id = RequestInquiryApiObject.create(
    AmountObject("10.00", "EUR"),
    counterparty_alias,
    "Please pay for dinner",
    allow_bunqme=False
).value

# Accept a payment request
RequestResponseApiObject.update(
    request_response_id,
    monetary_account_id,
    status="ACCEPTED"
)
Sharing
Share accounts with other bunq users:

Copy
from datetime import datetime, timedelta
from bunq.sdk.model.generated.endpoint import DraftShareInviteBankApiObject
from bunq.sdk.model.generated.object_ import DraftShareInviteEntryObject, ShareDetailObject, ShareDetailReadOnlyObject

# Set expiration date (1 hour from now)
expiration_date = (datetime.utcnow() + timedelta(hours=1)).isoformat()

# Define share details (what the connected person can see/do)
share_detail = ShareDetailObject(read_only=ShareDetailReadOnlyObject(True, True, True))
share_settings = DraftShareInviteEntryObject(share_detail)

# Create share invite
draft_id = DraftShareInviteBankApiObject.create(expiration_date, share_settings).value
Generating Share QR Code

Copy
from bunq.sdk.model.generated.endpoint import DraftShareInviteBankQrCodeContentApiObject

# Get QR code content
qr_content = DraftShareInviteBankQrCodeContentApiObject.list(draft_id).value

# Save QR code as an image
with open('connect-qr.png', 'wb') as f:
    f.write(qr_content)
Advanced Features
Pagination
The SDK supports pagination for listing resources:

Copy
from bunq import Pagination

# Create a pagination object
pagination = Pagination()
pagination.count = 5  # Number of items per page

# Get the first page
response = PaymentApiObject.list(params=pagination.url_params_count_only)
pagination_info = response.pagination

# Check if there's a previous page
if pagination_info.has_previous_page():
    # Get the previous page
    previous_page = PaymentApiObject.list(
        params=pagination_info.url_params_previous_page
    ).value

# Check if there's a next page
if pagination_info.has_next_page_assured():
    # Get the next page
    next_page = PaymentApiObject.list(
        params=pagination_info.url_params_next_page
    ).value
Notification Filters
Set up notification filters (webhooks) to receive updates when certain events occur:

Copy
from bunq.sdk.model.core.notification_filter_url_user_internal import NotificationFilterUrlUserInternal
from bunq.sdk.model.core.notification_filter_push_user_internal import NotificationFilterPushUserInternal
from bunq.sdk.model.generated.object_ import NotificationFilterUrl, NotificationFilterPush

# Create a URL notification filter for account mutations
notification_filter = NotificationFilterUrl("MUTATION", "https://your-webhook.com/callback")
all_notification_filter = [notification_filter]

# Set up user-level URL notifications
created_filters = NotificationFilterUrlUserInternal.create_with_list_response(
    all_notification_filter
).value

# Create a push notification filter
push_filter = NotificationFilterPush("MUTATION")
all_push_filter = [push_filter]

# Set up user-level push notifications
created_push_filters = NotificationFilterPushUserInternal.create_with_list_response(
    all_push_filter
).value

# Clear all notification filters
NotificationFilterUrlUserInternal.create_with_list_response()  # Empty list clears filters
Setting up Account-Specific Notification Filters

You can also set up notification filters for specific monetary accounts:

Copy
from bunq.sdk.model.core.notification_filter_url_monetary_account_internal import NotificationFilterUrlMonetaryAccountInternal
from bunq.sdk.model.generated.object_ import NotificationFilterUrl

# Create a notification filter
notification_filter = NotificationFilterUrl("MUTATION", "https://your-webhook.com/account-callback")

# Set up notification filter for a specific monetary account
NotificationFilterUrlMonetaryAccountInternal.create_with_list_response(
    monetary_account_id,    
    [notification_filter]
)

# Clear notification filters for a specific account
NotificationFilterUrlMonetaryAccountInternal.create_with_list_response(
    monetary_account_id,
    []  # Empty list clears filters
)
OAuth
Use OAuth for authentication:

Copy
from bunq.sdk.model.core.oauth_authorization_uri import OauthAuthorizationUri
from bunq.sdk.model.core.oauth_response_type import OauthResponseType
from bunq.sdk.model.generated.endpoint import OauthClient

# Create an OAuth client
oauth_client = OauthClient("My OAuth Client")

# Generate an authorization URI
authorization_uri = OauthAuthorizationUri.create(
    OauthResponseType(OauthResponseType.CODE),
    "https://your-redirect-uri.com/callback",
    oauth_client,
    "state_token"
).get_authorization_uri()

# Direct user to the authorization URI
print("Please visit:", authorization_uri)
Session Management
Manage API sessions:

Copy
from bunq.sdk.model.generated.endpoint import SessionApiObject
from bunq.sdk.context.bunq_context import BunqContext

# Delete the current session
SessionApiObject.delete(0)

# Reset the API context session
BunqContext.api_context().reset_session()

# Save the updated API context
BunqContext.api_context().save("bunq_api_context.conf")
Error Handling
The SDK uses exceptions to handle errors:

Copy
from bunq.sdk.exception.api_exception import ApiException
from bunq.sdk.exception.bunq_exception import BunqException

try:
    # API call that might fail
    MonetaryAccountBankApiObject.get(invalid_account_id)
except ApiException as e:
    # Handle API-specific errors
    print(f"API error: {e.message}")
    print(f"Response ID: {e.response_id}")  # Useful for support
except BunqException as e:
    # Handle general SDK errors
    print(f"SDK error: {e.message}")
except Exception as e:
    # Handle other exceptions
    print(f"Unexpected error: {str(e)}")
Examples
Example: Making a Payment
Copy
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject

# Load API context
api_context = ApiContext.restore("bunq_api_context.conf")
BunqContext.load_api_context(api_context)

# Create a payment
payment_id = PaymentApiObject.create(
    amount=AmountObject("5.00", "EUR"),
    counterparty_alias=PointerObject("EMAIL", "recipient@example.com"),
    description="Test payment"
).value

print(f"Payment created with ID: {payment_id}")
Example: Listing Transactions
Copy
from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq import Pagination

# Load API context
api_context = ApiContext.restore("bunq_api_context.conf")
BunqContext.load_api_context(api_context)

# Create pagination
pagination = Pagination()
pagination.count = 10

# List payments
payments = PaymentApiObject.list(params=pagination.url_params_count_only).value

# Display payments
for payment in payments:
    print(f"ID: {payment.id_}")
    print(f"Amount: {payment.amount.value} {payment.amount.currency}")
    print(f"Description: {payment.description}")
    print("---")
Troubleshooting
Common Issues and Solutions
Authentication Failures

Ensure your API key is valid

Check that your API context file is up-to-date

Try refreshing your session with BunqContext.api_context().ensure_session_active()

Expired Sessions

Sessions automatically expire; use api_context.ensure_session_active() to refresh if needed

The SDK will usually handle this automatically

Missing Permissions

Ensure your API key has the necessary permissions for the actions you're trying to perform

Resource Not Found

Verify that the resource IDs you're using are correct

Check if the resources still exist (e.g., a monetary account may have been closed)

Rate Limiting

The bunq API has rate limits; implement exponential backoff if you encounter rate limiting