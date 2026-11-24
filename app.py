import streamlit as st
import duckdb
import pandas as pd

st.set_page_config(page_title="APAC Weather Intelligence", page_icon="🌏", layout="wide")

st.title("🌏 APAC Multi-City Weather & Environmental Intelligence")
st.caption("Medallion Lakehouse (OpenWeather → dlt → S3 Parquet → dbt Star Schema → DuckDB)")



@st.cache_data(ttl=300)
def load_gold_marts():
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL aws; LOAD aws;")
    con.execute("CREATE SECRET (TYPE S3, PROVIDER credential_chain);")

    locations_df = con.execute("""
        SELECT *
        FROM read_parquet('s3://weather-datalake-dev/prod_gold/dim_location.parquet')
        ORDER BY city_name
    """).df()

    current_df = con.execute("""
        SELECT *
        FROM read_parquet('s3://weather-datalake-dev/prod_gold/fct_city_current_conditions.parquet')
        WHERE is_latest_observation = true
    """).df()

    forecast_df = con.execute("""
        SELECT *
        FROM read_parquet('s3://weather-datalake-dev/prod_gold/fct_city_forecast_3h.parquet')
        WHERE is_upcoming = true
        ORDER BY forecast_time_local ASC
    """).df()

    return locations_df, current_df, forecast_df


with st.spinner("Querying S3 Gold Layer..."):
    locations_df, current_df, forecast_df = load_gold_marts()

tab_city, tab_compare = st.tabs(["📍 City Forecast & Hazards", "📊 APAC Cross-City Comparison"])

with tab_city:
    city_options = dict(zip(locations_df["city_name"], locations_df["city_key"]))
    selected_name = st.selectbox("Select APAC City", list(city_options.keys()), index=0)
    selected_key = city_options[selected_name]

    city_now = current_df[current_df["city_key"] == selected_key].iloc[0]
    city_fct = forecast_df[forecast_df["city_key"] == selected_key].copy()
    city_fct["forecast_time_local"] = pd.to_datetime(city_fct["forecast_time_local"])

    st.markdown(
        f"**{city_now['city_name']}, {city_now['country_code']}** · "
        f"*{city_now['climate_zone']}* · "
        f"Condition: **{city_now['condition_desc'].title()}** · "
        f"Last Updated (Local): `{pd.to_datetime(city_now['observed_at_local']).strftime('%b %d, %I:%M %p')}`"
    )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric(
            "Temperature",
            f"{city_now['temp_celsius']:.1f} °C",
            f"Feels like {city_now['feels_like_celsius']:.1f} °C",
        )
    with k2:
        st.metric(
            "PAGASA Heat Index",
            f"{city_now['heat_index_celsius']:.1f} °C",
            city_now["heat_advisory_level"],
        )
    with k3:
        st.metric(
            "Air Quality (AQI)",
            f"{city_now['aqi_label']} ({int(city_now['aqi_score'])}/5)",
            f"PM2.5: {city_now['pm2_5_ugm3']:.1f} µg/m³",
        )
    with k4:
        st.metric(
            "Humidity & Clouds",
            f"{int(city_now['humidity_pct'])}%",
            f"Cloud cover: {int(city_now['clouds_pct'])}%",
        )
    with k5:
        st.metric(
            "Wind Speed",
            f"{city_now['wind_speed_kmh']:.1f} km/h",
            f"Pressure: {int(city_now['pressure_hpa'])} hPa",
        )

    st.divider()

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("5-Day Temperature & Feels-Like Outlook (3-Hr Steps)")
        temp_chart = city_fct.set_index("forecast_time_local")[
            ["temp_celsius", "feels_like_celsius"]
        ].rename(columns={"temp_celsius": "Temp (°C)", "feels_like_celsius": "Feels Like (°C)"})
        st.line_chart(temp_chart, color=["#ff7b00", "#00a8e8"])

    with col_chart2:
        st.subheader("5-Day Precipitation Probability (%)")
        rain_chart = city_fct.set_index("forecast_time_local")[["rain_prob_pct"]].rename(
            columns={"rain_prob_pct": "Rain Probability (%)"}
        )
        st.bar_chart(rain_chart, color="#3b82f6")

    st.subheader("3-Hour Forecast Schedule")
    schedule_df = city_fct[
        [
            "forecast_time_local",
            "condition_desc",
            "temp_celsius",
            "feels_like_celsius",
            "rain_prob_pct",
            "humidity_pct",
            "wind_speed_kmh",
        ]
    ].copy()
    schedule_df["forecast_time_local"] = schedule_df["forecast_time_local"].dt.strftime("%a %b %d, %H:%M")
    schedule_df["condition_desc"] = schedule_df["condition_desc"].str.title()
    schedule_df.columns = [
        "Local Time",
        "Condition",
        "Temp (°C)",
        "Feels Like (°C)",
        "Rain Prob (%)",
        "Humidity (%)",
        "Wind (km/h)",
    ]
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)

with tab_compare:
    st.subheader("Live APAC Regional Benchmarking")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Temperature vs. Heat Index (°C)**")
        comp_temp = current_df.set_index("city_name")[
            ["temp_celsius", "heat_index_celsius"]
        ].rename(columns={"temp_celsius": "Actual Temp (°C)", "heat_index_celsius": "Heat Index (°C)"})
        st.bar_chart(comp_temp)

    with c2:
        st.markdown("**Fine Particulate Matter — PM2.5 (µg/m³)**")
        comp_air = current_df.set_index("city_name")[["pm2_5_ugm3"]].rename(
            columns={"pm2_5_ugm3": "PM2.5 (µg/m³)"}
        )
        st.bar_chart(comp_air, color="#10b981")

    st.subheader("Regional Conditions Matrix")
    matrix_df = current_df[
        [
            "city_name",
            "country_code",
            "climate_zone",
            "condition_desc",
            "temp_celsius",
            "heat_index_celsius",
            "heat_advisory_level",
            "aqi_label",
            "pm2_5_ugm3",
            "humidity_pct",
            "wind_speed_kmh",
        ]
    ].sort_values("heat_index_celsius", ascending=False)
    matrix_df["condition_desc"] = matrix_df["condition_desc"].str.title()
    matrix_df.columns = [
        "City",
        "Country",
        "Climate Zone",
        "Condition",
        "Temp (°C)",
        "Heat Index (°C)",
        "Heat Advisory",
        "Air Quality",
        "PM2.5 (µg/m³)",
        "Humidity (%)",
        "Wind (km/h)",
    ]
    st.dataframe(matrix_df, use_container_width=True, hide_index=True)