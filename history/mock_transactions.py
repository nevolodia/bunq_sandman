from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.model.generated.endpoint import PaymentApiObject, RequestInquiryApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject
import random
import time
from datetime import datetime

def generate_mock_transactions(api_context=None):
    """
    Generate different mock transactions including:
    - Requests from sugar daddy
    - Payments to sugar daddy
    - Payments to other hardcoded entities
    
    Args:
        api_context: The BunqContext API context to use for API calls
    """
    print("Starting mock transaction generation...")
    
    # Load context
    if api_context:
        BunqContext.load_api_context(api_context)
    
    # Entities, first being sugar daddy
    entities = [
        {"type": "EMAIL", "value": "sugardaddy@bunq.com", "name": "Sugar Daddy"},
        {"type": "EMAIL", "value": "test+51be74e9-09a9-4633-be79-0037b15082f8@bunq.com", "name": "Guy next door"},
    ]
    
    # Transaction descriptions
    request_descriptions = [
        "Monthly allowance",
        "Weekly spending money",
        "Emergency funds",
        "Shopping spree"
    ]
    
    payment_descriptions = [
        "Rent payment",
        "Utility bills",
        "Grocery shopping",
        "Phone bill",
        "Internet service",
        "Streaming subscription"
    ]
    
    # Requests from sugar daddy
    sugar_daddy_amounts = ["30.00", "100.00", "50.00", "25.00", "45.00"]
    for i in range(15):
        index = i % (len(sugar_daddy_amounts) - 1)
        RequestInquiryApiObject.create(
            AmountObject(sugar_daddy_amounts[index], "EUR"),
            PointerObject("EMAIL", "sugardaddy@bunq.com"),
            request_descriptions[index],
            allow_bunqme=False
        ).value
        print(f"Created request {i+1}/{15} from sugar daddy for €{sugar_daddy_amounts[index]}")

    # Payments to other entities
    payment_amounts = ["0.03", "0.25", "1.00", "1.42", "2.00"]
    for i in range(15):
        try:
            entity = random.choice(entities)
            amount = random.choice(payment_amounts)
            description = random.choice(payment_descriptions)
            
            # Make a payment
            PaymentApiObject.create(
                amount=AmountObject(amount, "EUR"),
                counterparty_alias=PointerObject(entity["type"], entity["value"]),
                description=f"{description} to {entity['name']} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            ).value
            
            print(f"Created payment {i+1}/{15}: €{amount} to {entity['name']} - {description}")
            
            # Add small delay between payments
            time.sleep(0.5)
        except Exception as e:
            print(f"Error creating payment {i+1}: {str(e)}")
    
    print("All transactions have been committed to the network!:)")
