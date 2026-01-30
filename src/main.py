import json

from src.api_client import APIClient
from src.financial_analysis import *
from src.financial_forecast import *
from src.financial_logger import *

setup_user_output()

api_client = APIClient()
TEST_USERNAME = "Heelin"

print("--- SCENARIO 1: Attempt Login ---")

# 3. Call the login method
login_response = api_client.login(TEST_USERNAME)

if login_response:
    print("\n--- Login Response Data (Pretty Print) ---")
    print(json.dumps(login_response, indent=4))
    print("------------------------------------------")

    if api_client.auth_token:
        print(f"\n--- SCENARIO 2: Access Protected Profile ---")
        profile_response = api_client.get_user_accounts()
        print("\n--- Full Profile Response Data ---")
        print(json.dumps(profile_response, indent=4))
        print("----------------------------------")

        if profile_response and profile_response.get("success"):
            accounts_data = profile_response.get("data", [])
            analysis_results = calculate_financial_metrics(accounts_data)
            format_and_print_metrics(analysis_results)

            account_summary_df = summarize_all_accounts(accounts_data)
            format_and_print_account_summary(account_summary_df)

            summarize_latest_month_from_data(accounts_data)

            forecast_results = run_net_worth_forecast(accounts_data, forecast_years=5, lookback_months=1)
            format_and_print_forecast(forecast_results)

            forecast_results = run_net_worth_forecast(accounts_data, forecast_years=5, lookback_months=3)
            format_and_print_forecast(forecast_results)

            forecast_results = run_net_worth_forecast(accounts_data, forecast_years=5, lookback_months=5)
            format_and_print_forecast(forecast_results)

        else:
            print("\nSkipping Aggregation: Failed to retrieve profile data.")
    else:
        print("\nSkipping Profile Test: User ID not found in login response.")
else:
    print("\nClient terminated due to failed login or connection error.")
