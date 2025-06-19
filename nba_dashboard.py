# Import necessary libraries
import streamlit as st
import pandas as pd
import base64
import time # Import time for rate limiting
from nba_api.stats.static import players
from nba_api.stats.endpoints import playercareerstats

# --- Configuration and Data Loading ---

# Set page title and favicon
st.set_page_config(
    page_title="NBA Player Stats Dashboard",
    page_icon="🏀",
    layout="wide", # Use wide layout for better data display
    initial_sidebar_state="expanded" # Keep sidebar expanded by default
)

# Function to load NBA player stats data from nba_api
@st.cache_data
def load_data(season_year=2023):
    """
    Loads NBA player statistics for a given season from the nba_api.
    Fetches career stats for all active players and extracts data for the specified season.
    """
    # Get all active players from the static players module
    nba_players = players.get_active_players()
    all_season_stats = []
    player_count = 0
    total_players = len(nba_players)

    st.info(f"Fetching NBA player stats for the {season_year}-{str(season_year+1)[-2:]} season using nba_api... This might take a while due to API rate limits ({total_players} players).")
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Format the season ID to match NBA API's convention (e.g., "2023-24")
    target_season_id = f"{season_year}-{str(season_year+1)[-2:]}"

    for player_dict in nba_players:
        player_id = player_dict['id']
        player_full_name = player_dict['full_name']
        player_position = player_dict.get('position', 'N/A') # Get position from static player info

        try:
            # Fetch career stats for each player
            # The PlayerCareerStats endpoint returns data for all seasons a player has played.
            career = playercareerstats.PlayerCareerStats(player_id=player_id)

            # The get_data_frames() method returns a list of DataFrames.
            # 'SeasonTotalsRegularSeason' (index 0) typically contains the per-season stats.
            career_df = career.get_data_frames()[0]

            # Filter the DataFrame to get only the data for the target season
            season_data = career_df[career_df['SEASON_ID'] == target_season_id]

            if not season_data.empty:
                # Convert the single row of season data to a dictionary
                stats = season_data.iloc[0].to_dict()

                # Map NBA API column names to dashboard expected names
                player_stats = {
                    'Player': player_full_name,
                    'Player_ID': player_id, # Keeping player_id for potential future use/debugging
                    'Team': stats.get('TEAM_ABBREVIATION', 'N/A'),
                    'Position': player_position, # Use position from static players module
                    'Age': stats.get('PLAYER_AGE', None), # PlayerCareerStats includes PLAYER_AGE
                    'Games Played': stats.get('GP', 0),
                    'Points': stats.get('PTS', 0.0),
                    'Assists': stats.get('AST', 0.0),
                    'Rebounds': stats.get('REB', 0.0),
                    'Steals': stats.get('STL', 0.0),
                    'Blocks': stats.get('BLK', 0.0)
                }
                all_season_stats.append(player_stats)

        except Exception as e:
            # Catch exceptions for individual player API calls (e.g., player has no stats for season,
            # or temporary API issues). Print a warning but continue processing other players.
            st.warning(f"Could not fetch data for player {player_full_name} (ID: {player_id}): {e}. Skipping this player.")

        player_count += 1
        # Update progress bar and status text
        progress = player_count / total_players
        progress_bar.progress(progress)
        status_text.text(f"Fetching data for {player_count}/{total_players} players...")

        # Respect API rate limits (e.g., 0.6 seconds pause between requests)
        time.sleep(0.6)

    df = pd.DataFrame(all_season_stats)

    # Post-processing to ensure correct data types and handle potential missing values
    numeric_cols = ['Games Played', 'Points', 'Assists', 'Rebounds', 'Steals', 'Blocks']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Handle Age column: convert to numeric and fill any remaining NaNs
    if 'Age' in df.columns:
        df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
        # Fill missing ages with a default (e.g., 25) or the median of available ages
        df['Age'] = df['Age'].fillna(value=df['Age'].median() if not df['Age'].isnull().all() else 25).astype(int)
    else:
        # If 'Age' column somehow doesn't exist, create it with a default
        df['Age'] = 25


    st.success(f"Successfully loaded {len(df)} player stats for the {season_year}-{str(season_year+1)[-2:]} season using nba_api!")
    # Clear the progress bar and status text once loading is complete
    progress_bar.empty()
    status_text.empty()
    return df

# Load the data
df = load_data()

# --- Helper Function for Download Link ---
def create_download_link(df_to_download, filename="nba_player_stats.csv"):
    """
    Generates a link to download the given DataFrame as a CSV file.
    """
    csv = df_to_download.to_csv(index=False).encode('utf-8')
    b64 = base64.b64encode(csv).decode()  # bytes <-> string
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">Download Data as CSV</a>'
    return href

# --- Streamlit App Layout ---

st.title("🏀 NBA Player Stats Dashboard")
st.markdown("""
This dashboard displays key statistics for NBA players.
The data is fetched from the **unofficial NBA.com API via the `nba_api` Python library** for the 2023-2024 season.
Due to the nature of the API, data loading might take a moment as it fetches stats for each player.
Use the filters on the sidebar to explore the data.
""")

# --- Sidebar Filters ---
st.sidebar.header("Filter Options")

# Check if DataFrame is empty before trying to access unique values
if not df.empty:
    # Team Selection
    # Ensure 'Team' column exists and handle potential 'N/A' values
    if 'Team' in df.columns and not df['Team'].empty:
        sorted_teams = sorted(df['Team'].unique())
        selected_team = st.sidebar.multiselect('Select Team(s)', sorted_teams, sorted_teams)
    else:
        st.sidebar.warning("Team data not available for filtering.")
        selected_team = [] # Empty list to filter nothing

    # Position Selection
    if 'Position' in df.columns and not df['Position'].empty:
        sorted_positions = sorted(df['Position'].unique())
        selected_position = st.sidebar.multiselect('Select Position(s)', sorted_positions, sorted_positions)
    else:
        st.sidebar.warning("Position data not available for filtering.")
        selected_position = [] # Empty list to filter nothing

    # Age Slider - Only show if 'Age' column has valid data
    if 'Age' in df.columns and not df['Age'].isnull().all():
        # Ensure min/max values are sensible, handle cases where all ages are the same
        min_age_val = int(df['Age'].min())
        max_age_val = int(df['Age'].max())
        if min_age_val == max_age_val: # If all ages are the same, make slider range 5 years around it
            min_age = max(18, min_age_val - 2)
            max_age = min_age_val + 2
        else:
            min_age = min_age_val
            max_age = max_age_val

        age_range = st.sidebar.slider(
            'Filter by Age',
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age)
        )
    else:
        st.sidebar.info("Age data not fully available from API for filtering players accurately.")
        age_range = (0, 100) # Set a wide range to not filter anything if age is missing

    # Points Slider
    # Ensure 'Points' column is numeric and not empty before getting min/max
    if 'Points' in df.columns and not df['Points'].empty:
        min_points, max_points = float(df['Points'].min()), float(df['Points'].max())
        if min_points == max_points: # If all points are the same, provide a small range
            min_points = max(0.0, min_points - 5.0)
            max_points = min_points + 5.0
        points_range = st.sidebar.slider(
            'Filter by Points (per game)',
            min_value=min_points,
            max_value=max_points,
            value=(min_points, max_points),
            step=0.1
        )
    else:
        st.sidebar.warning("Points data not available for filtering.")
        points_range = (0.0, 100.0) # Wide range

    # --- Apply Filters ---
    # Apply filters only if the corresponding selection lists/ranges are not empty
    df_filtered = df.copy() # Start with a copy to avoid modifying the original cached DataFrame

    if selected_team:
        df_filtered = df_filtered[df_filtered['Team'].isin(selected_team)]
    if selected_position:
        df_filtered = df_filtered[df_filtered['Position'].isin(selected_position)]
    if 'Age' in df_filtered.columns: # Check if Age column exists after initial filtering
        df_filtered = df_filtered[
            (df_filtered['Age'] >= age_range[0]) & (df_filtered['Age'] <= age_range[1])
        ]
    if 'Points' in df_filtered.columns: # Check if Points column exists
        df_filtered = df_filtered[
            (df_filtered['Points'] >= points_range[0]) & (df_filtered['Points'] <= points_range[1])
        ]

else:
    st.warning("Data could not be loaded from the NBA API. Please check your internet connection or try again later.")
    df_filtered = pd.DataFrame() # Ensure df_filtered is empty if df is empty

# --- Display Data ---

st.subheader("Player Statistics Table")

if df_filtered.empty:
    st.warning("No players match the selected filters or no data was loaded. Please adjust your selections or check the API.")
else:
    st.dataframe(df_filtered.style.highlight_max(axis=0, subset=['Points', 'Assists', 'Rebounds', 'Steals', 'Blocks']), use_container_width=True)

    # --- Download Filtered Data ---
    st.markdown("---")
    st.subheader("Download Data")
    st.markdown(create_download_link(df_filtered), unsafe_allow_html=True)

    # --- Basic Statistics ---
    st.markdown("---")
    st.subheader("Summary Statistics for Filtered Players")
    st.write(df_filtered.describe())

    # --- Simple Visualizations (Example: Top Scorers) ---
    st.markdown("---")
    st.subheader("Top Players by Points")

    # Ensure df_filtered has enough rows for top_n selection
    if not df_filtered.empty:
        top_n_max = min(20, len(df_filtered)) # Limit max slider value
        top_n = st.slider("Show Top N Players", 1, top_n_max, min(10, top_n_max)) # Default to min of 10 or available players
        df_top_scorers = df_filtered.sort_values(by='Points', ascending=False).head(top_n)

        # Using st.bar_chart for a simple visualization
        if not df_top_scorers.empty:
            st.bar_chart(df_top_scorers.set_index('Player')['Points'])
        else:
            st.info("Not enough data to create chart for top players.")
    else:
        st.info("No data available to create chart for top players.")


    # --- More detailed visualization (example: scatter plot for Age vs Points) ---
    st.markdown("---")
    st.subheader("Age vs. Points (Scatter Plot)")
    # Ensure 'Age' and 'Points' are numeric for the scatter plot and drop NaNs
    df_plot = df_filtered.dropna(subset=['Age', 'Points'])

    if not df_plot.empty:
        st.scatter_chart(df_plot, x='Age', y='Points', size='Games Played', color='Team')
    else:
        st.info("Not enough valid 'Age' and 'Points' data to create scatter plot.")