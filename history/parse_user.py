from bunq.sdk.model.generated.endpoint import PaymentApiObject, RequestInquiryApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_context import ApiContext
from bunq import Pagination

from typing import List, Dict, Any
import json
import time
import os

from api import create_new_user


def get_user_transactions() -> List[Dict[str, Any]]:
    """
    Collect all transactions (payments and requests) for the current user.
    
    Returns:
        List of dictionaries containing transaction details
    """
    # Initialize result list
    transactions = []
    
    # Set up pagination
    pagination = Pagination()
    pagination.count = 200
    
    try:
        # Get payments
        payment_response = PaymentApiObject.list(params=pagination.url_params_count_only)
        payments = payment_response.value
        pagination_info = payment_response.pagination
        
        # Process payments
        while True:
            # Process current page
            for payment in payments:
                transaction = {
                    'type': 'PAYMENT',
                    'id': payment.id_,
                    'created': payment.created,
                    'updated': payment.updated,
                    'amount': payment.amount.value,
                    'currency': payment.amount.currency,
                    'description': payment.description,
                    'counterparty_iban': payment.counterparty_alias.label_monetary_account._iban
                }
                transactions.append(transaction)
            
            # Check if there are more pages
            if not pagination_info.has_next_page_assured():
                break
                
            # Fetch next page
            payment_response = PaymentApiObject.list(params=pagination_info.url_params_next_page)
            payments = payment_response.value
            pagination_info = payment_response.pagination
                
    except Exception as e:
        print(f"Error fetching payments: {str(e)}")
    
    # Reset pagination for requests
    pagination = Pagination()
    pagination.count = 200
    
    try:
        # Get requests
        request_response = RequestInquiryApiObject.list(params=pagination.url_params_count_only)
        requests = request_response.value
        pagination_info = request_response.pagination
        
        # Process requests
        while True:
            # Process current page
            for request in requests:
                transaction = {
                    'type': 'REQUEST',
                    'id': request.id_,
                    'created': request.created,
                    'updated': request.updated,
                    'amount': request.amount_inquired.value,
                    'currency': request.amount_inquired.currency,
                    'description': request.description,
                    'status': request.status,
                    'counterparty_iban': request.counterparty_alias.label_monetary_account._iban
                }
                transactions.append(transaction)
            
            # Check if there are more pages
            if not pagination_info.has_next_page_assured():
                break
                
            # Fetch next page
            request_response = RequestInquiryApiObject.list(params=pagination_info.url_params_next_page)
            requests = request_response.value
            pagination_info = request_response.pagination
                
    except Exception as e:
        print(f"Error fetching requests: {str(e)}")
    
    # Sort transactions by creation date (newest first)
    transactions.sort(key=lambda x: x['created'], reverse=True)
    
    return transactions


def extract_transaction_agents(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract unique agents (counterparties) with whom the main user has interacted.
    Focuses exclusively on IBAN identifiers.
    Does not give guarantees on the order of the agents.
    
    Args:
        transactions: List of transaction dictionaries
    
    Returns:
        List of dictionaries containing agent details
    """
    # Track unique agents by IBAN
    agents_by_iban = {}
    
    # Process all transactions
    for transaction in transactions:
        iban = transaction.get('counterparty_iban')
        
        # Skip if no IBAN
        if not iban:
            print(f"Skipping transaction with no IBAN: {transaction}")
            continue
            
        # Track by IBAN
        if iban not in agents_by_iban:
            agents_by_iban[iban] = {
                'iban': iban,
                'transaction_count': 1,
                'transaction_ids': [transaction['id']],
                'total_amount': float(transaction['amount']),
                'first_transaction': transaction['created'],
                'last_transaction': transaction['created']
            }
        # Add agent to list
        else:
            agents_by_iban[iban]['transaction_count'] += 1
            agents_by_iban[iban]['transaction_ids'].append(transaction['id'])
            agents_by_iban[iban]['total_amount'] += float(transaction['amount'])
    
    # Convert to list and sort by transaction count
    agents_list = list(agents_by_iban.values())
    agents_list.sort(key=lambda x: x['transaction_count'], reverse=True)
    
    return agents_list


def create_agent_users(agents: List[Dict[str, Any]], main_user_iban: str, output_dir: str) -> Dict[str, Dict[str, Any]]:
    """
    Create new users for each identified agent (based on IBAN) and 
    store their API contexts in the provided directory.
    
    Uses a pair file to track IBAN-to-user map to avoid creating
    duplicate users for the same IBAN.
    
    Args:
        agents: List of dictionaries containing agent details
        output_dir: Directory to store the new users' API contexts
    
    Returns:
        Dictionary mapping IBANs to new user information
    """
    # Create directory if doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize constants
    pair_file_path = f"{output_dir}/iban_user_pairs.json"
    sandbox_user_url = "https://public-api.sandbox.bunq.com/v1/sandbox-user-person"
    
    # Map of new users to original IBANs
    iban_to_user_map = {}

    # Check if pair file exists
    if os.path.exists(pair_file_path):
        try:
            with open(pair_file_path, 'r') as f:
                iban_to_user_map = json.load(f)
                print(f"Loaded {len(iban_to_user_map)} existing IBAN-user mappings from pair file")
        except Exception as e:
            print(f"Error loading pair file: {str(e)}")
            # Continue with empty mapping if file can't be read
    
    # Create a new user for each agent that's not already in the pair file
    for i, agent in enumerate(agents):
        print(f"Processing agent {i+1} of {len(agents)}")
        iban = agent['iban']
        
        # Skip if already in the mapping
        if iban in iban_to_user_map:
            context_file_path = iban_to_user_map[iban].get('context_file_path')
            if context_file_path and os.path.exists(context_file_path):
                iban_to_user_map[iban]['original_agent'] = agent
                continue
            else:
                # Remove from map since file is missing
                iban_to_user_map.pop(iban, None)
            
        # Create filename with IBAN
        safe_iban = iban.replace(" ", "").replace(".", "_")
        user_filename = f"{output_dir}/agent_{safe_iban}_{i+1}.conf"
        
        try:
            if iban == main_user_iban:
                name = "Main User"
            else:
                name = f"Agent {i+1} - {iban[-4:]}" # Using last 4 digits of IBAN to describe the agent

            # Create a new sandbox user
            print(f"Creating new user for agent with IBAN: {iban}")
            new_user = create_new_user(
                sandbox_user_url,
                user_filename,
                name
            )
            
            if new_user:
                # Load the API context to get the IBAN of the new account
                api_context = ApiContext.restore(new_user['context_file_path'])
                BunqContext.load_api_context(api_context)
                
                # Get the user's monetary account to extract their IBAN
                user_context = BunqContext.user_context()
                new_user_monetary_account = user_context.primary_monetary_account
                
                # Extract the IBAN from the new user
                new_user_iban = None
                for alias in new_user_monetary_account.alias:
                    if alias.type_ == 'IBAN':
                        new_user_iban = alias.value
                        break
                
                is_main_user = (iban == main_user_iban)
                
                # Store mapping from IBAN to new user
                iban_to_user_map[iban] = {
                    'api_key': new_user['api_key'],
                    'context_file_path': new_user['context_file_path'],
                    'iban': iban,
                    'copy_iban': new_user_iban,  # Store the new user's actual IBAN
                    'is_main_user': is_main_user,
                    'original_agent': agent
                }
                print(f"Successfully created user for IBAN {iban} (New account IBAN: {new_user_iban})")
                
                # Save the updated pair file after each successful creation
                try:
                    with open(pair_file_path, 'w') as f:
                        json.dump(iban_to_user_map, f, indent=2)
                except Exception as e:
                    print(f"Error saving pair file: {str(e)}")
            else:
                print(f"Failed to create user for IBAN {iban}")
                
        except Exception as e:
            print(f"Error creating user for IBAN {iban}: {str(e)}")
    
    # Save the final pair file
    try:
        with open(pair_file_path, 'w') as f:
            json.dump(iban_to_user_map, f, indent=2)
        print(f"Saved IBAN-user mappings to {pair_file_path}")
    except Exception as e:
        print(f"Error saving pair file: {str(e)}")
    
    # Print summary
    print(f"\nTotal of {len(iban_to_user_map)} agent users available")
    
    return iban_to_user_map


def calculate_agent_initial_balances(transactions: List[Dict[str, Any]], agents: List[Dict[str, Any]], buffer_amount: float = 1000.0) -> Dict[str, float]:
    """
    Calculate the minimum initial balance each agent needs to have
    to successfully execute all their transactions chronologically.
    
    The algorithm works by:
    1. Sorting all transactions by date (oldest first)
    2. Simulating the flow of money for each agent
    3. Tracking the lowest balance point for each agent
    4. The minimum initial balance is the absolute value of the lowest negative balance
       (or 0 if the balance never goes negative)
    5. Adding a buffer amount to ensure there are no insufficient funds issues
    
    Args:
        transactions: List of transaction dictionaries
        agents: List of agent dictionaries with IBAN identifiers
        buffer_amount: Extra amount to add as a safety margin (default: 100.0)
    
    Returns:
        Dictionary mapping each IBAN to its required minimum initial balance
    """
    # Create maps of: IBAN to agent info, IBAN to agent balances, IBAN to agent min balances
    iban_to_agent = {agent['iban']: agent for agent in agents}
    agent_balances = {agent['iban']: 0.0 for agent in agents}
    agent_min_balances = {agent['iban']: 0.0 for agent in agents}
    
    # Sort transactions by date
    sorted_transactions = sorted(transactions, key=lambda x: x['created'])
    
    # Process transactions
    for transaction in sorted_transactions:
        iban = transaction.get('counterparty_iban')
        if not iban or iban not in iban_to_agent:
            continue
            
        amount = float(transaction['amount'])
        transaction_type = transaction['type']
        
        # Calculate balance
        if transaction_type == 'PAYMENT':
            agent_balances[iban] += amount
        elif transaction_type == 'REQUEST' and transaction.get('status') == 'ACCEPTED':
            agent_balances[iban] -= amount
            
            # Update minimum balance if this creates a new low point
            if agent_balances[iban] < agent_min_balances[iban]:
                agent_min_balances[iban] = agent_balances[iban]
    
    # Calculate required initial balance for each agent
    required_initial_balances = {}
    for iban, min_balance in agent_min_balances.items():
        if min_balance < 0:
            # Add buffer amount to ensure sufficient funds
            required_initial_balances[iban] = abs(min_balance) + buffer_amount
        else:
            # Even for positive balance agents, add a small buffer to avoid issues
            required_initial_balances[iban] = buffer_amount
    
    print(f"Added buffer amount of €{buffer_amount:.2f} to all agent initial balances for safety")
            
    return required_initial_balances


def request_initial_balances(iban_to_user_map: Dict[str, Dict[str, Any]], required_balances: Dict[str, float], sugar_daddy_email: str = "sugardaddy@bunq.com") -> Dict[str, Any]:
    """
    Makes payment requests from each agent account to the sugar daddy account
    for their required initial balance.
    
    Args:
        iban_to_user_map: Dictionary mapping IBANs to user information
        required_balances: Dictionary mapping IBANs to required initial balances
        sugar_daddy_email: Email of the sugar daddy account to request money from
        
    Returns:
        Dictionary with results of the request operations
    """
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    # Current API context to restore later
    original_api_context = None
    if BunqContext.api_context():
        original_api_context = BunqContext.api_context()
    
    # Process each agent
    for iban, user_info in iban_to_user_map.items():
        # Skip if no initial balance required
        if iban not in required_balances or required_balances[iban] <= 0:
            results['skipped'].append({
                'iban': iban,
                'reason': 'No initial balance required'
            })
            continue
            
        # Context file path
        context_path = user_info.get('context_file_path')
        if not context_path or not os.path.exists(context_path):
            results['failed'].append({
                'iban': iban,
                'reason': f'Context file not found: {context_path}'
            })
            continue
            
        try:
            # Load the agent's API context
            api_context = ApiContext.restore(context_path)
            BunqContext.load_api_context(api_context)
            
            # Format the amount with 2 decimal places
            amount = f"{required_balances[iban]:.2f}"
            description = f"Initial balance request for agent with IBAN: {iban}"
            
            # Create a payment request to sugar daddy
            request = RequestInquiryApiObject.create(
                amount_inquired=AmountObject(amount, "EUR"),
                counterparty_alias=PointerObject("EMAIL", sugar_daddy_email, "Sugar Daddy"),
                description=description,
                allow_bunqme=True  # Allow bunq.me payment link
            )
            
            if request and hasattr(request, 'value'):
                results['success'].append({
                    'iban': iban,
                    'request_id': request.value,
                    'amount': amount,
                    'description': description
                })
                print(f"Successfully requested €{amount} from Sugar Daddy for IBAN: {iban}")
            else:
                results['failed'].append({
                    'iban': iban,
                    'reason': 'Request creation failed - no ID returned'
                })
                
        except Exception as e:
            results['failed'].append({
                'iban': iban,
                'reason': str(e)
            })
            print(f"Error creating request for IBAN {iban}: {str(e)}")
            
    # Restore original API context if there was one
    if original_api_context:
        BunqContext.load_api_context(original_api_context)
            
    # Print summary
    print("\n=== INITIAL BALANCE REQUESTS SUMMARY ===")
    print(f"Successful requests: {len(results['success'])}")
    print(f"Failed requests: {len(results['failed'])}")
    print(f"Skipped (no balance needed): {len(results['skipped'])}")
    
    return results


def print_transaction_summary(transactions: List[Dict[str, Any]]) -> None:
    """
    Print a summary of the transactions.
    
    Args:
        transactions: List of transaction dictionaries
    """
    payment_count = sum(1 for t in transactions if t['type'] == 'PAYMENT')
    request_count = sum(1 for t in transactions if t['type'] == 'REQUEST')
    
    print(f"\n=== TRANSACTION SUMMARY ===")
    print(f"Total transactions: {len(transactions)}")
    print(f"Payments: {payment_count}")
    print(f"Requests: {request_count}")
    print("=========================\n")
    
    print("Recent transactions:")
    for i, transaction in enumerate(transactions[:5]):
        if transaction['type'] == 'PAYMENT':
            print(f"{i+1}. PAYMENT: {transaction['amount']} {transaction['currency']} - {transaction['description']}")
        else:
            print(f"{i+1}. REQUEST: {transaction['amount']} {transaction['currency']} - {transaction['description']} ({transaction['status']})")


def print_agent_balance_requirements(required_balances: Dict[str, float]) -> None:
    """
    Print a formatted report of the initial balance requirements for each agent.
    
    Args:
        required_balances: Dictionary mapping IBAN to required initial balance
    """
    print("\n=== AGENT INITIAL BALANCE REQUIREMENTS ===")
    
    if not required_balances:
        print("No agent balance requirements calculated.")
        return
        
    # Sort by required balance (highest first)
    sorted_balances = sorted(required_balances.items(), key=lambda x: x[1], reverse=True)
    
    for iban, balance in sorted_balances:
        if balance > 0:
            print(f"IBAN: {iban} - Required initial balance: €{balance:.2f}")
        else:
            print(f"IBAN: {iban} - No initial balance required (always positive cash flow)")
    print()


def print_agents_summary(agents: List[Dict[str, Any]]) -> None:
    """
    Print a summary of the agents/counterparties.
    
    Args:
        agents: List of agent dictionaries
    """
    print(f"\n=== AGENTS SUMMARY ===")
    print(f"Total unique agents: {len(agents)}")
    print("=======================\n")
    
    if not agents:
        print("No agents found.")
        return
    
    print("Top agents by transaction count:")
    for i, agent in enumerate(agents[:5]):
        print(f"{i+1}. IBAN: {agent['iban']}")
        print(f"   Transactions: {agent['transaction_count']}")
        print(f"   Total amount: {agent['total_amount']:.2f}")
        print(f"   First transaction: {agent['first_transaction']}")
        print(f"   Last transaction: {agent['last_transaction']}")
        print("")


def print_iban_user_mapping(iban_to_user_map: Dict[str, Dict[str, Any]], required_balances: Dict[str, float]) -> None:
    """
    Print a formatted report of the IBAN to user mapping.
    
    Args:
        iban_to_user_map: Dictionary mapping IBANs to user information
        required_balances: Dictionary mapping IBANs to required initial balances
    """
    print("\n=== IBAN TO USER MAPPING ===")
    new_users_count = 0
    existing_users_count = 0
    
    for iban, user_info in iban_to_user_map.items():
        # Check if this is a new or existing path
        context_path = user_info['context_file_path']
        is_new = not os.path.exists(f"users/copy/iban_user_pairs.json.bak") and os.path.exists(context_path)
        
        if is_new:
            new_users_count += 1
            status = "NEWLY CREATED"
        else:
            existing_users_count += 1
            status = "EXISTING USER"
            
        # Get copy IBAN if available
        copy_iban = user_info.get('copy_iban', 'Unknown')
        
        # Display both original and copy IBANs
        print(f"Original IBAN: {iban} ({status})")
        print(f"  Copy IBAN: {copy_iban}")
        print(f"  API Key: {user_info['api_key']}")
        print(f"  Initial balance: €{required_balances.get(iban, 0.0):.2f}")
        print(f"  Is main user: {user_info.get('is_main_user', False)}")
        print("")
    
    print(f"Total users: {len(iban_to_user_map)} (New: {new_users_count}, Existing: {existing_users_count})")


def get_iban_from_context_file(context_file_path: str) -> str:
    """
    Retrieve the IBAN from a bunq API context file.
    
    Args:
        context_file_path: Path to the API context file
        
    Returns:
        The IBAN string if found, otherwise None
    """
    try:
        # Load the API context
        api_context = ApiContext.restore(context_file_path)
        BunqContext.load_api_context(api_context)
        
        # Get the user's monetary account
        user_context = BunqContext.user_context()
        monetary_account = user_context.primary_monetary_account
        
        # Find the IBAN in the aliases - matching how it's done in main.py
        for alias in monetary_account.alias:
            if alias.type_ == 'IBAN':
                return alias.value
                
        # If we can't find an IBAN type specifically, as a fallback
        # look for label_monetary_account._iban
        for alias in monetary_account.alias:
            if hasattr(alias, 'label_monetary_account') and hasattr(alias.label_monetary_account, '_iban'):
                return alias.label_monetary_account._iban
                
        print(f"WARNING: No IBAN found in any aliases for context file {context_file_path}")
        # Debug info to see what aliases are available
        print("Available aliases:")
        for alias in monetary_account.alias:
            print(f"  Type: {alias.type_}, Value: {alias.value}")
            if hasattr(alias, 'label_monetary_account'):
                print(f"    Has label_monetary_account: {alias.label_monetary_account.__dict__}")
            
        return None
    except Exception as e:
        print(f"Error getting IBAN from context file {context_file_path}: {str(e)}")
        return None


def update_agent_copy_ibans(output_dir: str = "users/copy/") -> Dict[str, Dict[str, Any]]:
    """
    Update the copy_iban field for all agent accounts in the iban_user_pairs.json file.
    This is useful when the copy_iban field is missing or showing as 'Unknown'.
    
    Args:
        output_dir: Directory containing the agent API contexts and pair file
        
    Returns:
        Updated iban_to_user_map dictionary
    """
    # Path to the pair file
    pair_file_path = f"{output_dir}/iban_user_pairs.json"
    
    # Check if pair file exists
    if not os.path.exists(pair_file_path):
        print(f"Pair file not found at {pair_file_path}")
        return {}
        
    # Load existing mappings
    try:
        with open(pair_file_path, 'r') as f:
            iban_to_user_map = json.load(f)
            print(f"Loaded {len(iban_to_user_map)} user mappings from pair file")
    except Exception as e:
        print(f"Error loading pair file: {str(e)}")
        return {}
    
    # Save the original API context if there was one
    original_api_context = None
    if BunqContext.api_context():
        original_api_context = BunqContext.api_context()
    
    # Track updated entries
    updated_count = 0
    
    # Update each mapping that doesn't have a copy_iban or has it set to Unknown
    for iban, user_info in iban_to_user_map.items():
        # Skip if copy_iban is already set and not Unknown
        if user_info.get('copy_iban') and user_info.get('copy_iban') != 'Unknown':
            continue
            
        # Get context file path - fix potential path issues
        context_path = user_info.get('context_file_path')
        if context_path and not os.path.exists(context_path):
            # Try prepending "v2/" if not found
            alt_path = f"v2/{context_path}"
            if os.path.exists(alt_path):
                context_path = alt_path
                print(f"Found context file at alternate path: {alt_path}")
        
        if not context_path or not os.path.exists(context_path):
            print(f"Context file not found for IBAN {iban}: {context_path}")
            continue
            
        # Get IBAN from context file - using improved function
        copy_iban = get_iban_from_context_file(context_path)
        if copy_iban:
            user_info['copy_iban'] = copy_iban
            updated_count += 1
            print(f"Updated copy IBAN for {iban}: {copy_iban}")
        else:
            print(f"Could not find IBAN in context file for {iban}")
    
    # Restore original API context if there was one
    if original_api_context:
        BunqContext.load_api_context(original_api_context)
    
    # Save the updated pair file
    if updated_count > 0:
        try:
            with open(pair_file_path, 'w') as f:
                json.dump(iban_to_user_map, f, indent=2)
            print(f"Saved {updated_count} updated IBAN mappings to {pair_file_path}")
        except Exception as e:
            print(f"Error saving pair file: {str(e)}")
    else:
        print("No IBAN mappings were updated")
    
    return iban_to_user_map


def replay_transactions_chronologically(transactions: List[Dict[str, Any]], iban_to_user_map: Dict[str, Dict[str, Any]], main_user_path: str) -> Dict[str, Any]:
    """
    Replay all transactions between users (including the main user) in chronological order.
    
    The function:
    1. Sorts all transactions by date (oldest first)
    2. For each transaction, logs in as the appropriate user (sender)
    3. Creates the payment/request to the appropriate recipient
    4. Maintains a log of all operations
    
    Args:
        transactions: List of transaction dictionaries
        iban_to_user_map: Dictionary mapping IBANs to user information
        main_user_path: Path to the main user's API context file
        
    Returns:
        Dictionary with results of the replay operations
    """
    results = {
        'success': [],
        'failed': [],
        'skipped': []
    }
    
    # Print a summary of what we're working with
    print(f"\n=== TRANSACTION REPLAY INFO ===")
    print(f"Total transactions to replay: {len(transactions)}")
    print(f"Total agent mappings available: {len(iban_to_user_map)}")
    print(f"Main user path: {main_user_path}")
    
    # Create a reverse mapping from copy_iban to original iban for easier lookups
    copy_iban_to_original = {}
    for original_iban, user_info in iban_to_user_map.items():
        copy_iban = user_info.get('copy_iban')
        if copy_iban:
            copy_iban_to_original[copy_iban] = original_iban
    
    print(f"Original IBAN to Copy IBAN mappings:")
    for original_iban, user_info in iban_to_user_map.items():
        print(f"  {original_iban} → {user_info.get('copy_iban', 'Unknown')}")
    
    # Get the main user API context
    try:
        main_api_context = ApiContext.restore(main_user_path)
        
        # Retrieve main user's IBAN using the improved function
        main_user_copy_iban = get_iban_from_context_file(main_user_path)
        
        if not main_user_copy_iban:
            print("ERROR: Could not find IBAN for main user copy")
            return results
        
        print(f"Main user copy IBAN: {main_user_copy_iban}")
    except Exception as e:
        print(f"Error loading main user API context: {str(e)}")
        return results
    
    # Save current API context if any
    original_api_context = None
    if BunqContext.api_context():
        original_api_context = BunqContext.api_context()
    
    # Sort transactions by date (oldest first)
    sorted_transactions = sorted(transactions, key=lambda x: x['created'])
    
    # Process each transaction
    for i, transaction in enumerate(sorted_transactions):
        transaction_type = transaction.get('type')
        original_iban = transaction.get('counterparty_iban')
        transaction_id = transaction.get('id')
        amount_str = transaction.get('amount')
        currency = transaction.get('currency', 'EUR')
        description = transaction.get('description', 'Replayed transaction')
        
        # Skip if no IBAN (can't identify counterparty)
        if not original_iban:
            results['skipped'].append({
                'transaction_id': transaction_id,
                'reason': 'No counterparty IBAN found'
            })
            continue
            
        # Verify this original IBAN is in our map
        if original_iban not in iban_to_user_map:
            results['skipped'].append({
                'transaction_id': transaction_id,
                'reason': f'Original IBAN {original_iban} not found in user map'
            })
            continue
        
        # Get the copy IBAN for this counterparty
        agent_copy_iban = iban_to_user_map[original_iban].get('copy_iban')
        if not agent_copy_iban:
            results['skipped'].append({
                'transaction_id': transaction_id,
                'reason': f'Copy IBAN for {original_iban} not available'
            })
            continue
            
        # Get the context file for this agent - handle path issues
        agent_context_path = iban_to_user_map[original_iban].get('context_file_path')
        if agent_context_path and not os.path.exists(agent_context_path):
            # Try prepending "v2/" if not found
            alt_path = f"v2/{agent_context_path}"
            if os.path.exists(alt_path):
                agent_context_path = alt_path
                print(f"Found context file at alternate path: {alt_path}")
                
        if not agent_context_path or not os.path.exists(agent_context_path):
            results['skipped'].append({
                'transaction_id': transaction_id,
                'reason': f'Context file for {original_iban} not found: {agent_context_path}'
            })
            continue
            
        try:
            # Parse the amount to determine direction
            try:
                # Convert amount to float to check sign
                amount_value = float(amount_str)
                is_negative = amount_value < 0
                # Get absolute amount for the API call (API always requires positive)
                formatted_amount = f"{abs(amount_value):.2f}"
            except (ValueError, TypeError):
                # If conversion fails, log and skip
                results['skipped'].append({
                    'transaction_id': transaction_id,
                    'reason': f'Invalid amount format: {amount_str}'
                })
                print(f"[{i+1}/{len(sorted_transactions)}] Skipping transaction with invalid amount: {amount_str}")
                continue
                
            # Determine transaction direction and setup sender/recipient accordingly
            if transaction_type == 'PAYMENT':
                if is_negative:
                    # Money going OUT from main account (negative amount)
                    # Main user sends money to agent
                    print(f"Payment: Main user → Agent {original_iban}")
                    sender_context = main_api_context
                    recipient_iban = agent_copy_iban
                    recipient_type = "IBAN"
                    sender_name = "Main User"
                    recipient_name = f"Agent {original_iban[-4:]}"
                else:
                    # Money coming IN to main account (positive amount)
                    # Agent sends money to main user
                    print(f"Payment: Agent {original_iban} → Main user")
                    sender_context = ApiContext.restore(agent_context_path)
                    recipient_iban = main_user_copy_iban
                    recipient_type = "IBAN"
                    sender_name = f"Agent {original_iban[-4:]}"
                    recipient_name = "Main User"
            else:  # REQUEST
                # Agent requests money from main user
                print(f"Request: Agent {original_iban} → Main user")
                sender_context = ApiContext.restore(agent_context_path)
                recipient_iban = main_user_copy_iban
                recipient_type = "IBAN"
                sender_name = f"Agent {original_iban[-4:]}"
                recipient_name = "Main User"
            
            # Load the sender's context
            BunqContext.load_api_context(sender_context)
            
            # Create the transaction
            if transaction_type == 'PAYMENT':
                # Create a payment with display_name parameter
                response = PaymentApiObject.create(
                    amount=AmountObject(formatted_amount, currency),
                    counterparty_alias=PointerObject(recipient_type, recipient_iban, recipient_name),
                    description=f"Replay: {description}"
                )
                
                if response and hasattr(response, 'value'):
                    results['success'].append({
                        'original_id': transaction_id,
                        'new_id': response.value,
                        'type': 'PAYMENT',
                        'amount': formatted_amount,
                        'description': description,
                        'from': sender_name,
                        'to': recipient_name,
                        'original_amount': amount_str
                    })
                    print(f"[{i+1}/{len(sorted_transactions)}] Successfully replayed payment of {formatted_amount} {currency} from {sender_name} to {recipient_name}")
                else:
                    raise Exception("Payment creation failed - no ID returned")
                    
            elif transaction_type == 'REQUEST':
                # Create a request with display_name parameter
                response = RequestInquiryApiObject.create(
                    amount_inquired=AmountObject(formatted_amount, currency),
                    counterparty_alias=PointerObject(recipient_type, recipient_iban, recipient_name),
                    description=f"Replay: {description}",
                    allow_bunqme=True
                )
                
                if response and hasattr(response, 'value'):
                    results['success'].append({
                        'original_id': transaction_id,
                        'new_id': response.value,
                        'type': 'REQUEST',
                        'amount': formatted_amount,
                        'description': description,
                        'from': sender_name,
                        'to': recipient_name,
                        'original_amount': amount_str
                    })
                    print(f"[{i+1}/{len(sorted_transactions)}] Successfully replayed request of {formatted_amount} {currency} from {sender_name} to {recipient_name}")
                else:
                    raise Exception("Request creation failed - no ID returned")
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
                
        except Exception as e:
            results['failed'].append({
                'transaction_id': transaction_id,
                'reason': str(e),
                'type': transaction_type,
                'iban': original_iban,
                'amount': amount_str
            })
            print(f"[{i+1}/{len(sorted_transactions)}] Error replaying {transaction_type} for IBAN {original_iban}: {str(e)}")
    
    # Restore original API context if there was one
    if original_api_context:
        BunqContext.load_api_context(original_api_context)
            
    # Print summary
    print("\n=== TRANSACTION REPLAY SUMMARY ===")
    print(f"Successful replays: {len(results['success'])}")
    print(f"Failed replays: {len(results['failed'])}")
    print(f"Skipped transactions: {len(results['skipped'])}")
    
    return results


def print_replay_results(results: Dict[str, Any]) -> None:
    """
    Print detailed results of the transaction replay operations.
    
    Args:
        results: Dictionary with results of the replay operations
    """
    print("\n=== DETAILED REPLAY RESULTS ===")
    
    if results['success']:
        print("\nSUCCESSFUL REPLAYS:")
        for txn in results['success']:
            print(f"Original ID: {txn['original_id']} -> New ID: {txn['new_id']}")
            print(f"  Type: {txn['type']}")
            print(f"  Amount: {txn['amount']}")
            print(f"  Description: {txn['description']}")
            print(f"  From: {txn['from']} -> To: {txn['to']}")
            print()
    
    if results['failed']:
        print("\nFAILED REPLAYS:")
        for txn in results['failed']:
            print(f"Transaction ID: {txn['transaction_id']}")
            print(f"  Type: {txn.get('type', 'Unknown')}")
            print(f"  IBAN: {txn.get('iban', 'Unknown')}")
            print(f"  Reason: {txn['reason']}")
            print()
    
    if results['skipped']:
        print("\nSKIPPED TRANSACTIONS:")
        for txn in results['skipped']:
            print(f"Transaction ID: {txn['transaction_id']}")
            print(f"  Reason: {txn['reason']}")
            print()


def print_request_results(results: Dict[str, Any]) -> None:
    """
    Print detailed results of the request operations.
    
    Args:
        results: Dictionary with results of the request operations
    """
    print("\n=== DETAILED REQUEST RESULTS ===")
    
    if results['success']:
        print("\nSUCCESSFUL REQUESTS:")
        for req in results['success']:
            print(f"IBAN: {req['iban']}")
            print(f"  Request ID: {req['request_id']}")
            print(f"  Amount: €{req['amount']}")
            print(f"  Description: {req['description']}")
            print()
    
    if results['failed']:
        print("\nFAILED REQUESTS:")
        for req in results['failed']:
            print(f"IBAN: {req['iban']}")
            print(f"  Reason: {req['reason']}")
            print()
    
    if results['skipped']:
        print("\nSKIPPED REQUESTS:")
        for req in results['skipped']:
            print(f"IBAN: {req['iban']}")
            print(f"  Reason: {req['reason']}")
            print()

