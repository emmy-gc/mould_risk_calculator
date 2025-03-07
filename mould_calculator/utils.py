import numpy as np
import pandas as pd
from collections import deque
from django.utils.timezone import now
from datetime import timedelta

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
            'Timestamp': pd.to_datetime(df[timestamp_col]) if timestamp_col else pd.Timestamp.now(),
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
def calculate_dMdt(RH, RH_crit, M, t1):
    
    try:
        RH = float(RH)
        RH_crit = float(RH_crit)
        M = float(M)
        
       
        RH_diff = RH - RH_crit

        if RH >= RH_crit:
            k1 = 0.006 if M < 1 else 0.009
            k2 = max(1 - np.exp(2.3 * (M - 6)), 0)
            
            if RH <= 0:
                return 0
                
            dMdt = k1 * k2
        else:
            dMdt = -0.001 * abs(RH_diff) if RH_diff > -10 else -0.0005

        return 0 if np.isnan(dMdt) or np.isinf(dMdt) else dMdt
        
    except Exception as e:
        print(f"Error in calculate_dMdt: {str(e)}")
        return 0
    

"""Calculate mould index from temperature and humidity data"""
def process_mold_index(data, rolling_window=30):
    try:
        print("Starting process_mold_index")
        print(f"Input data shape: {data.shape}")
        
        standardized_data = standardize_dataframe(data)
        print(f"Standardized data shape: {standardized_data.shape}")
        
        if standardized_data.empty:
            raise ValueError("No valid data after standardization")

        cutoff_time = now() - timedelta(days=rolling_window)
        recent_data = standardized_data[standardized_data['Timestamp'] >= cutoff_time]
        
        if recent_data.empty:
            recent_data = standardized_data.copy()

        
        M = 0.1 
        rolling_queue = deque(maxlen=rolling_window)

        for index, row in recent_data.iterrows():
            try:
                temp = float(row['Temperature'])
                RH = float(row['Humidity'])
                
                RH_crit = calculate_rh_crit(temp)
                rolling_queue.append((RH, temp))
                
                if len(rolling_queue) > 0:
                    avg_RH = np.mean([x[0] for x in rolling_queue])
                    avg_temp = np.mean([x[1] for x in rolling_queue])
                    
                    RH_crit_window = calculate_rh_crit(avg_temp)
                    dMdt = calculate_dMdt(avg_RH, RH_crit_window, M, t1=24)
                    
                    M = max(0, min(6, M + dMdt))
                    
                    percentage = (M / 6) * 100
                    
                    print(f"Row {index}: Temp={temp:.1f}°C, RH={RH:.1f}%, "
                          f"RH_crit={RH_crit:.1f}%, M={M:.2f}, Percentage={percentage:.1f}%")

            except Exception as row_error:
                print(f"Error processing row {index}: {str(row_error)}")
                continue
        final_percentage = (M / 6) * 100
        print(f"Final mould index: {M:.2f} ({final_percentage:.1f}%)")
        return final_percentage 

    except Exception as e:
        print(f"Error in process_mold_index: {str(e)}")
        return None

"""Evaluate mould risk level based on calculated index"""
def mould_score(mould_index, data):
    try:
        standardized_data = standardize_dataframe(data)
        latest_temp = standardized_data['Temperature'].iloc[-1]
        latest_humidity = standardized_data['Humidity'].iloc[-1]

        if mould_index < 16.7:
            risk_level = "Low"
            status = "Environmental conditions unfavorable for mould growth"
        elif mould_index < 50: 
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
















    
    
