import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import leagueleaders, playercareerstats, commonplayerinfo
from nba_api.stats.static import players

# --- Configuration ---
st.set_page_config(layout="wide", page_title="NBA Stats Dashboard")

# --- Helper Functions with Caching ---

@st.cache_data
def get_all_nba_players():
    """Fetches a list of all NBA players."""
    return players.get_players()

@st.cache_data
def get_league_leaders(stat_category):
    """
    Fetches league leaders for a given stat category.
    :param stat_category: The stat category to retrieve (e.g., 'PTS', 'AST', 'REB').
    """
    try:
        leaders = leagueleaders.LeagueLeaders(stat_category=stat_category, season='2023-24') # Default to current season
        df = leaders.get_data_frames()[0]
        # Rename columns for better readability if necessary
        df.columns = [col.replace('_', ' ').title() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Error fetching league leaders for {stat_category}: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

@st.cache_data
def get_player_career_stats(player_id):
    """
    Fetches career statistics for a given player ID.
    :param player_id: The ID of the NBA player.
    """
    try:
        career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
        # Regular season totals and per game stats are often in the first two dataframes
        df_totals = career_stats.get_data_frames()[0]
        df_per_game = career_stats.get_data_frames()[1]

        # Combine or select relevant columns. For simplicity, let's just show per game.
        df_per_game.columns = [col.replace('_', ' ').title() for col in df_per_game.columns]
        return df_per_game
    except Exception as e:
        st.error(f"Error fetching career stats for player ID {player_id}: {e}")
        return pd.DataFrame() # Return empty DataFrame on error

@st.cache_data
def get_player_info(player_id):
    """
    Fetches basic information for a given player ID.
    :param player_id: The ID of the NBA player.
    """
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        df = info.get_data_frames()[0]
        return df.iloc[0] # Return the first (and only) row as a Series
    except Exception as e:
        st.error(f"Error fetching player info for player ID {player_id}: {e}")
        return pd.Series() # Return empty Series on error

# --- Main Application Logic ---

def main():
    st.title("🏀 NBA Stats Dashboard")

    st.markdown("""
        Explore NBA player statistics, including league leaders and individual career stats.
    """)

    # Sidebar for filters and navigation
    st.sidebar.header("Navigation & Filters")
    analysis_type = st.sidebar.radio(
        "Select Analysis Type:",
        ("League Leaders", "Player Search")
    )

    if analysis_type == "League Leaders":
        st.header("🏆 League Leaders (2023-24 Season)")
        st.write("Displays the top players for selected statistical categories.")

        stat_categories = {
            "Points": "PTS",
            "Assists": "AST",
            "Rebounds": "REB",
            "Steals": "STL",
            "Blocks": "BLK",
            "Minutes Played": "MIN",
            "Field Goal Percentage": "FG_PCT",
            "3-Point Percentage": "FG3_PCT",
            "Free Throw Percentage": "FT_PCT",
            "Turnovers": "TOV"
        }
        selected_stat_name = st.sidebar.selectbox(
            "Select Stat Category:",
            list(stat_categories.keys())
        )
        selected_stat_code = stat_categories[selected_stat_name]

        leaders_df = get_league_leaders(selected_stat_code)

        if not leaders_df.empty:
            # Display relevant columns for leaders
            display_cols = [
                'Rank', 'Player', 'Team', 'Games Played', 'Min', selected_stat_name.replace(' ', '')
            ]
            # Ensure columns exist before trying to display them
            display_cols = [col for col in display_cols if col in leaders_df.columns]

            st.dataframe(leaders_df[display_cols], use_container_width=True)
        else:
            st.warning("No data available for league leaders.")

    elif analysis_type == "Player Search":
        st.header("🔍 Player Career Statistics")
        st.write("Search for an NBA player to view their career stats.")

        all_players = get_all_nba_players()
        player_names = sorted([player['full_name'] for player in all_players])

        selected_player_name = st.sidebar.selectbox(
            "Search for a Player:",
            [""] + player_names # Add an empty option
        )

        if selected_player_name:
            player_info = next((p for p in all_players if p['full_name'] == selected_player_name), None)

            if player_info:
                player_id = player_info['id']
                st.subheader(f"Stats for {selected_player_name}")

                # Display player's general info
                info_series = get_player_info(player_id)
                if not info_series.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Team:** {info_series.get('Team Name', 'N/A')}")
                        st.write(f"**Position:** {info_series.get('Position', 'N/A')}")
                        st.write(f"**Height:** {info_series.get('Height', 'N/A')}")
                    with col2:
                        st.write(f"**Weight:** {info_series.get('Weight', 'N/A')}")
                        st.write(f"**Draft:** {info_series.get('Draft Year', 'N/A')} {info_series.get('Draft Round', 'N/A')}. {info_series.get('Draft Number', 'N/A')}.")
                        st.write(f"**College:** {info_series.get('College', 'N/A')}")
                    st.markdown("---")


                career_df = get_player_career_stats(player_id)

                if not career_df.empty:
                    # Filter out unnecessary columns if present (e.g., Player ID, Team ID)
                    cols_to_drop = ['Player Id', 'Team Id', 'League Id'] # Common irrelevant columns
                    career_df = career_df.drop(columns=[col for col in cols_to_drop if col in career_df.columns], errors='ignore')

                    st.dataframe(career_df, use_container_width=True)

                    # Basic Charting for career average points, rebounds, assists
                    st.subheader("Career Per Game Averages Over Seasons")
                    chart_data = career_df[['Season Id', 'Pts', 'Reb', 'Ast']].set_index('Season Id')
                    st.line_chart(chart_data)
                else:
                    st.warning(f"No career statistics available for {selected_player_name}.")
            else:
                st.warning("Player not found. Please try a different name.")
        else:
            st.info("Select a player from the dropdown to see their career statistics.")

if __name__ == "__main__":
    main()