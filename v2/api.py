from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_context import ApiContext
from bunq import ApiEnvironmentType
import requests
import os


def create_api_connection(environment, api_key, description):
    """
    Create and initialize the bunq API connection.
    
    Returns:
        ApiContext: The initialized bunq API context
    """
    # Create API context
    api_context = ApiContext.create(
        environment,
        api_key,
        description
    )
    
    # Make sure the users directory exists for API context files
    os.makedirs("users", exist_ok=True)
    
    # Save the API context to a file for future use
    api_context.save("users/bunq_api_context.conf")
    
    # Load the API context into the SDK
    BunqContext.load_api_context(api_context)
    
    return api_context


def create_new_user(user_creation_url, description="New User"):
    """
    Create a completely new sandbox user.
    
    Args:
        description (str): Description for the user (not used directly but kept for compatibility)
        
    Returns:
        dict: Information about the newly created user, including its API key
    """
    # Make the API request to create a new sandbox user
    try:
        response = requests.post(
            user_creation_url,
            headers={
                'Content-Type': 'application/json',
                'Cache-Control': 'no-cache',
                'User-Agent': 'bunq-python-sdk'
            }
        )
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse the response
            result = response.json()
            
            if 'Response' in result and len(result['Response']) > 0:
                # Extract API key from response
                api_key = result['Response'][0]['ApiKey']['api_key']
                
                print(f"Successfully created new sandbox user with API key: {api_key}")
                
                # Create a new API context for this user
                new_api_context = ApiContext.create(
                    ApiEnvironmentType.SANDBOX,
                    api_key,
                    f"New User API - {description}"
                )
                
                # Save this API context to a separate file
                new_context_path = f"users/bunq_api_context_new_user_{api_key[-8:]}.conf"
                new_api_context.save(new_context_path)
                
                print(f"Saved new user API context to {new_context_path}")
                
                return {
                    'api_key': api_key,
                    'context_file_path': new_context_path,
                    'api_context': new_api_context
                }
            else:
                print("Failed to parse API key from response")
                print(f"Response: {result}")
                return None
        else:
            print(f"Failed to create sandbox user: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error creating sandbox user: {str(e)}")
        return None

