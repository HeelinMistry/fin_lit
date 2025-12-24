import pandas as pd


def calculate_base_currency_history(account_history):
    """
    Processes an account's monthly history to calculate all values (Balance, Contribution, P&L)
    in the base currency (BC), incorporating exchange rate movements.
    """
    processed_history = []
    sorted_history = sorted(account_history, key=lambda x: x['monthKey'])

    for i, h in enumerate(sorted_history):
        current_rate = h.get('exchangeRate', 1.0)
        opening_rate = current_rate

        # Calculate Base Currency Values
        closing_bc = h['closingBalance'] * current_rate
        opening_bc = h['openingBalance'] * opening_rate
        contribution_bc = h['contribution'] * current_rate  # Contribution valued at current month-end rate

        # Calculate Base Currency Monthly P&L (Growth + Currency Gain/Loss)
        monthly_pnl_bc = closing_bc - opening_bc - contribution_bc

        # Create a record with BC values
        bc_record = h.copy()
        bc_record['closingBalance'] = closing_bc
        bc_record['openingBalance'] = opening_bc
        bc_record['contribution'] = contribution_bc
        bc_record['monthly_pnl_bc'] = monthly_pnl_bc  # New column for P&L

        processed_history.append(bc_record)

    return processed_history


def calculate_growth_surpass_contribution_point(accounts_data, lookback_months=3):
    """
    Calculates the first month (if any) where the **3-Month Rolling Average Cumulative** Profit/Loss (Growth) surpasses the **3-Month Rolling Average Cumulative** Contribution
    for all SAVING accounts combined. This smooths out short-term volatility.

    Args:
        accounts_data (list): A list of account dictionaries.
        lookback_months (int): The window size for the rolling average.

    Returns:
        str or None: The monthKey (YYYY-MM) of the crossover, or None.
    """
    all_records = []

    # 1. Flatten Data and Calculate Monthly P&L (Growth) for SAVING Accounts
    for account in accounts_data:
        if account.get('type') != 'SAVING':
            continue
        bc_history = calculate_base_currency_history(account.get("monthlyHistory", []))
        for history in bc_history:
            record = {'monthKey': history['monthKey'], 'contribution': history['contribution'],
                      'monthly_pnl': history['closingBalance'] - history['openingBalance'] - history['contribution']}
            # P&L (Growth) = Closing - Opening - Contribution
            all_records.append(record)

    if not all_records:
        return None

    df = pd.DataFrame(all_records)
    df['monthKey'] = pd.to_datetime(df['monthKey'])
    df = df.sort_values('monthKey')

    # 2. Aggregate P&L and Contribution by Month Across ALL SAVING Accounts
    monthly_data = df.groupby('monthKey').agg(
        total_pnl=('monthly_pnl', 'sum'),
        total_contribution=('contribution', 'sum')
    ).reset_index()

    # 3. Calculate 3-Month Rolling Averages (Smoothing the inputs)
    # The 'min_periods=1' ensures the first months have a value, even if not a full 3 months
    monthly_data['rolling_pnl'] = monthly_data['total_pnl'].rolling(window=lookback_months, min_periods=1).mean()
    monthly_data['rolling_contribution'] = monthly_data['total_contribution'].rolling(window=lookback_months,
                                                                                      min_periods=1).mean()

    # 4. Calculate Cumulative Metrics using the SMOOTHED data
    monthly_data['cumulative_pnl_smooth'] = monthly_data['rolling_pnl'].cumsum()
    monthly_data['cumulative_contribution_smooth'] = monthly_data['rolling_contribution'].cumsum()

    # 5. Find the Cross-Over Point

    # Identify the rows where smoothed cumulative P&L > smoothed cumulative Contribution
    crossover_df = monthly_data[monthly_data['cumulative_pnl_smooth'] > monthly_data['cumulative_contribution_smooth']]

    if not crossover_df.empty:
        # Get the first month where the condition is met
        crossover_month = crossover_df.iloc[0]['monthKey']
        return crossover_month.strftime("%Y-%m")
    else:
        return None


def calculate_financial_metrics(accounts_data):
    """
    Parses financial data, calculates overall contributions, and the true
    NET Profit/Loss (P&L) by treating SAVING gains as positive and LOAN
    interest costs as negative.
    """
    all_records = []

    for account in accounts_data:
        account_name = account.get('name')
        account_type = account.get('type')
        bc_history = calculate_base_currency_history(account.get("monthlyHistory", []))

        for history in bc_history:
            record = {
                'name': account_name,
                'type': account_type,
                'monthKey': history['monthKey'],
                'openingBalance': history['openingBalance'],
                'contribution': history['contribution'],
                'closingBalance': history['closingBalance']
            }

            if account_type == 'SAVING':
                # SAVING: P&L = Closing - Opening - Contribution
                record['monthly_pnl'] = record['closingBalance'] - record['openingBalance'] - record['contribution']
                record['weighted_pnl'] = record['monthly_pnl']  # Savings P&L is positive
                record['weight'] = 1

            elif account_type == 'LOAN':
                # LOAN: Interest Paid is the cost (P&L for a loan)
                principal_paid = record['openingBalance'] - record['closingBalance']

                # Interest Paid = Contribution - Principal Paid
                # This represents the actual cost of the loan for the month.
                interest_paid = record['contribution'] - principal_paid

                record['monthly_pnl'] = interest_paid
                record['weighted_pnl'] = -interest_paid  # Loan cost is negative P&L
                record['weight'] = -1

            else:
                continue

            all_records.append(record)

    if not all_records:
        return None

    df = pd.DataFrame(all_records)
    df['monthKey'] = pd.to_datetime(df['monthKey'])

    df['weighted_balance'] = df['closingBalance'] * df['weight']
    total_contribution = df['contribution'].sum()
    overall_net_pnl = df['weighted_pnl'].sum()

    latest_close_month = df['monthKey'].max()
    df_latest = df[df['monthKey'] == latest_close_month].copy()

    # Apply the weight: LOAN is negative, SAVING is positive
    df_latest['weighted_balance'] = df_latest.apply(
        lambda row: row['closingBalance'] * (-1 if row['type'] == 'LOAN' else 1), axis=1
    )

    latest_net_balance = df_latest['weighted_balance'].sum()

    # --- 4. Breakdown of Last 3 Months ---

    recent_months = sorted(df['monthKey'].unique(), reverse=True)
    last_three_months = recent_months[:3]
    df_last_3 = df[df['monthKey'].isin(last_three_months)]
    monthly_summary = df_last_3.groupby(df_last_3['monthKey'].dt.to_period('M')).agg(
        total_contribution=('contribution', 'sum'),
        total_net_pnl=('weighted_pnl', 'sum'),  # Use weighted P&L for net performance
        # total_closing_balance is now the aggregated Net Worth for that month
        total_net_balance=('weighted_balance', 'sum')
    ).reset_index()
    monthly_summary['monthKey'] = monthly_summary['monthKey'].astype(str)

    crossover_point = calculate_growth_surpass_contribution_point(accounts_data)

    return {
        'total_contribution': total_contribution,
        'overall_net_pnl': overall_net_pnl,
        'latest_net_balance': latest_net_balance,
        'monthly_summary': monthly_summary,
        'crossover_point': crossover_point  # <--- NEW RETURN VALUE
    }


def format_and_print_metrics(results):
    """
    Formats and prints the financial results, using the combined
    Net P&L and Net Balance from the financial analysis.
    """
    if not results:
        # Adjusted message for clarity when no data is found
        print("\n--- 💰 Financial Analysis Result ---")
        print("No account data (SAVING or LOAN) available for analysis.")
        return

    # --- 1. Overall Summary (Netting Assets and Liabilities) ---
    print("\n--- 💰 Overall Financial Summary ---")

    # Updated keys from the analysis function:
    print(f"Total Cash Flow (Contributions):    {results['total_contribution']:,.2f}")
    print(f"Overall Net Profit/Loss (P&L):      {results['overall_net_pnl']:,.2f}")
    print(f"Current Net Worth (A - L):          {results['latest_net_balance']:,.2f}")
    print("-----------------------------------")

    # --- 2. Last 3 Months Breakdown (Aggregated) ---

    print("\n--- 📅 Last 3 Months Breakdown (Net Aggregation) ---")

    if not results['monthly_summary'].empty:
        summary_df = results['monthly_summary'].rename(columns={
            'monthKey': 'Month',
            'total_contribution': 'Total Cash Flow',  # Renamed for clarity
            'total_net_pnl': 'Net P&L',  # Changed from 'total_pnl'
            'total_net_balance': 'Net Worth (A - L)'  # Changed from 'total_closing_balance'
        })

        # Columns to apply the currency formatting to
        cols_to_format = ['Total Cash Flow', 'Net P&L', 'Net Worth (A - L)']

        # Fix for FutureWarning (using .apply/.map is correct)
        summary_df[cols_to_format] = summary_df[cols_to_format].apply(
            lambda s: s.map(lambda x: f'{x:,.2f}')
        )

        # Print the Markdown table
        print(summary_df.to_markdown(index=False))

        crossover_point = results['crossover_point']
        if crossover_point:
            print(f"Growth > Contribution Crossover:  **{crossover_point}** (Your money works harder!)")

        else:
            print("Growth > Contribution Crossover:  **Not Yet Reached** (Keep contributing!)")

        print("-----------------------------------")
        # A visualization would help the user see the trend:
        print("")
    else:
        print("No monthly history data available for the last three months.")


def summarize_all_accounts(accounts_data):
    """
    Creates a detailed summary of all accounts (SAVING and LOAN),
    showing the latest balance, the latest P&L/Interest Paid, and
    the overall historical P&L/Interest Paid.

    Args:
        accounts_data (list): A list of dictionaries representing accounts.

    Returns:
        pd.DataFrame: A summary table.
    """
    all_latest_records = []

    for account in accounts_data:
        account_name = account.get('name')
        account_type = account.get('type')

        history = account.get('monthlyHistory', [])
        processed_history = calculate_base_currency_history(history)
        if not processed_history:
            continue

        # Find the latest month's history
        # We sort by monthKey to ensure the last item is the most recent (assuming standard YYYY-MM format)
        latest_history = sorted(processed_history, key=lambda x: x['monthKey'])[-1]

        # --- Calculate Latest P&L/Interest Paid ---

        opening_balance = latest_history['openingBalance']
        contribution = latest_history['contribution']
        closing_balance = latest_history['closingBalance']

        # Calculate historical P&L (same approach as calculate_financial_metrics)
        historical_pnl = 0.0

        if account_type == 'SAVING':
            # Latest P&L
            latest_pnl = closing_balance - opening_balance - contribution

            # Overall P&L (Total Change - Total Contributions)
            earliest_opening = processed_history[0].get('openingBalance', 0.0)
            total_contributions = sum(h.get('contribution', 0) for h in processed_history)
            historical_pnl = closing_balance - earliest_opening - total_contributions

            balance_label = "Current Value"
            pnl_label = "Market Gain/Loss"

        elif account_type == 'LOAN':
            # Latest Interest Paid (Cost)
            principal_paid = opening_balance - closing_balance
            latest_pnl = contribution - principal_paid  # Interest Paid (Cost)

            # Overall Historical Interest Paid
            total_principal_paid = opening_balance - closing_balance  # Approximation for single month
            total_contributions = sum(h.get('contribution', 0) for h in processed_history)

            earliest_opening = processed_history[0].get('openingBalance', 0.0)
            latest_closing = processed_history[-1].get('closingBalance', 0.0)

            total_principal_paid_hist = earliest_opening - latest_closing
            historical_pnl = total_contributions - total_principal_paid_hist  # Total Interest Paid

            balance_label = "Debt Balance"
            pnl_label = "Interest Paid (Cost)"

        else:
            continue  # Skip unsupported types

        # Assemble the record
        record = {
            'Account': account_name,
            'Type': account_type,
            'Latest Month': latest_history['monthKey'],
            balance_label: closing_balance,
            f'Latest {pnl_label}': latest_pnl,
            f'Historical {pnl_label}': historical_pnl
        }
        all_latest_records.append(record)

    df = pd.DataFrame(all_latest_records)

    return df


def print_account_summary(summary_df):
    """Formats and prints the detailed account summary."""
    if summary_df.empty:
        print("\n--- 🧾 Detailed Account Summary ---")
        print("No account data found.")
        return

    print("\n--- 🧾 Detailed Account Summary ---")

    # Identify dynamic columns (Current Value/Debt Balance, etc.) for formatting
    cols_to_format = [
        col for col in summary_df.columns
        if any(keyword in col for keyword in ['Value', 'Balance', 'Gain', 'Loss', 'Cost', 'Paid'])
    ]

    # Format the currency columns
    for col in cols_to_format:
        # Use .map to apply currency formatting
        summary_df[col] = summary_df[col].map(lambda x: f'{x:,.2f}' if not pd.isna(x) else '')

    print(summary_df.to_markdown(index=False))