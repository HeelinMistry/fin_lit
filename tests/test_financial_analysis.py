import unittest
from unittest.mock import patch
from src.financial_analysis import calculate_base_currency_history, calculate_financial_metrics

class TestFinancialAnalysis(unittest.TestCase):

    def setUp(self):
        """Set up common test data."""
        self.simple_account_history = [
            {
                'monthKey': '2023-01',
                'openingBalance': 1000.0,
                'closingBalance': 1100.0,
                'contribution': 50.0,
                'exchangeRate': 1.0
            },
            {
                'monthKey': '2023-02',
                'openingBalance': 1100.0,
                'closingBalance': 1200.0,
                'contribution': 50.0,
                'exchangeRate': 1.1
            }
        ]

        self.complex_accounts_data = [
            {
                "name": "Savings Account",
                "type": "SAVING",
                "monthlyHistory": [
                    {
                        "monthKey": "2023-01",
                        "openingBalance": 1000.0,
                        "closingBalance": 1050.0,
                        "contribution": 0.0,
                        "exchangeRate": 1.0
                    },
                    {
                        "monthKey": "2023-02",
                        "openingBalance": 1050.0,
                        "closingBalance": 1120.0,
                        "contribution": 20.0,
                        "exchangeRate": 1.0
                    },
                    {
                        "monthKey": "2023-03",
                        "openingBalance": 1120.0,
                        "closingBalance": 1200.0,
                        "contribution": 30.0,
                        "exchangeRate": 1.0
                    }
                ]
            },
            {
                "name": "Home Loan",
                "type": "LOAN",
                "monthlyHistory": [
                    {
                        "monthKey": "2023-01",
                        "openingBalance": 5000.0,
                        "closingBalance": 4900.0,
                        "contribution": 150.0, # 100 principal + 50 interest
                        "exchangeRate": 1.0
                    },
                    {
                        "monthKey": "2023-02",
                        "openingBalance": 4900.0,
                        "closingBalance": 4800.0,
                        "contribution": 140.0, # 100 principal + 40 interest
                        "exchangeRate": 1.0
                    },
                    {
                        "monthKey": "2023-03",
                        "openingBalance": 4800.0,
                        "closingBalance": 4700.0,
                        "contribution": 130.0, # 100 principal + 30 interest
                        "exchangeRate": 1.0
                    }
                ]
            }
        ]

    def test_calculate_base_currency_history(self):
        """Test currency conversion and P&L calculation for a single account history."""
        result = calculate_base_currency_history(self.simple_account_history)

        self.assertEqual(len(result), 2)
        
        # --- Month 1: Exchange Rate 1.0 ---
        # No conversion needed.
        # P&L = Closing (1100) - Opening (1000) - Contribution (50) = 50
        self.assertEqual(result[0]['closingBalance'], 1100.0)
        self.assertEqual(result[0]['openingBalance'], 1000.0)
        self.assertEqual(result[0]['contribution'], 50.0)
        self.assertEqual(result[0]['monthly_pnl_bc'], 50.0)

        # --- Month 2: Exchange Rate 1.1 ---
        # Values are converted to Base Currency (BC).
        # Closing BC: 1200 * 1.1 = 1320.0
        # Opening BC: 1100 * 1.1 = 1210.0
        # Contribution BC: 50 * 1.1 = 55.0
        # PnL BC: 1320 - 1210 - 55 = 55.0
        self.assertAlmostEqual(result[1]['closingBalance'], 1320.0)
        self.assertAlmostEqual(result[1]['openingBalance'], 1210.0)
        self.assertAlmostEqual(result[1]['contribution'], 55.0)
        self.assertAlmostEqual(result[1]['monthly_pnl_bc'], 55.0)

    @patch('src.financial_analysis.logging')
    def test_calculate_financial_metrics(self, _mock_logging):
        """Test overall financial metrics calculation including SAVING and LOAN accounts."""
        results = calculate_financial_metrics(self.complex_accounts_data)

        self.assertIsNotNone(results)
        
        # --- Verify Total Contribution ---
        # Savings: 0 + 20 + 30 = 50
        # Loan: 150 + 140 + 130 = 420
        # Total: 470
        self.assertAlmostEqual(results['total_contribution'], 470.0)

        # --- Verify Overall Net P&L ---
        # Savings P&L (Growth):
        #   Jan: 1050 - 1000 - 0 = 50
        #   Feb: 1120 - 1050 - 20 = 50
        #   Mar: 1200 - 1120 - 30 = 50
        #   Total Savings P&L = 150
        #
        # Loan P&L (Interest Cost):
        #   Jan: Interest = 150 (Contrib) - (5000 - 4900) (Principal) = 50
        #   Feb: Interest = 140 - (4900 - 4800) = 40
        #   Mar: Interest = 130 - (4800 - 4700) = 30
        #   Total Loan Cost = 120 (Negative P&L)
        #
        # Overall Net P&L = 150 (Savings) - 120 (Loan) = 30
        self.assertAlmostEqual(results['overall_net_pnl'], 30.0)

        # --- Verify Latest Net Balance (Net Worth) ---
        # As of March 2023:
        # Savings Balance: 1200
        # Loan Balance: 4700 (Liability)
        # Net Worth = 1200 - 4700 = -3500
        self.assertAlmostEqual(results['latest_net_balance'], -3500.0)

        # --- Verify Monthly Summary for Latest Month (March 2023) ---
        latest_month_summary = results['monthly_summary'][results['monthly_summary']['monthKey'] == '2023-03'].iloc[0]
        
        # Contribution: 30 (Savings) + 130 (Loan) = 160
        self.assertAlmostEqual(latest_month_summary['total_contribution'], 160.0)
        
        # Net P&L: 50 (Savings Growth) - 30 (Loan Interest) = 20
        self.assertAlmostEqual(latest_month_summary['total_net_pnl'], 20.0)
        
        # Net Balance: 1200 (Savings) - 4700 (Loan) = -3500
        self.assertAlmostEqual(latest_month_summary['total_net_balance'], -3500.0)

        # --- Verify Crossover Point ---
        # Savings Cumulative P&L: 50, 100, 150
        # Savings Cumulative Contribution: 0, 20, 50
        # Since P&L > Contribution from the start, crossover is the first month.
        self.assertEqual(results['crossover_point'], '2023-01')

if __name__ == '__main__':
    unittest.main()
