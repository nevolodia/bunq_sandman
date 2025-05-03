
# 🏦 Bunq Sandman 🏦

Bunq Sandman is a powerfull toolset which consists of two parts:

1. **Bunq Sandman History**,
2. **Bunq Sandman Visualizer**.


# 🏦 Bunq Sandman History 🏦

A utility that retrieves data from production or sandbox environment and creates a clone for another sandbox account set, so that algorithms can be safely tested on real cases.
Furhter, it serves as a utility which retrieves data for the web graph platform.

## ✨ Features

### 🔄 Transaction Replay
- **Clone Your Account** - Create a sandbox duplicate of your bunq account provided with the api key
- **Agent Simulation** - Automatically create sandbox accounts for everyone you've interacted with
- **Balance Management** - Intelligently calculate required starting balances for each account
- **Chronological Replay** - Replay all transactions in the correct time sequence

### 💰 Account Management
- **API Context Management** - Efficient storage and retrieval of API contexts
- **Mock Cases Creation** - Create mock cases for testing the system

### 📊 Analysis & Insights
- **Transaction Summary** - Get statistics about your transaction history
- **Balance Requirements** - Calculate minimum balance needs for all accounts

## 🚀 Getting Started

### Basic Usage
1. Run the main script to start the sandbox creation process:
```
python history/main.py
```
2. Follow the interactive prompts to:
   - Create your sandbox account
   - Generate mock transactions (optional)
   - Create agent accounts
   - Request initial balances
   - Replay transactions

3. Run the to_web script to retrieve data for the web graph platform:
```
python history/to_web.py <api_key>
```

## 🧩 How It Works

The system follows this process:

1. **Account Setup** - Creates a sandbox user with conf file, or create a new one if file is not provided
2. **Transaction Analysis** - Reads your transaction history to identify all counterparties
3. **Agent Creation** - Creates sandbox accounts for each person you've interacted with
4. **Balance Calculation** - Determines minimum starting balances for successful transaction replay
5. **Transaction Replay** - Methodically recreates all transactions between accounts

## 📝 API Documentation

### Main Components

#### 🔌 `api.py`
- `create_api_connection()` - Establishes connection to the bunq API
- `create_new_user()` - Creates a new sandbox user with retry logic

#### 🔍 `parse_user.py`
- `get_user_transactions()` - Retrieves transaction history
- `extract_transaction_agents()` - Identifies unique counterparties
- `create_agent_users()` - Creates sandbox users for each counterparty
- `calculate_agent_initial_balances()` - Determines starting balance requirements
- `replay_transactions_chronologically()` - Recreates transactions in time order

#### 📊 `parser.py`
- `to_visualizer_format()` - Formats transaction data for visualization
- `transactions_to_visualizer_format()` - Converts transactions to JSON format

#### 🏃 `main.py`
- Orchestrates the entire process from account setup to transaction replay
- Provides interactive command-line interface

#### 📊 `to_web.py`
- Retrieves data for the web graph platform


## 📝 Limitations

- The system sometimes miscalulates requiered starting balances.
- The system has rare edge cases where action in the replay may be incorrectly interpreted and therefore not executed.
- The system does not handle several accounts of the same user.

