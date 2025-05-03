from typing import List, Dict, Any
import json
import time
from datetime import datetime

def to_visualizer_format(transactions: List[Dict[str, Any]], agents: List[Dict[str, Any]], sugar_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Convert transactions and agents into a format suitable for visualization.
    
    Args:
        transactions: List of transaction dictionaries
        agents: List of agent dictionaries
        sugar_mode: If True, enables sugar daddy mode where certain transactions 
                   will be requested from the central authority
    """
    visualization_data = []
    
    # Create User actions for all agents
    for idx, agent in enumerate(agents):
        # Create user person action
        visualization_data.append({
            "action_type": "CreateUserPerson",
            "user_id": idx
        })
        
        # Create monetary account action
        visualization_data.append({
            "action_type": "CreateMonetaryAccount",
            "user_id": idx,
            "account_id": "0",
            "currency": "EUR",
            "daily_limit_value": 5000.0
        })
        
        # Get account overview action
        visualization_data.append({
            "action_type": "GetAccountOverview",
            "account_id": "0",
            "monetary_account_id": "0"
        })
        
        # If sugar mode is enabled, request initial funds from sugar daddy
        if sugar_mode:
            # Generate a random request amount based on agent index
            request_amount = (idx + 1) * 50.0
            
            # Add sugar daddy request
            visualization_data.append({
                "action_type": "RequestPayment",
                "user_id": idx,
                "account_id": "0",
                "monetary_account_id": "0",
                "amount_value": request_amount,
                "amount_currency": "EUR",
                "counterparty_account_id": "sugardaddy",  # Special identifier for sugar daddy
                "description": f"Initial funds request for agent {idx}",
                "expiry_date": int(time.time()) + 604800,  # 1 week expiry
                "request_response_id": int(time.time())  # Use timestamp as unique ID
            })
    
    # Process all transactions
    for transaction in transactions:
        if transaction['type'] == 'PAYMENT':
            user_id = 0  # Default user
            counterparty_id = "1"  # Default counterparty
            
            visualization_data.append({
                "action_type": "MakePayment",
                "user_id": user_id,
                "account_id": "0",
                "monetary_account_id": "0",
                "amount_value": float(transaction['amount']),
                "amount_currency": transaction['currency'],
                "counterparty_iban": transaction.get('counterparty_iban', "NL00BUNQ0000000000"),
                "counterparty_account_id": counterparty_id
            })
            
            # Add a ListPayments action
            visualization_data.append({
                "action_type": "ListPayments",
                "user_id": user_id,
                "account_id": "0",
                "monetary_account_id": "0"
            })
            
        elif transaction['type'] == 'REQUEST':
            user_id = 0  # Default user
            counterparty_id = "1"  # Default counterparty
            
            # Get expiry timestamp (1 week from now)
            expiry_timestamp = int(time.time()) + 604800
            
            # Get transaction ID - RequestPayment needs an integer request_response_id
            request_id = int(transaction.get('id', 0))
            
            # If sugar mode is enabled and amount is above threshold, request from sugar daddy instead
            target_counterparty_id = counterparty_id
            if sugar_mode and float(transaction['amount']) > 100.0:
                target_counterparty_id = "sugardaddy"
            
            visualization_data.append({
                "action_type": "RequestPayment",
                "user_id": user_id,
                "account_id": "0",
                "monetary_account_id": "0",
                "amount_value": float(transaction['amount']),
                "amount_currency": transaction['currency'],
                "counterparty_iban": transaction.get('counterparty_iban', "NL00BUNQ0000000000"),
                "counterparty_account_id": target_counterparty_id,
                "expiry_date": expiry_timestamp,
                "request_response_id": request_id  # Integer for RequestPayment
            })
            
            # Add a response if status is available
            if 'status' in transaction:
                status = "ACCEPTED" if transaction['status'] == "ACCEPTED" else "REJECTED"
                visualization_data.append({
                    "action_type": "RespondToPaymentRequest",
                    "user_id": user_id,
                    "account_id": "0",
                    "monetary_account_id": "0",
                    "request_response_id": int(transaction['id']),  # Integer for request_response_id
                    "status": status,
                    "counterparty_account_id": counterparty_id  # String for counterparty_account_id
                })
    
    return visualization_data

def transactions_to_visualizer_format(transactions: List[Dict[str, Any]], agents: List[Dict[str, Any]], sugar_mode: bool = False) -> str:
    """
    Convert transactions and agents into a string format suitable for visualization.
    
    Args:
        transactions: List of transaction dictionaries
        agents: List of agent dictionaries
        sugar_mode: If True, enables sugar daddy mode where certain transactions 
                   will be requested from the central authority
    """
    visualization_data = to_visualizer_format(transactions, agents, sugar_mode)
    return json.dumps(visualization_data, indent=2) 