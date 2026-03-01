import json
import os
import pandas as pd


def analyze_utility_data(file_path='./data/utility.json'):
    if not os.path.exists(file_path):
        return None

    with open(file_path, 'r') as f:
        data = json.load(f)

    utility_list = data.get('utility', [])
    processed_data = []

    print("\nCost Efficiency (The 'Value to Amount' Ratio)")
    print("Higher = Bad (You are paying more per unit)")
    for utility in utility_list:
        history = sorted(utility.get('monthlyHistory', []), key=lambda x: x['dateKey'])

        for i, record in enumerate(history):
            date = pd.to_datetime(record['dateKey'])
            amt_paid = record.get('amount', 0.0)
            units_received = record.get('value', 0.0)
            bal_before_load = record.get('balance', 0.0)
            cost_per_unit = amt_paid / units_received if units_received > 0 else 0
            processed_data.append({
                'Month': date.strftime('%Y-%m'),
                'Paid': amt_paid,
                'kWh_Bought': units_received,
                'Price_Per_kWh': round(cost_per_unit, 2),
                'remaining_balance_before_load': bal_before_load,
            })

    return pd.DataFrame(processed_data)


# Run and Display
df = analyze_utility_data()
print(df.to_string())
def format_and_print_utility_analysis(df):
    """
    Formats and logs the utility analysis results.
    """
    if df is None or df.empty:
        print("\n--- 💡 Utility Analysis ---")
        print("No utility data available for analysis.")
        return

    print("\n--- 💡 Utility Analysis ---")
    
    # Format currency columns
    cols_to_format = ['Total Cost', 'Average Monthly Cost', 'Latest Cost']
    for col in cols_to_format:
        if col in df.columns:
            df[col] = df[col].map(lambda x: f'{x:,.2f}')

    print(df.to_markdown(index=False))

if __name__ == '__main__':
    # --- Utility Analysis ---
    utility_df = analyze_utility_data()
    format_and_print_utility_analysis(utility_df)