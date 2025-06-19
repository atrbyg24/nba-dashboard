# Import necessary libraries
import streamlit as st
import pandas as pd
import base64
import time # Import time for rate limiting (though less critical with LeagueDashPlayerStats)

# Import nba_api modules
from nba_api.stats.static import players
from nba_api.stats.static import teams # To get team names/abbreviations
from nba_api.stats.endpoints import leaguedashplayerstats

# --- Configuration and Data Loading ---

# Set page title and favicon
st.set_page_config(
    page_title="NBA Player Stats Dashboard",
    page_icon="🏀",
    layout="wide", # Use wide layout for better data display
    initial_sidebar_state="expanded" # Keep sidebar expanded by default
)

# Cache all NBA players static data for quick lookup
@st.cache_data
def get_all_nba_players_static():
    return players.get_active_players()

# Cache all NBA teams static data for quick lookup
@st.cache_data
def get_all_nba_teams_static():
    return teams.get_teams()

# Function to load NBA player stats data from nba_api using LeagueDashPlayerStats
@st.cache_data
def load_data(season_year):
    """
    Loads NBA player statistics for a given season from the nba_api.
    Uses LeagueDashPlayerStats for efficient league-wide data retrieval.
    """
    # Get the season ID in "YYYY-YY" format (e.g., "2023-24")
    target_season_id = f"{season_year}-{str(season_year+1)[-2:]}"

    st.info(f"Fetching NBA player stats for the {target_season_id} season...")

    try:
        # Fetch league-wide player dashboard stats for the specified season
        # This endpoint provides per-game stats for all players in a season
        league_stats = leaguedashplayerstats.LeagueDashPlayerStats(
            season=target_season_id,
            per_mode_simple='PerGame', # Ensure per game averages
            # No need for measure_type_simple='Base' unless we need advanced stats later
        )

        # Get the first DataFrame from the endpoint results, which is PlayerStats
        df = league_stats.get_data_frames()[0]

        # Map NBA API column names to dashboard expected names
        df = df.rename(columns={
            'PLAYER_NAME': 'Player',
            'TEAM_ABBREVIATION': 'Team',
            'PLAYER_AGE': 'Age',
            'GP': 'Games Played',
            'PTS': 'Points',
            'AST': 'Assists',
            'REB': 'Rebounds',
            'STL': 'Steals',
            'BLK': 'Blocks',
            'PLAYER_ID': 'Player_ID' # Keep player ID for potential future use
        })

        # The LeagueDashPlayerStats endpoint does not directly provide 'Position'.
        # We'll map it using the static players data fetched earlier.
        all_nba_players_static = get_all_nba_players_static()

        # MODIFIED: Explicitly handle None or empty strings for position
        player_id_to_position = {}
        for p in all_nba_players_static:
            pos = p.get('position')
            # If position is None or an empty string after stripping whitespace, set it to 'N/A'
            player_id_to_position[p['id']] = pos if pos and pos.strip() != '' else 'N/A'

        df['Position'] = df['Player_ID'].map(player_id_to_position).fillna('N/A')


        # Post-processing to ensure correct data types and handle potential missing values
        numeric_cols = ['Games Played', 'Points', 'Assists', 'Rebounds', 'Steals', 'Blocks', 'Age']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Ensure Age is integer
        df['Age'] = df['Age'].astype(int)

        st.success(f"Successfully loaded {len(df)} player stats for the {target_season_id} season!")
        return df

    except Exception as e:
        st.error(f"Error fetching data from NBA API for season {target_season_id}: {e}")
        st.warning("Data might not be available for the selected season yet, or there was an issue with the API.")
        return pd.DataFrame() # Return empty DataFrame on error

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
The data is fetched from the **unofficial NBA.com API via the `nba_api` Python library**.
Select a season and use the filters on the sidebar to explore the data.
""")

# --- Sidebar Filters ---
st.sidebar.header("Filter Options")

# Season Year Selector
# NBA API LeagueDashPlayerStats generally has data from 2000-01 season onwards reliably.
current_year = pd.Timestamp.now().year
season_options = list(range(2000, current_year)) # Up to current year for recent seasons
selected_season_year = st.sidebar.selectbox('Select Season Year', sorted(season_options, reverse=True), index=0) # Default to most recent

# Load the data based on selected season
df = load_data(selected_season_year)

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
        min_age_val = int(df['Age'].min())
        max_age_val = int(df['Age'].max())
        # Ensure slider range is sensible even if min/max are the same
        if min_age_val == max_age_val:
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
    if 'Points' in df.columns and not df['Points'].empty:
        min_points, max_points = float(df['Points'].min()), float(df['Points'].max())
        # Ensure slider range is sensible even if min/max are the same
        if min_points == max_points:
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
    df_filtered = df.copy() # Start with a copy to avoid modifying the original cached DataFrame

    if selected_team:
        df_filtered = df_filtered[df_filtered['Team'].isin(selected_team)]
    if selected_position:
        df_filtered = df_filtered[df_filtered['Position'].isin(selected_position)]
    if 'Age' in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered['Age'] >= age_range[0]) & (df_filtered['Age'] <= age_range[1])
        ]
    if 'Points' in df_filtered.columns:
        df_filtered = df_filtered[
            (df_filtered['Points'] >= points_range[0]) & (df_filtered['Points'] <= points_range[1])
        ]

else:
    st.warning("Data could not be loaded for the selected season. Please check your internet connection or try a different season.")
    df_filtered = pd.DataFrame() # Ensure df_filtered is empty if df is empty

# --- Display Data ---

st.subheader("Player Statistics Table")

if df_filtered.empty:
    st.warning("No players match the selected filters or no data was loaded for the chosen season. Please adjust your selections or try a different season.")
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

    if not df_filtered.empty:
        top_n_max = min(20, len(df_filtered)) # Limit max slider value
        top_n = st.slider("Show Top N Players", 1, top_n_max, min(10, top_n_max))
        df_top_scorers = df_filtered.sort_values(by='Points', ascending=False).head(top_n)

        if not df_top_scorers.empty:
            st.bar_chart(df_top_scorers.set_index('Player')['Points'])
        else:
            st.info("Not enough data to create chart for top players.")
    else:
        st.info("No data available to create chart for top players.")

    # --- More detailed visualization (example: scatter plot for Age vs Points) ---
    st.markdown("---")
    st.subheader("Age vs. Points (Scatter Plot)")
    df_plot = df_filtered.dropna(subset=['Age', 'Points'])

    if not df_plot.empty:
        st.scatter_chart(df_plot, x='Age', y='Points', size='Games Played', color='Team')
    else:
        st.info("Not enough valid 'Age' and 'Points' data to create scatter plot.")
