# Financial Literacy Analysis Tool

This project provides a comprehensive analysis of your financial health by examining your savings, loans, and utility expenses. It offers insights into your net worth, cash flow, and investment performance, helping you make informed financial decisions.

## Key Features

*   **Holistic Financial Overview**: Get a clear picture of your financial situation by combining data from your savings accounts, loans, and utility bills.
*   **Net Worth Calculation**: Track your net worth over time by subtracting your liabilities (loans) from your assets (savings).
*   **Cash Flow Analysis**: Understand where your money is going with a detailed breakdown of your contributions and expenses.
*   **Investment Performance**: See how well your investments are performing with the "Growth > Contribution Crossover" metric, which shows when your investments start working for you.
*   **Financial Forecasting**: Project your future net worth based on your historical performance and contribution habits.
*   **Utility Expense Tracking**: Monitor your utility costs to identify opportunities for savings.

## Professional Advisor Insights

Based on the analysis provided by this tool, a professional financial advisor might offer the following insights:

*   **Debt Management**: The "Detailed Account Summary" provides a clear view of your loan balances and interest costs. An advisor would likely focus on strategies to pay down high-interest debt, such as the "avalanche" or "snowball" method. The forecast's "Months to Payoff" can be a powerful motivator.
*   **Investment Strategy**: The "Growth > Contribution Crossover" is a key indicator of your investment portfolio's maturity. If this crossover has been recently achieved, an advisor might suggest that your portfolio is generating self-sustaining growth. If it has not been reached, the focus would be on increasing contributions or optimizing asset allocation for better returns.
*   **Cash Flow Optimization**: The "Last 3 Months Breakdown" and "Utility Analysis" can highlight areas where your cash flow can be improved. An advisor might suggest creating a budget to reduce non-essential spending and redirecting those funds towards savings or debt repayment.
*   **Long-Term Goals**: The financial forecast is a powerful tool for long-term planning. An advisor can help you use this forecast to set realistic goals for retirement, a down payment on a house, or other major life events. By adjusting the `forecast_years` and `lookback_months` parameters, you can model different scenarios and see how changes in your financial habits can impact your future net worth.

## How to Use

1.  **Update your data**:
    *   The financial data is currently mocked in `src/api_client.py`. In a real-world scenario, you would replace this with a connection to your financial institution's API.
    *   Update `src/data/utility.json` with your actual utility bill information.
2.  **Run the analysis**:
    ```sh
    make run
    ```
3.  **Review the output**: The analysis will be printed to the console and saved in a log file in the `logs` directory.

## Future Enhancements

*   **Automated Data Ingestion**: Connect to financial data aggregators (like Plaid or TrueLayer) to automatically pull in your latest financial data.
*   **Interactive Dashboards**: Use a library like Plotly or Dash to create interactive charts and graphs for a more engaging user experience.
*   **Budgeting and Goal Setting**: Add features to help users create budgets, set financial goals, and track their progress over time.
*   **More Sophisticated Forecasting**: Incorporate Monte Carlo simulations to provide a more probabilistic view of your financial future.
