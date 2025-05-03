from bunq.sdk.model.generated.endpoint import PaymentApiObject
from bunq.sdk.context.bunq_context import BunqContext
from bunq import Pagination
import time
import json
from typing import List, Dict, Any


def get_all_transactions_and_users():
    """
    Retrieve all transactions and the users associated with these transactions from the main account.
    
    This function collects all payments (both incoming and outgoing) from the primary monetary account
    and extracts information about the counterparties (users) involved in these transactions.
    
    Returns:
        dict: A dictionary containing:
            - 'transactions': List of all transactions
            - 'users': Dictionary of unique users identified by their ID/alias with their transaction history
    """
    # Get the primary monetary account
    user_context = BunqContext.user_context()
    primary_account = user_context.primary_monetary_account
    primary_account_id = primary_account.id_
    
    print(f"Retrieving transactions for primary account ID: {primary_account_id}")
    
    # Initialize variables to store all transactions and users
    all_transactions = []
    all_users = {}  # Dictionary to store user info keyed by their alias/ID
    
    # Set up pagination with a large count to minimize API calls
    pagination = Pagination()
    pagination.count = 200  # Maximum allowed by the API
    
    # Flag to control whether to continue fetching more pages
    has_more_pages = True
    page_number = 0
    
    # Keep fetching until we've retrieved all transactions
    while has_more_pages:
        page_number += 1
        print(f"Fetching page {page_number} of transactions...")
        
        try:
            # Get a page of payments
            payments_response = PaymentApiObject.list(
                monetary_account_id=primary_account_id,
                params=pagination.url_params_count_only
            )
            
            payments = payments_response.value
            pagination_info = payments_response.pagination
            
            if not payments:
                print("No more transactions found.")
                break
                
            print(f"Retrieved {len(payments)} transactions on page {page_number}.")
            
            # Process each payment
            for payment in payments:
                # Extract payment details
                transaction = {
                    'id': payment.id_,
                    'created': payment.created,
                    'updated': payment.updated,
                    'amount': {
                        'value': payment.amount.value,
                        'currency': payment.amount.currency,
                    },
                    'description': payment.description,
                }
                
                # Extract counterparty information
                if hasattr(payment, 'counterparty_alias') and payment.counterparty_alias:
                    counterparty = {
                        'display_name': payment.counterparty_alias.display_name,
                        'type': getattr(payment.counterparty_alias, 'type_', 'UNKNOWN'),
                        'value': getattr(payment.counterparty_alias, 'value', 'UNKNOWN'),
                    }
                    
                    # Add counterparty to transaction
                    transaction['counterparty'] = counterparty
                    
                    # Use a unique identifier for the counterparty
                    counterparty_id = counterparty['value']
                    
                    # Add or update user in the all_users dictionary
                    if counterparty_id not in all_users:
                        all_users[counterparty_id] = {
                            'display_name': counterparty['display_name'],
                            'type': counterparty['type'],
                            'value': counterparty['value'],
                            'transactions': []
                        }
                    
                    # Add this transaction to the user's transaction list
                    all_users[counterparty_id]['transactions'].append({
                        'id': transaction['id'],
                        'created': transaction['created'],
                        'amount': transaction['amount'],
                        'description': transaction['description']
                    })
                else:
                    transaction['counterparty'] = None
                
                # Add the transaction to our list
                all_transactions.append(transaction)
            
            # Check if there are more pages to fetch
            has_more_pages = pagination_info.has_next_page()
            
            if has_more_pages:
                # Update pagination for the next page
                pagination.older_id = pagination_info.older_id
                
                # Sleep a bit to avoid hitting rate limits
                time.sleep(0.5)
            
        except Exception as e:
            print(f"Error retrieving transactions: {str(e)}")
            break
    
    # Create the result structure
    result = {
        'transactions': all_transactions,
        'users': all_users,
        'summary': {
            'total_transactions': len(all_transactions),
            'unique_users': len(all_users),
            'account_id': primary_account_id
        }
    }
    
    return result


def save_transactions_to_file(transactions_data: Dict[str, Any], filename: str = "transactions_data.json"):
    """
    Save the transactions data to a JSON file.
    
    Args:
        transactions_data: The data returned by get_all_transactions_and_users()
        filename: The name of the file to save the data to
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(transactions_data, f, indent=2, ensure_ascii=False)
        print(f"Transaction data successfully saved to {filename}")
        return True
    except Exception as e:
        print(f"Error saving transaction data: {str(e)}")
        return False


if __name__ == "__main__":
    # If this file is run directly, execute the function and save the results
    transactions_data = get_all_transactions_and_users()
    save_transactions_to_file(transactions_data) 