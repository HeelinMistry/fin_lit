import datetime


def get_previous_month_key():
    """Calculates the YYYY-MM key for the previous month."""
    # Get today's date
    today = datetime.date.today()

    # Calculate the previous month (by subtracting 1 day and then formatting)
    # This correctly handles year transitions (Jan 1 -> Dec 31)
    first_of_month = today.replace(day=1)
    last_day_of_previous_month = first_of_month - datetime.timedelta(days=1)

    return last_day_of_previous_month.strftime("%Y-%m")


def calculate_net_total(accounts_data):
    """
    Calculates the net total closing balance across all accounts for the previous month.
    """
    target_month_key = get_previous_month_key()

    net_total_balance = 0.0

    print(f"\n--- Aggregating Total for Month: {target_month_key} ---")

    # 2. Iterate through all accounts
    for account in accounts_data:
        account_id = account.get("id")
        account_name = account.get("name")

        # 3. Search the monthlyHistory for the target month
        monthly_history = account.get("monthlyHistory", [])

        target_record = next(
            (m for m in monthly_history if m["monthKey"] == target_month_key),
            None
        )

        if target_record:
            closing_balance = target_record.get("closingBalance", 0.0)
            net_total_balance += closing_balance
            print(f"  ✅ {account_name}: Closing Balance = {closing_balance:,.2f}")
        else:
            print(f"  ⚠️ {account_name} ({account_id}): Record for {target_month_key} not found.")

    return net_total_balance, target_month_key