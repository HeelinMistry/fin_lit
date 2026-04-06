import datetime
import logging
import math

import numpy as np
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


def calculate_loan_payoff_date(principal, annual_rate, monthly_payment, start_date=None):
    """
    Calculates the number of months required to pay off a loan and the resulting date,
    assuming constant payment and interest rate.

    Args:
        principal (float): The current loan balance (PV).
        annual_rate (float): The loan's annual interest rate (decimal, e.g., 0.0965).
        monthly_payment (float): The constant monthly payment (PMT).
        start_date (datetime.date or None): The date the forecast starts from.

    Returns:
        tuple: (months_to_payoff, payoff_date_string)
    """
    if monthly_payment <= 0:
        return np.inf, "Payment required"

    monthly_rate = annual_rate / 12.0

    if start_date is None:
        start_date = datetime.date.today()

    try:
        if monthly_rate == 0:
            # Simple division if rate is 0
            months_to_payoff = principal / monthly_payment
        else:
            # Safety check: If payment is too low to cover interest (P * r/12), it never pays off
            monthly_interest = principal * monthly_rate
            if monthly_payment <= monthly_interest:
                return np.inf, "Interest not covered"

            # Amortization Formula for Number of Periods (n)
            # P = principal, r = monthly_rate, C = monthly_payment
            numerator = math.log(monthly_payment / (monthly_payment - principal * monthly_rate))
            denominator = math.log(1 + monthly_rate)
            months_to_payoff = numerator / denominator

        # Round up to the next full month
        months_to_payoff = int(np.ceil(months_to_payoff))

        # Calculate Payoff Date
        payoff_date = start_date + datetime.timedelta(days=30 * months_to_payoff)
        payoff_date_string = payoff_date.strftime("%Y-%m")

        return months_to_payoff, payoff_date_string

    except ValueError:
        # math.log(negative number) occurs if payment C is insufficient
        return np.inf, "Interest not covered"
    except ZeroDivisionError:
        return np.inf, "Zero Rate Error"

def get_rolling_average_inputs(account_data, lookback_months=3):
    """
    Calculates the rolling MEDIAN of the annual rate and contribution
    over the last N months for a single account. Using median is more robust
    to outliers than mean for forecasting.

    Args:
        account_data (dict): A single account dictionary object.
        lookback_months (int | None): The number of recent months to average over.
                                      If None or 0, uses all months.
    Returns:
        dict: A dictionary containing the median rate and contribution.
    """
    history = account_data.get('monthlyHistory', [])
    account_type = account_data.get('type')
    processed_history = calculate_base_currency_history(history)
    if not processed_history:
        logging.info(f"Account '{account_data.get('name', 'Unknown')}' has no processed history. Returning zeros.")
        return {'avg_rate': 0.0, 'avg_contribution': 0.0, 'avg_monthly_pnl_currency': 0.0}

    df = pd.DataFrame(processed_history)

    if df.empty:
        logging.info(
            f"Account '{account_data.get('name', 'Unknown')}' has empty DataFrame after processing. Returning zeros.")
        return {'avg_rate': 0.0, 'avg_contribution': 0.0, 'avg_monthly_pnl_currency': 0.0}

    # Prepare DataFrame: Sort and select lookback window
    df['monthKey'] = pd.to_datetime(df['monthKey'], format='%Y-%m')
    df = df.sort_values(by='monthKey', ascending=False)
    if lookback_months is None or lookback_months <= 0:
        # If None or <= 0, use ALL months (df contains all, as it's sorted)
        df_lookback = df.copy()
        actual_lookback_used = len(df_lookback)
        logging.debug(
            f"Using ALL {actual_lookback_used} months for median calculation (lookback set to {lookback_months}).")
    else:
        # If a number > 0, use the specified number of months
        df_lookback = df.head(lookback_months).copy()
        actual_lookback_used = len(df_lookback)
        logging.debug(
            f"Using the last {actual_lookback_used} months for median calculation (lookback set to {lookback_months}).")

    if df_lookback.empty:
        return {'avg_rate': 0.0, 'avg_contribution': 0.0, 'avg_monthly_pnl_currency': 0.0}

    # 1. Calculate Median Monthly Contribution (PMT)
    # Median is more robust for forecasting as it ignores one-off large contributions.
    avg_contribution = df_lookback['contribution'].median()

    # 2. Determine Rate based on Account Type
    avg_rate = 0.0
    avg_pnl_currency = 0.0

    if account_type == 'SAVING':
        # Calculate individual monthly rates to find the median interest rate.
        opening_bal = df_lookback['openingBalance'].values
        closing_bal = df_lookback['closingBalance'].values
        pnl = df_lookback['monthly_pnl_bc'].values

        # Calculate rate safely to avoid division by zero warnings
        monthly_rates = np.divide(pnl, opening_bal, out=np.zeros_like(pnl), where=opening_bal > 0)
        # For months where opening balance was 0, try using closing balance
        zero_opening_mask = (opening_bal <= 0) & (closing_bal > 0)
        if np.any(zero_opening_mask):
            monthly_rates[zero_opening_mask] = pnl[zero_opening_mask] / closing_bal[zero_opening_mask]

        avg_monthly_rate = np.median(monthly_rates)
        avg_rate = avg_monthly_rate * 12.0
        avg_pnl_currency = df_lookback['monthly_pnl_bc'].median()

    elif account_type == 'LOAN':
        original_df = pd.DataFrame(history)
        original_df['monthKey'] = pd.to_datetime(original_df['monthKey'], format='%Y-%m')
        # Slicing the original data to match the determined lookback period
        lookback_months_list = df_lookback['monthKey'].dt.strftime('%Y-%m').unique()
        original_df['monthKey_str'] = original_df['monthKey'].dt.strftime('%Y-%m')
        df_loan_lookback = original_df[original_df['monthKey_str'].isin(lookback_months_list)].copy()

        if 'interestRate' in df_loan_lookback.columns:
            # Using median interest rate for loans
            avg_rate = df_loan_lookback['interestRate'].median()
        else:
            avg_rate = 0.0

    return {
        'avg_rate': avg_rate if account_type == 'SAVING' else avg_rate / 100.0,
        'avg_contribution': avg_contribution,
        'avg_monthly_pnl_currency': avg_pnl_currency
    }

def calculate_simple_projection(current_balance, annual_rate, monthly_payment, months_to_project):
    """
    Projects the future balance of a single account using monthly compounding.
    """
    if months_to_project <= 0:
        return current_balance

    # Monthly rate (r)
    monthly_rate = annual_rate / 12.0

    # Part 1: Future Value of the Current Balance (PV)
    future_value_of_pv = current_balance * np.power((1 + monthly_rate), months_to_project)

    # Part 2: Future Value of the Monthly Payments (PMT)
    if monthly_rate == 0:
        future_value_of_pmt = monthly_payment * months_to_project
    else:
        future_value_of_pmt = monthly_payment * ((np.power((1 + monthly_rate), months_to_project) - 1) / monthly_rate)

    return future_value_of_pv + future_value_of_pmt


def run_net_worth_forecast(accounts_data, forecast_years=10, lookback_months=3):
    """
    Runs a net worth forecast by projecting the future balance for each account.
    """
    months_to_project = forecast_years * 12
    projected_net_worth = 0.0
    projection_details = []
    
    # Get the start date for the forecast
    latest_month_key = None
    for account in accounts_data:
        if account.get('monthlyHistory'):
            current_account_latest_key = sorted(account['monthlyHistory'], key=lambda x: x['monthKey'])[-1]['monthKey']
            if latest_month_key is None or current_account_latest_key > latest_month_key:
                latest_month_key = current_account_latest_key
    
    if latest_month_key:
        latest_date = datetime.datetime.strptime(latest_month_key, "%Y-%m").date()
        start_date = latest_date.replace(day=1) + datetime.timedelta(days=32)
        start_date = start_date.replace(day=1)
    else:
        start_date = datetime.date.today().replace(day=1)

    for account in accounts_data:
        account_type = account.get('type')
        account_name = account.get('name')

        history = account.get('monthlyHistory', [])
        processed_history = calculate_base_currency_history(history)
        if not processed_history:
           continue
        latest_history = sorted(processed_history, key=lambda x: x['monthKey'])[-1]
        current_balance = latest_history['closingBalance']

        if current_balance <= 0.0:
            continue

        avg_inputs = get_rolling_average_inputs(account, lookback_months=lookback_months)
        historical_rate = avg_inputs['avg_rate']
        monthly_payment_raw = avg_inputs['avg_contribution']

        rate = 0.0
        projected_balance = 0.0
        months_to_payoff = 0.0
        payoff_date_str = 'N/A'

        if account_type == 'SAVING':
            rate = historical_rate
            
            # TFSA / ISA logic: These have annual caps. Projecting a rolling monthly
            # average for 10 years would be inaccurate if the cap is hit early.
            # We treat these as growth-only (compounding existing P&L).
            if "TFSA" in account_name.upper():
                monthly_payment = 0.0
                logging.debug(f"Account '{account_name}' identified as TFSA. Ignoring contributions for long-term projection.")
            else:
                monthly_payment = monthly_payment_raw 

            projected_balance = calculate_simple_projection(
                current_balance, rate, monthly_payment, months_to_project
            )
            projected_net_worth += projected_balance

        elif account_type == 'LOAN':
            rate = historical_rate 
            monthly_payment = -monthly_payment_raw 

            months_to_payoff, payoff_date_str = calculate_loan_payoff_date(
                principal=current_balance,
                annual_rate=rate,
                monthly_payment=abs(monthly_payment),
                start_date=start_date
            )

            if months_to_payoff <= months_to_project:
                projected_balance = 0.0
            else:
                projected_balance = calculate_simple_projection(
                    current_balance, rate, monthly_payment, months_to_project
                )

            projected_balance = max(0.0, projected_balance)
            projected_net_worth -= projected_balance

        projection_details.append({
            'Account': account_name,
            'Type': account_type,
            'Current Balance': current_balance,
            f'{forecast_years} Year Projection': projected_balance,
            'Annual Rate Used': rate,
            'Months to Payoff': months_to_payoff,
            'Payoff Date': payoff_date_str
        })

    return {
        'forecast_years': forecast_years,
        'lookback_months': lookback_months,
        'projected_net_worth': projected_net_worth,
        'projection_details': projection_details
    }


def format_and_print_forecast(forecast_results):
    """Formats and prints the results of the net worth forecast."""

    if not forecast_results['projection_details']:
        logging.info(f"\n--- 🔮 Financial Forecast ---")
        logging.info("No account data available for projection.")
        return

    forecast_years = forecast_results['forecast_years']
    lookback_months = forecast_results.get('lookback_months', 3) 

    # --- Overall Summary ---
    logging.info(f"\n--- 🔮 {forecast_years} Year Financial Forecast Summary ---")
    logging.info(f"\n--- using {lookback_months}-month rolling median for rates and contributions ---")
    logging.info(f"Projected Net Worth in {forecast_years} Years: {forecast_results['projected_net_worth']:,.2f}")
    logging.info("-----------------------------------------------------")

    # --- Detail Table ---
    df = pd.DataFrame(forecast_results['projection_details'])

    # Formatting for display
    df['Annual Rate Used'] = df['Annual Rate Used'].map(lambda x: f'{x:,.2%}')
    df['Current Balance'] = df['Current Balance'].map(lambda x: f'{x:,.2f}')
    df[f'{forecast_years} Year Projection'] = df[f'{forecast_years} Year Projection'].map(lambda x: f'{x:,.2f}')

    logging.info("\n--- Account-by-Account Projection ---")
    logging.info(df.to_markdown(index=False))


def summarize_latest_month_from_data(accounts_data):
    """
    Calculates and prints the Net Contribution and Market Gain/Loss
    for the latest month across all accounts using existing keys:
    'contribution', 'openingBalance', and 'closingBalance'.
    """
    if not accounts_data:
        logging.info("Error: The account data list is empty.")
        return

    latest_month_key = None
    net_contribution = 0.0
    total_pl = 0.0

    # 1. First Pass: Find the single latest 'monthKey' across ALL accounts
    for account in accounts_data:
        history = account.get('monthlyHistory', [])
        if history:
            current_account_latest_key = sorted(history, key=lambda x: x['monthKey'])[-1]['monthKey']
            if latest_month_key is None or current_account_latest_key > latest_month_key:
                latest_month_key = current_account_latest_key

    if not latest_month_key:
        logging.info("No historical data found in any account to summarize.")
        return

    try:
        latest_date = datetime.datetime.strptime(latest_month_key, "%Y-%m").date()
        month_str = latest_date.strftime('%B %Y')
    except ValueError:
        month_str = latest_month_key

    for account in accounts_data:
        history = account.get('monthlyHistory', [])
        latest_record = next((d for d in history if d.get('monthKey') == latest_month_key), None)

        if latest_record:
            closing_balance = latest_record.get('closingBalance', 0.0)
            opening_balance = latest_record.get('openingBalance', 0.0)
            contribution = latest_record.get('contribution', 0.0)
            account_type = account.get('type')

            if account_type == 'LOAN':
                monthly_cashflow = -contribution
            else:
                monthly_cashflow = contribution

            monthly_pl = closing_balance - opening_balance - contribution

            if account_type == 'LOAN':
                monthly_pl = -monthly_pl

            net_contribution += monthly_cashflow
            total_pl += monthly_pl

    logging.info(f"\n--- 💰 Financial Summary for the Latest Month: {month_str} ---")
    net_contribution_fmt = f"{net_contribution:,.2f}"
    total_pl_fmt = f"{total_pl:,.2f}"
    logging.info(f"| Net Contribution (Your Cash Flow): {' ' * (28 - len(net_contribution_fmt))} {net_contribution_fmt}")
    logging.info(f"| Net Market Gain / (Loss) (Interest/Return): {' ' * (18 - len(total_pl_fmt))} {total_pl_fmt}")

    net_change = net_contribution + total_pl
    net_change_fmt = f"{net_change:,.2f}"

    if net_change < 0:
        logging.info(f"\n⚠️ WARNING: Overall Net Worth DECREASED by {net_change_fmt}.")
    else:
        logging.info(f"\n✅ GROWTH: Overall Net Worth INCREASED by {net_change_fmt}.")
