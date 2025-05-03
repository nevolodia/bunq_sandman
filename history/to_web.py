from bunq.sdk.context.api_environment_type import ApiEnvironmentType
from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_context import ApiContext

from parse_user import (
    get_user_transactions, 
    extract_transaction_agents
)

from parser import transactions_to_visualizer_format

def to_web(api_key):
    
    api_context = ApiContext.create(
        ApiEnvironmentType.SANDBOX,
        api_key,
        "bunq api"
    )
    BunqContext.load_api_context(api_context)
    
    # Get transactions of the main user and agents he interacted with
    transactions = get_user_transactions()
    agents = extract_transaction_agents(transactions)

    re = transactions_to_visualizer_format(transactions, agents)
    # save to file
    with open("visualizer_data.json", "w") as f:
        f.write(re)

# sandbox_e001b8029b87528aecbb9a238e89f3ea13f2fdb6cc19f662bf6ed0e1

# run from key provided as cmd arg
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python to_web.py <api_key>")
        sys.exit(1)
    to_web(sys.argv[1])

