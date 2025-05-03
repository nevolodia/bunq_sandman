from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_context import ApiContext

import shutil
import os

from mock_transactions import generate_mock_transactions
from api import create_new_user
from parse_user import (
    get_user_transactions, 
    extract_transaction_agents, 
    create_agent_users,
    calculate_agent_initial_balances,
    print_agent_balance_requirements,
    request_initial_balances,
    print_iban_user_mapping,
    replay_transactions_chronologically,
    print_replay_results
)

from parser import transactions_to_visualizer_format

def main():
    # Try to load main user, or create it if no main file exists
    main_user_path = "users/main_user.conf"
    if not os.path.exists(main_user_path):
        new_user = create_new_user("https://public-api.sandbox.bunq.com/v1/sandbox-user-person", main_user_path, "Main User")
        if new_user is None:
            print("Failed to create new user. Please try again later.")
            return
        api_context = new_user['api_context']
    else:
        try:
            api_context = ApiContext.restore(main_user_path)
        except Exception as e:
            print(f"Error loading main user API context: {str(e)}")
            print("Try deleting the main_user.conf file and running again.")
            return
            
    BunqContext.load_api_context(api_context)

    # Get user context and print his balance
    user_context = BunqContext.user_context()

    # Extract IBAN from primary monetary account aliases
    main_user_iban = None
    for alias in user_context.primary_monetary_account.alias:
        if alias.type_ == 'IBAN':
            main_user_iban = alias.value
            break
    
    if main_user_iban:
        print(f"Main user IBAN: {main_user_iban}")
    else:
        print("Warning: Could not find IBAN for main user")
        return
        
    print(f"Current balance: {user_context.primary_monetary_account.balance.value}")

    # Ask if user want to create mock transactions
    make_mock_transactions = input(">> Do you want to make mock transactions? (y/n): ").strip()
    if make_mock_transactions == "y":
        generate_mock_transactions()
    
    # Get transactions of the main user and agents he interacted with
    transactions = get_user_transactions()
    agents = extract_transaction_agents(transactions)

    # Calculate minimum initial balances for each agent
    required_balances = calculate_agent_initial_balances(transactions, agents)
    print_agent_balance_requirements(required_balances)
    
    # Ask user if they want to create agent users (proceed)
    create_agents = input(">> Do you want to create agent users for each IBAN? (y/n): ").strip()
    if create_agents != "y":
        print("Exiting...")
        return
    
    # Gets map of created new users to original IBANs
    iban_to_user_map = create_agent_users(agents, main_user_iban, "users/copy/")
    
    # Print the mapping
    print_iban_user_mapping(iban_to_user_map, required_balances)
        
    # Create a backup of the pair file
    pair_file = "users/copy/iban_user_pairs.json"
    if os.path.exists(pair_file) and not os.path.exists(f"{pair_file}.bak"):
        try:
            shutil.copy2(pair_file, f"{pair_file}.bak")
            print(f"Created backup of pair file: {pair_file}.bak")
        except Exception as e:
            print(f"Failed to create backup: {str(e)}")
    
    # Ask user if they want to request initial balances
    request_balances = input(">> Do you want to request initial balances from Sugar Daddy? (y/n): ").strip()
    if request_balances == "y":
        # Make the requests and print the results
        request_initial_balances(iban_to_user_map, required_balances, "sugardaddy@bunq.com")
    
    # Ask user if they want to replay transactions chronologically
    replay_transactions = input(">> Do you want to replay transactions? (y/n): ").strip()
    if replay_transactions != "y":
        print("Exiting...")
        return

    # Replay the transactions and print the results
    replay_results = replay_transactions_chronologically(transactions, iban_to_user_map, main_user_path)
    print_replay_results(replay_results)

if __name__ == "__main__":
    main()
