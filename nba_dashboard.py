import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import playercareerstats, commonplayerinfo, commonallplayers
from nba_api.stats.static import players

# --- Configuration ---
# Set up the Streamlit page layout to be wide for better data display
st.set_page_config(layout="wide", page_title="NBA Stats Dashboard")

# --- Helper Functions with Caching ---
# Caching data to prevent redundant API calls and speed up the application.
# Streamlit's cache_data decorator automatically handles data caching.

@st.cache_data
def get_all_nba_players():
    """
    Fetches a list of all NBA players (historical and current).
    This function is primarily a fallback or for general lookup,
    as `get_current_season_players` will be used for filtering.
    Returns:
        list: A list of dictionaries, each representing an NBA player.
    """
    try:
        return players.get_players()
    except Exception as e:
        st.error(f"Error fetching all NBA players: {e}")
        return []

@st.cache_data
def get_current_season_players():
    """
    Fetches a list of players active in the current NBA season (2024-2025).
    Uses the CommonAllPlayers endpoint with is_only_current_season=1.
    Returns:
        list: A list of dictionaries, each representing an NBA player active in the current season,
              or falls back to all historical players if an error occurs.
    """
    try:
        # Set is_only_current_season=1 to get players active in the current season.
        active_players_data = commonallplayers.CommonAllPlayers(is_only_current_season=1)
        df = active_players_data.get_data_frames()[0]
        
        # Clean up column names returned by the API for easier access
        df.columns = [col.replace('_', ' ').title() for col in df.columns]

        player_list = []
        for index, row in df.iterrows():
            # CommonAllPlayers typically returns 'PERSON_ID' and 'DISPLAY_FIRST_LAST'
            player_list.append({
                'id': row.get('Person Id'),
                'full_name': row.get('Display First Last')
            })
        # Filter out any entries where 'id' or 'full_name' might be None
        return [p for p in player_list if p['id'] is not None and p['full_name'] is not None]
    except Exception as e:
        st.error(f"Error fetching current season players: {e}")
        st.info("Falling back to all historical players for search due to API error. Please ensure your 'nba_api' is up to date.")
        # Fallback to all players if current season retrieval fails
        return get_all_nba_players()

@st.cache_data
def get_player_career_stats(player_id):
    """
    Fetches career statistics for a given NBA player ID across all seasons.
    
    Args:
        player_id (int): The ID of the NBA player.
    
    Returns:
        pandas.DataFrame: A DataFrame containing the player's career per-game stats.
    """
    try:
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        
        all_data_frames = career_stats.get_data_frames()
        
        for i, df in enumerate(all_data_frames):
            print(f"  DataFrame {i} (Head):")
            # Only print head if DataFrame is not empty
            if not df.empty:
                print(df.head())
            else:
                print("    (Empty DataFrame)")
            print("-" * 30)

        df_per_game = pd.DataFrame() # Initialize as empty
        
        found_per_game_df = False
        for df in all_data_frames:
            if not df.empty and 'SEASON_ID' in df.columns and 'PLAYER_ID' in df.columns and df['SEASON_ID'].nunique() > 1:
                df_per_game = df
                found_per_game_df = True
                break
            elif hasattr(career_stats, 'get_data_frames_names') and 'PerGame' in career_stats.get_data_frames_names():
                 df_per_game = all_data_frames[career_stats.get_data_frames_names().index('PerGame')]
                 found_per_game_df = True
                 break


        if not found_per_game_df and len(all_data_frames) > 1:
            df_per_game = all_data_frames[1]
        elif not found_per_game_df and len(all_data_frames) > 0:
            df_per_game = all_data_frames[0]
        elif df_per_game.empty: # If after all checks, it's still empty
             st.warning(f"No suitable career statistics DataFrame found for player ID {player_id}.")
             return pd.DataFrame()


        # Clean up column names for display
        df_per_game.columns = [col.replace('_', ' ').title() for col in df_per_game.columns]
        
        # Set 'Season Id' as the index for a clear season-by-season breakdown
        if 'Season Id' in df_per_game.columns:
            df_per_game = df_per_game.set_index('Season Id')
        elif 'Seasonid' in df_per_game.columns: # Sometimes it might be Seasonid (less common after title casing)
            df_per_game = df_per_game.set_index('Seasonid')


        return df_per_game
    except Exception as e:
        st.error(f"Error fetching career stats for player ID {player_id}: {e}")
        st.info("Please ensure your 'nba_api' library is up to date (`pip install --upgrade nba_api`).")
        return pd.DataFrame()

@st.cache_data
def get_player_info(player_id):
    """
    Fetches basic information for a given NBA player ID.
    
    Args:
        player_id (int): The ID of the NBA player.
    
    Returns:
        pandas.Series: A Series containing the player's general information,
                       or an empty Series if an error occurs.
    """
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        # The first DataFrame contains general player info
        df = info.get_data_frames()[0]
        # Clean up column names for consistency
        df.columns = [col.replace('_', ' ').title() for col in df.columns]

        return df.iloc[0] # Return the first (and only) row as a Series
    except Exception as e:
        st.error(f"Error fetching player info for player ID {player_id}: {e}")
        return pd.Series()

# --- Main Application Logic ---

def main():
    """
    The main function that sets up and runs the Streamlit NBA Stats Dashboard.
    """
    st.title("🏀 NBA Stats Dashboard")
    st.markdown("""
        Welcome to the NBA Stats Dashboard! Explore real-time NBA player statistics,
        including league leaders for various categories and detailed career stats for individual players.
    """)

    # Sidebar for navigation and user input
    st.sidebar.header("Navigation & Filters")
    st.header("🔍 Player Career Statistics (2024-25 Season Active Players)")
    st.write("Search for an NBA player active in the 2024-2025 season to view their career stats.")

    # Get only players active in the current season for the search dropdown
    active_season_players = get_current_season_players()
    player_names = sorted([player['full_name'] for player in active_season_players])

    selected_player_name = st.sidebar.selectbox(
        "Search for a Player:",
        [""] + player_names # Add an empty option as default
    )

    if selected_player_name:
        # Find the player ID from the selected name in the active season players list
        player_info_static = next((p for p in active_season_players if p['full_name'] == selected_player_name), None)

        if player_info_static:
            player_id = player_info_static['id']
            st.subheader(f"Stats for {selected_player_name}")

            # Display general player information
            info_series = get_player_info(player_id)
            if not info_series.empty:
                # Use columns to neatly arrange player information
                col1, col2 = st.columns(2)
                with col1:
                    # Attempt to get values with robustness for different column names
                    team_name = info_series.get('Team Name') or info_series.get('Team', 'N/A')
                    position = info_series.get('Position') or info_series.get('Player Position', 'N/A')
                    height = info_series.get('Player Height') or info_series.get('Height', 'N/A')
                    st.write(f"**Team:** {team_name}")
                    st.write(f"**Position:** {position}")
                    st.write(f"**Height:** {height}")
                with col2:
                    weight = info_series.get('Player Weight') or info_series.get('Weight', 'N/A')
                    draft_year = info_series.get('Draft Year', 'N/A')
                    draft_round = info_series.get('Draft Round', 'N/A')
                    draft_number = info_series.get('Draft Number', 'N/A')
                    school = info_series.get('School') or info_series.get('College', 'N/A') # Try both 'School' and 'College'
                    
                    st.write(f"**Weight:** {weight}")
                    st.write(f"**Draft:** {draft_year} Rd. {draft_round} Pick {draft_number}")
                    st.write(f"**College:** {school}") 
                st.markdown("---") # Visual separator

            # Fetch and display career statistics
            st.subheader("Season By Season Stats") # Added a subheader for clarity
            career_df = get_player_career_stats(player_id)

            if not career_df.empty:
                # Drop potentially irrelevant ID columns for cleaner display
                # Ensure 'Player Id', 'Team Id', 'League Id' are dropped if they exist AND are not the index.
                # Since Season Id is now the index, we need to be careful not to drop it.
                cols_to_drop = ['Player Id', 'Team Id', 'League Id']
                # Filter out columns to drop if they are NOT the index
                cols_to_drop_final = [col for col in cols_to_drop if col in career_df.columns and col != career_df.index.name]
                career_df = career_df.drop(columns=cols_to_drop_final, errors='ignore')

                st.dataframe(career_df, use_container_width=True)

                # Add a simple line chart for key per-game averages over seasons
                st.subheader("Career Per Game Averages Over Seasons")
                # Ensure the columns exist before attempting to plot
                
                season_totals_df = career_df.groupby(level=0).last()
                chart_data_per_game = pd.DataFrame(index=season_totals_df.index)
                for col in ['Pts', 'Reb', 'Ast']:
                    chart_data_per_game[col] = season_totals_df[col] / season_totals_df['Gp']
                    
                st.line_chart(chart_data_per_game)
            else:
                st.warning(f"No career statistics available for {selected_player_name}.")
        else:
            st.warning("Player not found in the NBA database for the current season. Please check the name and try again.")
    else:
        st.info("Select a player from the dropdown in the sidebar to view their career statistics.")

if __name__ == "__main__":
    main()
