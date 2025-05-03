from bunq.sdk.context.api_environment_type import ApiEnvironmentType
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_context import ApiContext
import argparse

from parse_user import (
    get_user_transactions, 
    extract_transaction_agents
)

from parser import transactions_to_visualizer_format

def to_web(api_key, sugar_mode=False):
    
    api_context = ApiContext.create(
        ApiEnvironmentType.SANDBOX,
        api_key,
        "bunq api"
    )
    BunqContext.load_api_context(api_context)
    
    # Get transactions of the main user and agents he interacted with
    transactions = get_user_transactions()
    agents = extract_transaction_agents(transactions)
    print(f"Found {len(transactions)} transactions and {len(agents)} agents")

    # Generate data with or without sugar mode enabled
    re = transactions_to_visualizer_format(transactions, agents, sugar_mode=sugar_mode)
    
    if sugar_mode:
        print(f"Data converted to visualizer format with sugar daddy mode ENABLED")
    else:
        print(f"Data converted to visualizer format")

    # save to file
    output_file = "visualizer_data_sugar.json" if sugar_mode else "visualizer_data.json"
    with open(output_file, "w") as f:
        f.write(re)
    print(f"Data saved to {output_file}")

# sandbox_e001b8029b87528aecbb9a238e89f3ea13f2fdb6cc19f662bf6ed0e1

# run from key provided as cmd arg
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert Bunq transactions to visualizer format')
    parser.add_argument('api_key', help='Bunq API key')
    parser.add_argument('-sugar', '--sugar', action='store_true', 
                        help='Enable sugar daddy mode to request money from central authority')
    
    args = parser.parse_args()
    to_web(args.api_key, sugar_mode=args.sugar)

