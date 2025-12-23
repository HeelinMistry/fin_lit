import json

from src.api_client import APIClient
from src.financial_analysis import *
from src.financial_forecast import *

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
            analysis_results = calculate_financial_metrics(accounts_data)
            format_and_print_metrics(analysis_results)

            account_summary_df = summarize_all_accounts(accounts_data)
            print_account_summary(account_summary_df)

            print("\n" + "=" * 50)
            print("RUNNING FINANCIAL FORECAST...")
            print("=" * 50)

            # Set your desired parameters (e.g., 10 years, 8% savings return, 9.65% loan cost)
            forecast_results = run_net_worth_forecast(
                accounts_data,
                forecast_years=10
            )

            format_and_print_forecast(forecast_results)

        else:
            print("\nSkipping Aggregation: Failed to retrieve profile data.")
    else:
        print("\nSkipping Profile Test: User ID not found in login response.")
else:
    print("\nClient terminated due to failed login or connection error.")