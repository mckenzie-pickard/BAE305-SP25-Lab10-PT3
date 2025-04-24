import streamlit as st
import pandas as pd
import folium
import matplotlib.pyplot as plt
from folium.plugins import MarkerCluster
from datetime import datetime
from streamlit_folium import st_folium

# Load and filter sites (Part 1)
def load_and_filter_sites(file_path):
    df = pd.read_csv(file_path, dtype=str)
    df['LatitudeMeasure'] = pd.to_numeric(df.get('LatitudeMeasure'), errors='coerce')
    df['LongitudeMeasure'] = pd.to_numeric(df.get('LongitudeMeasure'), errors='coerce')
    unique_sites = df.drop_duplicates(subset=['MonitoringLocationName', 'LatitudeMeasure', 'LongitudeMeasure'])
    unique_sites = unique_sites.dropna(subset=['LatitudeMeasure', 'LongitudeMeasure'])
    return unique_sites

def plot_sites_on_map(sites_df):
    if sites_df.empty:
        raise ValueError("No valid monitoring sites to plot.")
    m = folium.Map(
        location=[sites_df['LatitudeMeasure'].mean(), sites_df['LongitudeMeasure'].mean()],
        zoom_start=6
    )
    for _, row in sites_df.iterrows():
        folium.Marker(
            location=[row['LatitudeMeasure'], row['LongitudeMeasure']],
            popup=row['MonitoringLocationName']
        ).add_to(m)
    return m

# Load the contaminant data (Part 2)
def load_contaminant_data(file_path):
    df = pd.read_csv(file_path)
    df['ResultMeasureValue'] = pd.to_numeric(df.get('ResultMeasureValue'), errors='coerce')
    df['ActivityStartDate'] = pd.to_datetime(df.get('ActivityStartDate'), errors='coerce')

    # Only convert lat/lon if they exist
    if 'LatitudeMeasure' in df.columns and 'LongitudeMeasure' in df.columns:
        df['LatitudeMeasure'] = pd.to_numeric(df.get('LatitudeMeasure'), errors='coerce')
        df['LongitudeMeasure'] = pd.to_numeric(df.get('LongitudeMeasure'), errors='coerce')
    return df

# Filter contaminant data based on user input
def filter_data(df, contaminant, value_range, date_range):
    filtered_df = df[df['CharacteristicName'] == contaminant]
    filtered_df = filtered_df[
        (filtered_df['ResultMeasureValue'] >= value_range[0]) &
        (filtered_df['ResultMeasureValue'] <= value_range[1])
    ]
    date_range = [pd.to_datetime(date) for date in date_range]
    filtered_df = filtered_df[
        (filtered_df['ActivityStartDate'] >= date_range[0]) &
        (filtered_df['ActivityStartDate'] <= date_range[1])
    ]

    # Add Latitude and Longitude if missing
    if 'LatitudeMeasure' not in filtered_df.columns or 'LongitudeMeasure' not in filtered_df.columns:
        if 'MonitoringLocationIdentifier' in df.columns:
            lat_lon_df = df[['MonitoringLocationIdentifier', 'LatitudeMeasure', 'LongitudeMeasure']].drop_duplicates()
            filtered_df = filtered_df.merge(lat_lon_df, on='MonitoringLocationIdentifier', how='left')
    return filtered_df

# Plot the dual characteristics with switched axes
def plot_dual_characteristics(df, characteristics):
    if not (1 <= len(characteristics) <= 2):
        raise ValueError("Please specify one or two characteristics.")

    date_col = 'ActivityStartDate'
    site_col = 'MonitoringLocationIdentifier'
    value_col = 'ResultMeasureValue'
    char_col = 'CharacteristicName'

    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col, value_col, site_col, char_col])
    df_filtered = df[df[char_col].isin(characteristics)]

    plt.figure(figsize=(12, 6))
    for (site, char), group in df_filtered.groupby([site_col, char_col]):
        group_sorted = group.sort_values(date_col)
        label = f"{site} - {char}"
        plt.plot(group_sorted[value_col], group_sorted[date_col], label=label)

    plt.title("Water Quality Characteristics Over Time (Switched Axes)")
    plt.xlabel("Measured Value")
    plt.ylabel("Date")
    plt.legend(title="Site - Characteristic", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.grid(True)
    plt.tight_layout()
    st.pyplot(plt)

# Plot stations on map based on filtered data
def plot_filtered_map(filtered_df):
    if 'LatitudeMeasure' not in filtered_df.columns or 'LongitudeMeasure' not in filtered_df.columns:
        st.warning("No location data to map.")
        return None
    unique_sites = filtered_df[['MonitoringLocationIdentifier', 'LatitudeMeasure', 'LongitudeMeasure']].drop_duplicates()
    unique_sites = unique_sites.dropna(subset=['LatitudeMeasure', 'LongitudeMeasure'])

    m = folium.Map(
        location=[unique_sites['LatitudeMeasure'].mean(), unique_sites['LongitudeMeasure'].mean()],
        zoom_start=6
    )
    for _, row in unique_sites.iterrows():
        folium.Marker(
            location=[row['LatitudeMeasure'], row['LongitudeMeasure']],
            popup=row['MonitoringLocationIdentifier']
        ).add_to(m)
    return m

# Streamlit app layout
def app():
    st.title("Contaminant Trend and Map Viewer")

    site_file = st.file_uploader("Upload Site Locations CSV", type="csv")
    if site_file is not None:
        sites = load_and_filter_sites(site_file)
        st.subheader("Stations with Monitoring Locations")
        map_display = plot_sites_on_map(sites)
        st_folium(map_display, width=700)

    contaminant_file = st.file_uploader("Upload Contaminant Data CSV", type="csv")
    if contaminant_file is not None:
        df = load_contaminant_data(contaminant_file)

        if 'CharacteristicName' not in df.columns:
            st.error("CSV must include a 'CharacteristicName' column.")
            return

        contaminants = df['CharacteristicName'].dropna().unique()
        contaminant = st.selectbox("Select Contaminant", contaminants)

        min_value = df['ResultMeasureValue'].min()
        max_value = df['ResultMeasureValue'].max()
        value_range = st.slider("Select Value Range", float(min_value), float(max_value), (float(min_value), float(max_value)))

        min_date = pd.to_datetime(df['ActivityStartDate'].min()).to_pydatetime()
        max_date = pd.to_datetime(df['ActivityStartDate'].max()).to_pydatetime()
        date_range = st.slider("Select Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date))

        filtered_df = filter_data(df, contaminant, value_range, date_range)

        st.subheader(f"Stations with the Selected Contaminant ({contaminant})")
        filtered_map = plot_filtered_map(filtered_df)
        if filtered_map:
            st_folium(filtered_map, width=700)

        st.subheader(f"Trend of {contaminant} Over Time")
        plot_dual_characteristics(filtered_df, [contaminant])

if __name__ == "__main__":
    app()
