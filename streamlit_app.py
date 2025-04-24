import streamlit as st
import pandas as pd
import folium
import matplotlib.pyplot as plt
from folium.plugins import MarkerCluster
from datetime import datetime
from streamlit_folium import st_folium  # Updated import

# Load and filter sites (Part 1)
def load_and_filter_sites(file_path):
    df = pd.read_csv(file_path, dtype=str)

    # Convert lat/lon to numeric (may contain missing or invalid data)
    df['LatitudeMeasure'] = pd.to_numeric(df['LatitudeMeasure'], errors='coerce')
    df['LongitudeMeasure'] = pd.to_numeric(df['LongitudeMeasure'], errors='coerce')

    # Filter for water quality monitoring sites (remove duplicates by location)
    unique_sites = df.drop_duplicates(subset=['MonitoringLocationName', 'LatitudeMeasure', 'LongitudeMeasure'])

    # Drop rows with missing coordinates
    unique_sites = unique_sites.dropna(subset=['LatitudeMeasure', 'LongitudeMeasure'])

    return unique_sites

def plot_sites_on_map(sites_df):
    if sites_df.empty:
        raise ValueError("No valid monitoring sites to plot.")

    # Center the map around the mean location
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

def load_contaminant_data(file_path):
    df = pd.read_csv(file_path)

    df['ResultMeasureValue'] = pd.to_numeric(df['ResultMeasureValue'], errors='coerce')
    df['ActivityStartDate'] = pd.to_datetime(df['ActivityStartDate'], errors='coerce')

    return df

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

    return filtered_df

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

def plot_filtered_map(filtered_df):
    unique_sites = filtered_df[['MonitoringLocationIdentifier', 'LatitudeMeasure', 'LongitudeMeasure']].drop_duplicates()

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

def app():
    st.title("Contaminant Trend and Map Viewer")

    site_file = st.file_uploader("Upload Site Locations CSV", type="csv")
    if site_file is not None:
        sites = load_and_filter_sites(site_file)
        st.subheader("Stations with Monitoring Locations")
        map_display = plot_sites_on_map(sites)
        st_folium(map_display, returned_objects=[])

    contaminant_file = st.file_uploader("Upload Contaminant Data CSV", type="csv")
    if contaminant_file is not None:
        df = load_contaminant_data(contaminant_file)

        contaminants = df['CharacteristicName'].unique()
        contaminant = st.selectbox("Select Contaminant", contaminants)

        min_value = df['ResultMeasureValue'].min()
        max_value = df['ResultMeasureValue'].max()
        value_range = st.slider("Select Value Range", min_value, max_value, (min_value, max_value))

        # Convert timestamps to native datetime for slider
        min_date = df['ActivityStartDate'].min().to_pydatetime()
        max_date = df['ActivityStartDate'].max().to_pydatetime()
        date_range = st.slider(
            "Select Date Range",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD"
        )

        filtered_df = filter_data(df, contaminant, value_range, date_range)

        st.subheader(f"Stations with the Selected Contaminant ({contaminant})")
        map_display = plot_filtered_map(filtered_df)
        st_folium(map_display, returned_objects=[])

        st.subheader(f"Trend of {contaminant} Over Time")
        plot_dual_characteristics(filtered_df, [contaminant])

if __name__ == "__main__":
    app()
