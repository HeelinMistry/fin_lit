import json

from src.api_client import APIClient
from src.data_utils import calculate_net_total

api_client = APIClient()
TEST_USERNAME = "Heelin"

print("--- SCENARIO 1: Attempt Login ---")

# 3. Call the login method
login_response = api_client.login(TEST_USERNAME)

if login_response:
    print("\n--- Login Response Data (Pretty Print) ---")
    print(json.dumps(login_response, indent=4))
    print("------------------------------------------")

    # 4. Scenario: Use the acquired token for a protected resource
    # Assuming the login response contains the user ID
    user_id = login_response.get("data", {}).get("user", {}).get("id")

    if user_id:
        print(f"\n--- SCENARIO 2: Access Protected Profile (User ID: {user_id}) ---")
        profile_response = api_client.get_user_accounts(user_id)
        print("\n--- Full Profile Response Data ---")
        print(json.dumps(profile_response, indent=4))
        print("----------------------------------")

        if profile_response and profile_response.get("success"):
            accounts_data = profile_response.get("data", [])

            # --- NEW LOGIC: Calculate Net Total ---
            net_total, month_key = calculate_net_total(accounts_data)

            print("\n============================================")
            print(f"  NET PORTFOLIO TOTAL ({month_key}): {net_total:,.2f}")
            print("============================================")

        else:
            print("\nSkipping Aggregation: Failed to retrieve profile data.")
    else:
        print("\nSkipping Profile Test: User ID not found in login response.")
else:
    print("\nClient terminated due to failed login or connection error.")