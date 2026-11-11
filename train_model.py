import duckdb
import pandas as pd
import xgboost as xgb
from datetime import timedelta

print("Initializing ML Engine...")
con = duckdb.connect(database=':memory:')
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL aws; LOAD aws;")
con.execute("CREATE SECRET (TYPE S3, PROVIDER credential_chain);")

# 1. Read all columns from the current Silver path
print("Reading historical data from S3 silver...")
df = con.execute("SELECT * FROM read_parquet('s3://weather-datalake-dev/silver/stg_manila_daily.parquet')").df()

print("Columns found in Silver layer:", df.columns.tolist())

# 2. Dynamically find the date and max temperature columns based on your dbt transformations
date_col = 'time' if 'time' in df.columns else 'date' if 'date' in df.columns else df.columns[0]
temp_col = 'max_temp_celsius' if 'max_temp_celsius' in df.columns else 'temperature_2m_max'

# 3. Feature Engineering for Time Series
df = df.dropna(subset=[date_col, temp_col]).copy()
df[date_col] = pd.to_datetime(df[date_col])
df = df.sort_values(date_col)

df['day_of_year'] = df[date_col].dt.dayofyear
df['trend'] = range(len(df))

# 4. Train the XGBoost Regressor
print(f"Training XGBoost Regressor using {date_col} and {temp_col}...")
X = df[['day_of_year', 'trend']]
y = df[temp_col]

model = xgb.XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
model.fit(X, y)

# 5. Generate 7-Day Future Forecast
print("Generating 7-day forecast...")
last_date = df[date_col].max()
future_dates = [last_date + timedelta(days=i) for i in range(1, 8)]
last_trend = df['trend'].max()

future_df = pd.DataFrame({
    'forecast_date': future_dates,
    'day_of_year': [d.dayofyear for d in future_dates],
    'trend': [last_trend + i for i in range(1, 8)]
})

# Predict and format output
future_df['predicted_max_temp_celsius'] = model.predict(future_df[['day_of_year', 'trend']])
future_forecast = future_df[['forecast_date', 'predicted_max_temp_celsius']]

# 6. Write Predictions back to S3 Gold Layer
print("Writing forecast to S3 gold...")
con.register('forecast_view', future_forecast)
con.execute("""
    COPY (SELECT * FROM forecast_view)
    TO 's3://weather-datalake-dev/gold/fct_ml_forecast.parquet'
    (FORMAT PARQUET);
""")

print("Success: ML Forecast Pipeline Complete!")