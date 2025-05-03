from bunq.sdk.context.bunq_context import BunqContext
from bunq.sdk.context.api_context import ApiContext
from bunq import ApiEnvironmentType
import requests
import os
import time


def create_api_connection(environment, api_key, description, save_path):
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
    
    # Make sure the dir exists
    dir_path = os.path.dirname(save_path)
    os.makedirs(dir_path, exist_ok=True)
    
    api_context.save(save_path) # Save API context
    BunqContext.load_api_context(api_context) # Load API context
    
    return api_context


def create_new_user(user_creation_url, path_to_save_api_context, description="New User", max_retries=3, retry_delay=5):
    """
    Create a completely new sandbox user with retry logic for rate limiting.
    
    Args:
        user_creation_url (str): URL to create a new sandbox user
        path_to_save_api_context (str): Path to save the API context
        description (str): Description for the user
        max_retries (int): Maximum number of retry attempts on rate limit errors
        retry_delay (int): Delay in seconds between retry attempts
        
    Returns:
        dict: Information about the newly created user, including its API key
    """
    # Check if the context file already exists
    if os.path.exists(path_to_save_api_context):
        try:
            print(f"Context file {path_to_save_api_context} already exists, trying to load it")
            api_context = ApiContext.restore(path_to_save_api_context)
            return {
                'api_key': 'loaded_from_existing_file',
                'context_file_path': path_to_save_api_context,
                'api_context': api_context
            }
        except Exception as e:
            print(f"Failed to load existing context file: {str(e)}")
            print("Will attempt to create a new user")
    
    # Retry logic for API rate limits
    for attempt in range(max_retries):
        try:
            # Make the API request to create a new sandbox user
            response = requests.post(
                user_creation_url,
                headers={
                    'Content-Type': 'application/json',
                    'Cache-Control': 'no-cache',
                    'User-Agent': 'bunq-python-sdk'
                }
            )
            
            # Handle rate limit errors (HTTP 429)
            if response.status_code == 429:
                wait_time = retry_delay * (attempt + 1)
                print(f"Rate limit hit. Waiting {wait_time} seconds before retry... (Attempt {attempt+1}/{max_retries})")
                print(f"Response: {response.text}")
                
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                else:
                    print("Maximum retry attempts reached.")
                    return None
            
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
                    
                    # Make sure the directory exists
                    directory = os.path.dirname(path_to_save_api_context)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                    
                    # Save this API context to a separate file
                    new_api_context.save(path_to_save_api_context)
                    
                    print(f"Saved new user API context to {path_to_save_api_context}")
                    
                    return {
                        'api_key': api_key,
                        'context_file_path': path_to_save_api_context,
                        'api_context': new_api_context
                    }
                else:
                    print("Failed to parse API key from response")
                    print(f"Response: {result}")
                    return None
            else:
                print(f"Failed to create sandbox user: {response.status_code}")
                print(f"Response: {response.text}")
                
                # If it's not a rate limit error, don't retry
                return None
                
        except Exception as e:
            print(f"Error creating sandbox user: {str(e)}")
            
            # For network errors, retry
            if "Connection" in str(e) and attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"Network error. Waiting {wait_time} seconds before retry... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                return None
    
    return None

