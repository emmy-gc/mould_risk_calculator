from django.test import TestCase
import pandas as pd
import numpy as np
from mould_calculator.utils import (
    standardize_dataframe,
    calculate_rh_crit,
    calculate_dMdt,
    process_mold_index,
    mould_score,
)

class UtilsPureFunctionTests(TestCase):
    def test_standardize_dataframe_basic(self):
        df = pd.DataFrame({
            'Timestamp': ['2024-01-01 00:00:00'],
            'Temp(°C)': [25],
            'RH (%)': [80]
        })
        std = standardize_dataframe(df)
        # Check that columns are renamed correctly
        self.assertListEqual(list(std.columns), ['Timestamp', 'Temperature', 'Humidity'])
        # Check values
        self.assertEqual(std['Temperature'].iloc[0], 25.0)
        self.assertEqual(std['Humidity'].iloc[0], 80.0)

    def test_calculate_rh_crit_values(self):
        # Exactly at 20°C
        self.assertEqual(calculate_rh_crit(20), 80)
        # Below 20°C
        self.assertEqual(calculate_rh_crit(10), 80 + (-0.5 * (20 - 10)))

    def test_calculate_dMdt_growth_and_decay(self):
        # Growth branch (RH >= RH_crit, M < 1)
        val_growth = calculate_dMdt(RH=85, RH_crit=80, M=0.5, t1=24)
        k1 = 0.006
        k2 = max(1 - np.exp(2.3 * (0.5 - 6)), 0)
        self.assertAlmostEqual(val_growth, k1 * k2, places=6)

        # Decay branch (RH < RH_crit, small difference)
        val_decay_small = calculate_dMdt(RH=75, RH_crit=80, M=0.5, t1=24)
        self.assertAlmostEqual(val_decay_small, -0.001 * abs(75 - 80), places=6)

        # Decay branch (RH < RH_crit, large difference)
        val_decay_large = calculate_dMdt(RH=50, RH_crit=80, M=0.5, t1=24)
        self.assertAlmostEqual(val_decay_large, -0.0005, places=6)

    def test_process_mold_index_returns_expected_structure(self):
        # Create a small synthetic dataset with RH >= RH_crit to force growth
        dates = pd.date_range('2024-01-01', periods=10, freq='h')
        df = pd.DataFrame({'time': dates, 'temperature': [30]*10, 'humidity': [95]*10})
        idx, series, timeframe, full_data = process_mold_index(df, rolling_window=5)
        # Final index should be a float
        self.assertIsInstance(idx, float)
        # Series should be a list of dicts with timestamp and mould_index
        self.assertIsInstance(series, list)
        self.assertTrue(all(isinstance(item, dict) for item in series))
        self.assertTrue(all('timestamp' in item and 'mould_index' in item for item in series))
        # Full_data should be list of records
        self.assertIsInstance(full_data, list)

    def test_mould_score_mapping(self):
        # Single-row DF to extract last temperature/humidity
        dates = pd.date_range('2024-01-01', periods=1, freq='h')
        df = pd.DataFrame({'time': dates, 'temperature': [25], 'humidity': [85]})
        # Low index
        score_low = mould_score(10.0, df)
        self.assertEqual(score_low['risk_level'], 'Low')
        # Moderate index
        score_mod = mould_score(30.0, df)
        self.assertEqual(score_mod['risk_level'], 'Moderate')
        # High index
        score_high = mould_score(60.0, df)
        self.assertEqual(score_high['risk_level'], 'High')
