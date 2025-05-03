from bunq.sdk.model.generated.endpoint import UserApiObject as User
from bunq.sdk.context.bunq_context import BunqContext
from bunq import ApiEnvironmentType
from pprint import pprint
import json
import os

from api import create_api_connection, create_new_user
from process_user import get_all_transactions_and_users, save_transactions_to_file

def main():
    
    # Create and initialize the API connection
    api_context = create_api_connection(
        ApiEnvironmentType.SANDBOX,
        "07d45edfffe208fadebd57358bac7472dd5e8272fd1eec333559e7c57679051a",
        "bunq api"
    )



    

    # Access the user context and get his id
    user_context = BunqContext.user_context()
    user_id = user_context.user_id

    # Retrieve all transactions and users
    print("\n=== RETRIEVING ALL TRANSACTIONS AND USERS ===")
    try:
        # Get all transactions and users
        transactions_data = get_all_transactions_and_users()
        
        # Try to save it
        os.makedirs("transactions", exist_ok=True)
        filename = f"transactions/transactions_{user_id}.json"
        save_transactions_to_file(transactions_data, filename)
    
    except Exception as e:
        print(f"Error processing transactions: {str(e)}")

if __name__ == "__main__":
    main()




