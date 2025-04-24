import streamlit as st
import pandas as pd
import folium
import matplotlib.pyplot as plt
from folium.plugins import MarkerCluster
from datetime import datetime
from streamlit_folium import folium_static

# Load and filter sites (Part 1)
def load_and_filter_sites(file_path):
    df = pd.read_csv(file_path, dtype=str)  # Read everything as string first

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

    # Add markers for each site
    for _, row in sites_df.iterrows():
        folium.Marker(
            location=[row['LatitudeMeasure'], row['LongitudeMeasure']],
            popup=row['MonitoringLocationName']
        ).add_to(m)

    return m

# Load the contaminant data (Part 2)
def load_contaminant_data(file_path):
    df = pd.read_csv(file_path)
    
    # Ensure correct data types for filtering
    df['ResultMeasureValue'] = pd.to_numeric(df['ResultMeasureValue'], errors='coerce')
    df['ActivityStartDate'] = pd.to_datetime(df['ActivityStartDate'], errors='coerce')
    
    return df

# Filter contaminant data based on user input
def filter_data(df, contaminant, value_range, date_range):
    # Filter by contaminant
    filtered_df = df[df['CharacteristicName'] == contaminant]
    
    # Filter by value range
    filtered_df = filtered_df[(filtered_df['ResultMeasureValue'] >= value_range[0]) & 
                               (filtered_df['ResultMeasureValue'] <= value_range[1])]
    
    # Convert date range to pandas Timestamps to avoid datetime comparison issues
    date_range = [pd.to_datetime(date) for date in date_range]
    
    # Filter by date range
    filtered_df = filtered_df[(filtered_df['ActivityStartDate'] >= date_range[0]) & 
                               (filtered_df['ActivityStartDate'] <= date_range[1])]
    
    return filtered_df

# Plot the dual characteristics with switched axes
def plot_dual_characteristics(df, characteristics):
    if not (1 <= len(characteristics) <= 2):
        raise ValueError("Please specify one or two characteristics.")
    
    # Column name assumptions
    date_col = 'ActivityStartDate'
    site_col = 'MonitoringLocationIdentifier'
    value_col = 'ResultMeasureValue'
    char_col = 'CharacteristicName'

    # Convert dates
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col, value_col, site_col, char_col])

    # Filter for desired characteristics
    df_filtered = df[df[char_col].isin(characteristics)]

    plt.figure(figsize=(12, 6))

    # Assign a color per site-characteristic pair
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
    # Get unique stations for the selected contaminant
    unique_sites = filtered_df[['MonitoringLocationIdentifier', 'LatitudeMeasure', 'LongitudeMeasure']].drop_duplicates()

    # Create the map
    m = folium.Map(location=[unique_sites['LatitudeMeasure'].mean(), unique_sites['LongitudeMeasure'].mean()], zoom_start=6)

    # Add markers for each site
    for _, row in unique_sites.iterrows():
        folium.Marker(
            location=[row['LatitudeMeasure'], row['LongitudeMeasure']],
            popup=row['MonitoringLocationIdentifier']
        ).add_to(m)

    return m

# Streamlit app layout
def app():
    st.title("Contaminant Trend and Map Viewer")
    
    # File Upload for Site Locations (Part 1)
    site_file = st.file_uploader("Upload Site Locations CSV", type="csv")
    if site_file is not None:
        sites = load_and_filter_sites(site_file)
        # Display the map with station locations
        st.subheader("Stations with Monitoring Locations")
        map_display = plot_sites_on_map(sites)
        folium_static(map_display)

    # File Upload for Contaminant Data (Part 2)
    contaminant_file = st.file_uploader("Upload Contaminant Data CSV", type="csv")
    if contaminant_file is not None:
        df = load_contaminant_data(contaminant_file)
        
        # Show available contaminants
        contaminants = df['CharacteristicName'].unique()
        contaminant = st.selectbox("Select Contaminant", contaminants)
        
        # Select value range
        min_value = df['ResultMeasureValue'].min()
        max_value = df['ResultMeasureValue'].max()
        value_range = st.slider("Select Value Range", min_value, max_value, (min_value, max_value))
        
        # Select date range
        min_date = df['ActivityStartDate'].min()
        max_date = df['ActivityStartDate'].max()
        date_range = st.slider("Select Date Range", min_date, max_date, (min_date, max_date))
        
        # Filter the data based on the selected ranges
        filtered_df = filter_data(df, contaminant, value_range, date_range)
        
        # Display the map with station locations filtered by contaminant
        st.subheader(f"Stations with the Selected Contaminant ({contaminant})")
        map_display = plot_filtered_map(filtered_df)
        folium_static(map_display)
        
        # Plot the trend of the contaminant over time at different stations
        st.subheader(f"Trend of {contaminant} Over Time")
        plot_dual_characteristics(filtered_df, [contaminant])

# Run the Streamlit app
if __name__ == "__main__":
    app()
