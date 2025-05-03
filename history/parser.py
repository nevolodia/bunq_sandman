from typing import List, Dict, Any
import json
import time
from datetime import datetime

def to_visualizer_format(transactions: List[Dict[str, Any]], agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Convert transactions and agents into a format suitable for visualization.
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
            
            # Get transaction ID or use default (0)
            # Convert to integer since the schema expects an integer
            request_id = int(transaction.get('id', 0))
            
            # Properly convert counterparty_id to integer if it's a numeric string
            counterparty_id_int = int(counterparty_id) if counterparty_id.isdigit() else 0
            
            visualization_data.append({
                "action_type": "RequestPayment",
                "user_id": user_id,
                "account_id": "0",
                "monetary_account_id": "0",
                "amount_value": float(transaction['amount']),
                "amount_currency": transaction['currency'],
                "counterparty_iban": transaction.get('counterparty_iban', "NL00BUNQ0000000000"),
                "counterparty_account_id": counterparty_id,
                "expiry_date": expiry_timestamp,
                "request_response_id": request_id
            })
            
            # Add a response if status is available
            if 'status' in transaction:
                status = "ACCEPTED" if transaction['status'] == "ACCEPTED" else "REJECTED"
                visualization_data.append({
                    "action_type": "RespondToPaymentRequest",
                    "user_id": user_id,
                    "account_id": "0",
                    "monetary_account_id": "0",
                    "request_response_id": int(transaction['id']),
                    "status": status,
                    "counterparty_account_id": counterparty_id_int  # Properly converted to integer
                })
    
    return visualization_data

def transactions_to_visualizer_format(transactions: List[Dict[str, Any]], agents: List[Dict[str, Any]]) -> str:
    """
    Convert transactions and agents into a string format suitable for visualization.
    """
    visualization_data = to_visualizer_format(transactions, agents)
    return json.dumps(visualization_data, indent=2) 