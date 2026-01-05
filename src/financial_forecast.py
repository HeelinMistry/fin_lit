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
    Calculates the rolling average of the annual rate and contribution
    over the last N months for a single account. If lookback_months is
    None or <= 0, the average is calculated over ALL available history.
    Args:
        account_data (dict): A single account dictionary object.
        lookback_months (int | None): The number of recent months to average over.
                                      If None or 0, uses all months.
    Returns:
        dict: A dictionary containing the average rate and contribution.
    """
    history = account_data.get('monthlyHistory', [])
    account_type = account_data.get('type')
    processed_history = calculate_base_currency_history(history)
    if not processed_history:
        logging.info(f"Account '{account_data.get('name', 'Unknown')}' has no processed history. Returning zeros.")
        return {'avg_rate': 0.0, 'avg_contribution': 0.0}

    df = pd.DataFrame(processed_history)

    if df.empty:
        logging.info(
            f"Account '{account_data.get('name', 'Unknown')}' has empty DataFrame after processing. Returning zeros.")
        return {'avg_rate': 0.0, 'avg_contribution': 0.0}

    # Prepare DataFrame: Sort and select lookback window
    df['monthKey'] = pd.to_datetime(df['monthKey'], format='%Y-%m')
    df = df.sort_values(by='monthKey', ascending=False)
    if lookback_months is None or lookback_months <= 0:
        # If None or <= 0, use ALL months (df contains all, as it's sorted)
        df_lookback = df.copy()
        actual_lookback_used = len(df_lookback)
        logging.debug(
            f"Using ALL {actual_lookback_used} months for average calculation (lookback set to {lookback_months}).")
    else:
        # If a number > 0, use the specified number of months
        df_lookback = df.head(lookback_months).copy()
        actual_lookback_used = len(df_lookback)
        logging.debug(
            f"Using the last {actual_lookback_used} months for average calculation (lookback set to {lookback_months}).")

        # If the lookback window is empty (e.g., less history than requested), return zeros
    if df_lookback.empty:
        return {'avg_rate': 0.0, 'avg_contribution': 0.0, 'avg_monthly_pnl_currency': 0.0}
    # 1. Calculate Average Monthly Payment (PMT)
    avg_contribution = df_lookback['contribution'].mean()

    # 2. Determine Rate based on Account Type
    avg_rate = 0.0
    avg_pnl_currency = 0.0

    if account_type == 'SAVING':
        # P&L and Balance are already in Base Currency
        avg_pnl_currency = df_lookback['monthly_pnl_bc'].mean()  # Use the new BC P&L field
        avg_balance_for_rate_calc = df_lookback['closingBalance'].mean()

        if avg_balance_for_rate_calc > 0:
            avg_monthly_rate = avg_pnl_currency / avg_balance_for_rate_calc
            avg_rate = avg_monthly_rate * 12.0
    elif account_type == 'LOAN':
        original_df = pd.DataFrame(history)
        original_df['monthKey'] = pd.to_datetime(original_df['monthKey'], format='%Y-%m')
        # Slicing the original data to match the determined lookback period
        lookback_months = df_lookback['monthKey'].dt.strftime('%Y-%m').unique()
        original_df['monthKey_str'] = original_df['monthKey'].dt.strftime('%Y-%m')
        df_loan_lookback = original_df[original_df['monthKey_str'].isin(lookback_months)].copy()
        avg_rate = 0.0  # Initialize avg_rate to 0.0
        if 'interestRate' in df_loan_lookback.columns:
            # 1. Sort the lookback data to ensure the newest month is at the top
            #    We use the index from df_lookback which is already sorted DESC by monthKey
            df_loan_lookback = df_loan_lookback.sort_values(by='monthKey', ascending=False)
            # 2. Get the value from the first row that is NOT null (the latest month)
            latest_rate = df_loan_lookback['interestRate'].dropna().iloc[0] if not df_loan_lookback[
                'interestRate'].dropna().empty else 0.0
            # Set the avg_rate to this latest rate
            avg_rate = latest_rate
        else:
            avg_rate = 0.0  # Stays 0.0

    return {
        'avg_rate': avg_rate if account_type == 'SAVING' else avg_rate / 100.0,
        'avg_contribution': avg_contribution,
        'avg_monthly_pnl_currency': avg_pnl_currency
    }

# The formula used is the Future Value of an Annuity (FV)
# FV = PV * (1 + r)^n + PMT * [((1 + r)^n - 1) / r]
# Where:
# PV = Present Value (Current Balance)
# PMT = Periodic Payment (Monthly Contribution/Payment)
# r = Rate per period (Annual Rate / 12)
# n = Number of periods (Months to Project)

def calculate_simple_projection(current_balance, annual_rate, monthly_payment, months_to_project):
    """
    Projects the future balance of a single account using monthly compounding.

    Args:
        current_balance (float): The starting value of the account (PV).
        annual_rate (float): The expected annual return rate (as a decimal, e.g., 0.08).
        monthly_payment (float): The periodic contribution (PMT). Positive for savings, negative for loan.
        months_to_project (int): The duration of the projection in months (n).

    Returns:
        float: The projected future balance (FV).
    """
    if months_to_project <= 0:
        return current_balance

    # Monthly rate (r)
    monthly_rate = annual_rate / 12.0

    # Calculate Future Value

    # Part 1: Future Value of the Current Balance (PV)
    future_value_of_pv = current_balance * np.power((1 + monthly_rate), months_to_project)

    # Part 2: Future Value of the Monthly Payments (PMT)
    if monthly_rate == 0:
        # Avoid division by zero if rate is 0
        future_value_of_pmt = monthly_payment * months_to_project
    else:
        future_value_of_pmt = monthly_payment * ((np.power((1 + monthly_rate), months_to_project) - 1) / monthly_rate)

    return future_value_of_pv + future_value_of_pmt


def run_net_worth_forecast(accounts_data, forecast_years=10):
    """
    Runs a net worth forecast by projecting the future balance for each account.

    Args:
        accounts_data (list): The list of account objects.
        forecast_years (int): The number of years to project.
        savings_rate (float): Expected annual return rate for SAVING accounts (as decimal).
        loan_rate (float): Effective annual interest rate for LOAN accounts (as decimal).

    Returns:
        dict: Projected net worth and a list of projected account details.
    """
    months_to_project = forecast_years * 12
    projected_net_worth = 0.0
    projection_details = []
    # Get the start date for the forecast (assume the latest month end)
    latest_month_key = None
    for account in accounts_data:
        if account.get('monthlyHistory'):
            # Find the latest month key in this specific account's history
            current_account_latest_key = sorted(account['monthlyHistory'], key=lambda x: x['monthKey'])[-1]['monthKey']

            # Compare the keys
            if latest_month_key is None:
                # If this is the first month key found, assign it directly
                latest_month_key = current_account_latest_key
            else:
                # Only compare if latest_month_key already holds a string value
                latest_month_key = max(latest_month_key, current_account_latest_key)
    if latest_month_key:
        latest_date = datetime.datetime.strptime(latest_month_key, "%Y-%m").date()
        # Advance the date to the first day of the NEXT month
        start_date = latest_date.replace(day=1) + datetime.timedelta(days=32)
        start_date = start_date.replace(day=1)
    else:
        # Fallback if no history was found anywhere
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

        avg_inputs = get_rolling_average_inputs(account, lookback_months=3)
        historical_rate = avg_inputs['avg_rate']
        monthly_payment_raw = avg_inputs['avg_contribution']

        if current_balance <= 0.0:
            continue

        rate = 0.0
        projected_balance = 0.0
        months_to_payoff = 0.0
        payoff_date_str = 'N/A'

        if account_type == 'SAVING':
            rate = historical_rate
            monthly_payment = monthly_payment_raw  # Money going in (Positive PMT)

            projected_balance = calculate_simple_projection(
                current_balance, rate, monthly_payment, months_to_project
            )
            projected_net_worth += projected_balance

        elif account_type == 'LOAN':
            # For loans, the calculation is simpler: the remaining principal is reduced by payments.
            # We use the loan rate as the negative compounding return.
            rate = -historical_rate  # Treat the loan rate as a negative return on debt balance
            monthly_payment = -monthly_payment_raw  # Money going out (Negative PMT)

            months_to_payoff, payoff_date_str = calculate_loan_payoff_date(
                principal=current_balance,
                annual_rate=rate,
                monthly_payment=abs(monthly_payment),
                start_date=start_date
            )

            # If the loan pays off within the forecast period, the projected balance is 0.00
            # Otherwise, use the compounding formula
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

    # --- Overall Summary ---
    logging.info(f"\n--- 🔮 {forecast_years} Year Financial Forecast Summary ---")
    logging.info(f"\n--- using all data average except loans ---")
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

    Args:
        accounts_data (List[Dict]): The list of account objects, each containing
                                    a 'monthlyHistory' list.
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
            # Note: We assume the monthKey strings are comparable (e.g., 'YYYY-MM')
            current_account_latest_key = sorted(history, key=lambda x: x['monthKey'])[-1]['monthKey']
            if latest_month_key is None or current_account_latest_key > latest_month_key:
                latest_month_key = current_account_latest_key

    if not latest_month_key:
        logging.info("No historical data found in any account to summarize.")
        return

    # Convert monthKey for printing (using datetime.datetime to fix previous error)
    try:
        latest_date = datetime.datetime.strptime(latest_month_key, "%Y-%m").date()
        month_str = latest_date.strftime('%B %Y')
    except ValueError:
        # Fallback if the date format is unexpected
        month_str = latest_month_key

        # 2. Second Pass: Calculate P&L and Cashflow for the latest month
    for account in accounts_data:
        history = account.get('monthlyHistory', [])
        # Find the specific record for the latest month
        latest_record = next((d for d in history if d.get('monthKey') == latest_month_key), None)

        if latest_record:
            closing_balance = latest_record.get('closingBalance', 0.0)
            opening_balance = latest_record.get('openingBalance', 0.0)

            # --- Key Calculation Step ---

            # Cashflow is directly available as 'contribution'
            # For SAVING accounts, this is positive (deposit).
            # For LOAN accounts, this is assumed to be negative (payment),
            # but is provided as a positive number in the data structure,
            # so we flip it for LOANs to represent a negative cash flow.

            contribution = latest_record.get('contribution', 0.0)
            account_type = account.get('type')

            if account_type == 'LOAN':
                # Treat loan payments as an outflow
                monthly_cashflow = -contribution
            else:
                # Treat deposits as an inflow
                monthly_cashflow = contribution

            # P&L = Closing Balance - Opening Balance - Contribution (with proper sign)
            # Since contribution is usually an absolute number in history,
            # we use the absolute value here and let the loan type determine
            # the sign of the P&L later.

            # P&L is the net change *after* accounting for the cash movement:
            monthly_pl = closing_balance - opening_balance - contribution

            # For LOANs, the P&L is the interest accrual, which is a *negative* return
            # on net worth, but a positive change in the loan's numerical balance.
            # We must account for this by flipping the sign of P&L for loans.
            if account_type == 'LOAN':
                # Interest paid reduces net worth, so P&L is negative.
                # Since P&L is calculated as a positive number (interest cost), we flip it.
                monthly_pl = -monthly_pl

                # --- Aggregation ---
            net_contribution += monthly_cashflow
            total_pl += monthly_pl

    # --- Print the Summary ---
    logging.info(f"\n--- 💰 Financial Summary for the Latest Month: {month_str} ---")

    # Format values for readability
    net_contribution_fmt = f"{net_contribution:,.2f}"
    total_pl_fmt = f"{total_pl:,.2f}"

    logging.info(f"| Net Contribution (Your Cash Flow): {' ' * (28 - len(net_contribution_fmt))} {net_contribution_fmt}")
    logging.info(f"| Net Market Gain / (Loss) (Interest/Return): {' ' * (18 - len(total_pl_fmt))} {total_pl_fmt}")

    # Optional: Provide the interpretation
    net_change = net_contribution + total_pl
    net_change_fmt = f"{net_change:,.2f}"

    if net_change < 0:
        logging.info(f"\n⚠️ WARNING: Overall Net Worth DECREASED by {net_change_fmt}.")
        if total_pl < 0:
            logging.info("Reason: High debt cost and/or poor asset performance.")
        else:
            logging.info("Reason: Contribution/Withdrawal was too low to offset debt cost.")
    else:
        logging.info(f"\n✅ GROWTH: Overall Net Worth INCREASED by {net_change_fmt}.")
        logging.info("Reason: Total return (P&L) and contribution were positive.")