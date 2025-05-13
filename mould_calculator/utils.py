import numpy as np
import pandas as pd
from collections import deque
from datetime import timedelta
import math

"""Standardizes input dataframe to have consistent column names and data types"""
def standardize_dataframe(df):
    try:
        df.columns = df.columns.str.lower().str.strip()

        timestamp_columns = [
            'timestamp', 'local date/time', 'utc date/time', 'date/time', 'date', 
            'time', 'datetime', 'measurement time'
        ]

        temperature_columns = [
            'temperature', 'temperature (°c)', 'temperature (c)', 'temperature (ºc)', 
            'heat index (°c)', 'temp', 'temp(°c)', 'temp(c)', 'temp °c', 'temp c',
            't(°c)', 't(c)', 't °c', 't c'
        ]

        humidity_columns = [
            'humidity', 'humidity (%)', 'relative humidity', 'rh (%)', 'rh', 
            'humidity%', 'rh%', 'relative humidity (%)', 'humidity level'
        ]

        print("Available columns in CSV:", df.columns.tolist())

        timestamp_col = next((col for col in df.columns if any(name in col for name in timestamp_columns)), None)
        temperature_col = next((col for col in df.columns if any(name in col for name in temperature_columns)), None)
        humidity_col = next((col for col in df.columns if any(name in col for name in humidity_columns)), None)

        print(f"Found timestamp column: {timestamp_col}")
        print(f"Found temperature column: {temperature_col}")
        print(f"Found humidity column: {humidity_col}")

        if not all([timestamp_col, temperature_col, humidity_col]):
            missing_cols = []
            if not timestamp_col: missing_cols.append("Timestamp")
            if not temperature_col: missing_cols.append("Temperature")
            if not humidity_col: missing_cols.append("Humidity")
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

        standardized_df = pd.DataFrame({
            'Timestamp': pd.to_datetime(df[timestamp_col]),
            'Temperature': pd.to_numeric(df[temperature_col], errors='coerce'),
            'Humidity': pd.to_numeric(df[humidity_col], errors='coerce')
        })

        print("\nStandardized data first few rows:")
        print(standardized_df.head())

        return standardized_df.dropna().sort_values('Timestamp')

    except Exception as e:
        print(f"Error in standardize_dataframe: {str(e)}")
        raise


"""Calculate critical relative humidity threshold for mould growth"""
def calculate_rh_crit(temp):
    try:
        temp = float(temp)
        if temp <= 20:
            return 80 + (-0.5 * (20 - temp))
        else:
            return 80
    except Exception as e:
        print(f"Error in calculate_rh_crit: {str(e)}")
        return 80


"""Calculate rate of change of mould index"""
def calculate_dMdt(RH, RH_crit, M, time_delta_hours):
    try:
        RH = float(RH)
        RH_crit = float(RH_crit)
        M = float(M)

        RH_diff = RH - RH_crit

        if RH >= RH_crit:
            k1 = 0.22 if M < 1 else 0.33  
            k2 = max(1 - np.exp(2.3 * (M - 6)), 0)

            if RH <= 0:
                return 0

            dMdt = k1 * k2
        else:
            dMdt = -0.001 * abs(RH_diff) if RH_diff > -10 else -0.0005

        #scale dMdt by time delta 
        scaled_dMdt = dMdt * (time_delta_hours / 24.0)
        print(f"RH: {RH:.2f}, RH_crit: {RH_crit:.2f}, M: {M:.4f}, dMdt: {dMdt:.6f}, scaled_dMdt: {scaled_dMdt:.6f}")
        return 0 if np.isnan(scaled_dMdt) or np.isinf(scaled_dMdt) else scaled_dMdt

    except Exception as e:
        print(f"Error in calculate_dMdt: {str(e)}")
        return 0


"""Calculate mould index from temperature and humidity data"""
def process_mold_index(data, rolling_window=None):
    try:
        standardized_data = standardize_dataframe(data)
        if standardized_data.empty:
            raise ValueError("No valid data after standardization")

        #detect time interval in minutes
        time_deltas = standardized_data['Timestamp'].diff().dt.total_seconds() / 60.0
        median_interval = time_deltas.median()
        if np.isnan(median_interval) or median_interval <= 0:
            median_interval = 60.0  
        print(f"Detected median time interval: {median_interval:.2f} minutes")

        #calculate dynamic rolling window based on dataset duration
        time_span = standardized_data['Timestamp'].max() - standardized_data['Timestamp'].min()
        rolling_window_days = max(1, math.ceil(time_span.total_seconds() / (24 * 3600)))
        if rolling_window is None:
            rolling_window = rolling_window_days
        else:
            rolling_window = min(rolling_window, rolling_window_days)  # Respect user input if shorter
        print(f"Dynamic rolling window set to {rolling_window} days based on dataset duration")

        #calculate number of data points in rolling window based on time interval
        points_per_day = (24 * 60) / median_interval
        rolling_queue_maxlen = int(rolling_window * points_per_day)
        print(f"Rolling queue maxlen: {rolling_queue_maxlen} data points")

        latest_timestamp = standardized_data['Timestamp'].max()
        cutoff_time = latest_timestamp - timedelta(days=rolling_window)
        recent_data = standardized_data[standardized_data['Timestamp'] >= cutoff_time]

        if recent_data.empty:
            recent_data = standardized_data.copy()
            used_timeframe = f"Entire dataset ({recent_data['Timestamp'].min().date()} to {recent_data['Timestamp'].max().date()})"
        else:
            used_timeframe = f"Last {rolling_window} days ({recent_data['Timestamp'].min().date()} to {recent_data['Timestamp'].max().date()})"

        M = 0.1
        rolling_queue = deque(maxlen=rolling_queue_maxlen)
        mould_index_series = []

        #calculate time for scaling 
        recent_data['TimeDelta'] = recent_data['Timestamp'].diff().dt.total_seconds() / 3600.0
        recent_data['TimeDelta'] = recent_data['TimeDelta'].fillna(median_interval / 60.0)  

        for index, row in recent_data.iterrows():
            try:
                temp = float(row['Temperature'])
                RH = float(row['Humidity'])
                time_delta_hours = float(row['TimeDelta'])

                RH_crit = calculate_rh_crit(temp)
                rolling_queue.append((RH, temp))

                if rolling_queue:
                    avg_RH = np.mean([x[0] for x in rolling_queue])
                    avg_temp = np.mean([x[1] for x in rolling_queue])
                    RH_crit_window = calculate_rh_crit(avg_temp)
                    dMdt = calculate_dMdt(avg_RH, RH_crit_window, M, time_delta_hours)

                    M = max(0, min(6, M + dMdt))
                    print(f"Timestamp: {row['Timestamp']}, Avg RH: {avg_RH:.2f}, Avg Temp: {avg_temp:.2f}, M: {M:.4f}")

                    mould_index_series.append({
                        "timestamp": row['Timestamp'].strftime("%Y-%m-%d %H:%M"),
                        "mould_index": round(M, 2)
                    })

            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                continue

        #smooth the mould index values over time
        series_df = pd.DataFrame(mould_index_series)
        if not series_df.empty:
            series_df['smoothed'] = series_df['mould_index'].rolling(window=5, min_periods=1).mean()
            series_df['mould_index'] = series_df['smoothed'].round(2)
            mould_index_series = series_df[['timestamp', 'mould_index']].to_dict(orient='records')

        final_percentage = (M / 6) * 100
        return final_percentage, mould_index_series, used_timeframe, standardized_data.to_dict(orient='records')

    except Exception as e:
        print(f"Error in process_mold_index: {str(e)}")
        return None, [], "No data", []


"""Evaluate mould risk level based on calculated index"""
def mould_score(mould_index, data):
    try:
        standardized_data = standardize_dataframe(data)
        latest_temp = standardized_data['Temperature'].iloc[-1]
        latest_humidity = standardized_data['Humidity'].iloc[-1]

        if mould_index < 16.7:
            risk_level = "Low"
            status = "Environmental conditions unfavorable for mould growth"
        elif mould_index < 30: 
            risk_level = "Moderate"
            status = "Conditions could potentially support mould growth"
        else:
            risk_level = "High"
            status = "Conditions highly favorable for mould growth"

        return {
            'risk_level': risk_level,
            'status': status,
            'mould_index': mould_index,
            'current_temperature': latest_temp,
            'current_humidity': latest_humidity
        }
    except Exception as e:
        print(f"Error in mould_score: {str(e)}")
        return None