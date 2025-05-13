from django.test import TestCase
import pandas as pd
from mould_calculator.utils import process_mold_index

class CalculationMultipleScenariosTests(TestCase):
    """
    Demo test that runs the mould-index algorithm on multiple temperature/RH scenarios
    and prints out the final index for each, verifying all runs complete successfully.
    """
    def make_df(self, temp, rh, rows=6, freq='h'):
        """
        Helper to build a DataFrame of constant temp/RH for `rows` time steps.
        """
        return pd.DataFrame({
            'time': pd.date_range('2025-01-01', periods=rows, freq=freq),
            'temperature': [temp] * rows,
            'humidity':    [rh] * rows,
        })

    def test_multiple_scenarios(self):
        scenarios = [
            (15, 40),  
            (15, 90),  
            (20, 60),  
            (20, 85),  
            (25, 70),  
            (25, 90),  
            (30, 60),  
            (30, 95),  
            (22, 80),  
            (18, 75),  
            (28, 65),  
            (28, 85),  
        ]

        print("\n=== Multiple Scenario Demo ===")
        for temp, rh in scenarios:
            df = self.make_df(temp=temp, rh=rh, rows=6)
            final_pct, series, timeframe, _ = process_mold_index(df, rolling_window=6)
            # Each scenario should produce a float index
            self.assertIsInstance(final_pct, float)
            # Print summary for demonstration
            print(f"{temp}°C / {rh}% RH -> final mould index: {final_pct:.2f}% over {timeframe}")
