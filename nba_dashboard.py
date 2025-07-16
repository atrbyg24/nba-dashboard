import streamlit as st
import pandas as pd
from nba_api.stats.endpoints import (
    leaguestandings, leaguedashplayerstats, leaguedashteamstats, teamgamelog
)
import plotly.express as px

st.set_page_config(layout="wide", page_title="NBA Dashboard")

# --- Data Caching (to avoid refetching data on every interaction) ---
@st.cache_data
def load_standings(season):
    try:
        data = leaguestandings.LeagueStandings(season=season).get_data_frames()[0]
        return data
    except Exception as e:
        st.error(f"Error loading standings data for {season}: {e}")
        return pd.DataFrame()

@st.cache_data
def load_player_stats(season):
    try:
        data = leaguedashplayerstats.LeagueDashPlayerStats(season=season).get_data_frames()[0]
        return data
    except Exception as e:
        st.error(f"Error loading player statistics for {season}: {e}")
        return pd.DataFrame()

@st.cache_data
def load_team_stats(season):
    try:
        data = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]
        return data
    except Exception as e:
        st.error(f"Error loading team statistics for {season}: {e}")
        return pd.DataFrame()

@st.cache_data
def load_team_game_log(team_id, season):
    try:
        data = teamgamelog.TeamGameLog(team_id=team_id, season=season).get_data_frames()[0]
        return data
    except Exception as e:
        st.error(f"Error loading game log for team {team_id} in {season}: {e}")
        return pd.DataFrame()

# --- Sidebar for global controls ---
st.sidebar.header("NBA Dashboard Controls")
# Example seasons: 2023-24 is the current active season.
season_options = [f"{i}-{i+1}" for i in range(2023, 2010, -1)]
selected_season = st.sidebar.selectbox("Select Season", season_options, index=0)

# --- Main Dashboard Layout ---
st.title("Interactive NBA Dashboard")

# --- Tabbed Interface ---
tab1, tab2, tab3, tab4 = st.tabs(["Team Standings", "Player Statistics", "Team Comparison", "Trends & Distributions"])

with tab1:
    st.header(f"NBA Team Standings ({selected_season} Season)")
    with st.spinner("Loading standings..."):
        standings_df = load_standings(selected_season)
    if not standings_df.empty:
        standings_df['W_PCT'] = pd.to_numeric(standings_df['W_PCT'])
        st.dataframe(standings_df[['TEAM_NAME', 'W', 'L', 'W_PCT', 'CONF_RANK', 'DIV_RANK', 'HOME_RECORD', 'ROAD_RECORD']].sort_values(by='W_PCT', ascending=False))
    else:
        st.warning("No standings data available for the selected season. Please try another season or check your connection.")

with tab2:
    st.header(f"Top Player Statistics ({selected_season} Season)")
    with st.spinner("Loading player statistics..."):
        player_stats_df = load_player_stats(selected_season)

    if not player_stats_df.empty:
        # Filter out NaN/inf values from potential statistics before offering them for selection
        available_stats = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'AST_PCT', 'USG_PCT', 'PLUS_MINUS']
        # Ensure selected stats are present and valid in the dataframe
        valid_stats = [stat for stat in available_stats if stat in player_stats_df.columns and pd.api.types.is_numeric_dtype(player_stats_df[stat])]

        if not valid_stats:
            st.warning("No valid numeric statistics found for plotting.")
        else:
            stat_choice = st.selectbox("Select Statistic", valid_stats)
            top_n = st.slider("Show Top N Players", 5, 50, 10)

            # Sort and display, handling potential NaN values in the chosen stat
            sorted_players = player_stats_df.sort_values(by=stat_choice, ascending=False).head(top_n)
            st.dataframe(sorted_players[['PLAYER_NAME', 'TEAM_ABBREVIATION', stat_choice, 'GP', 'MIN']])

            fig_player_stats = px.bar(sorted_players, x='PLAYER_NAME', y=stat_choice,
                                      title=f"Top {top_n} Players by {stat_choice}",
                                      labels={'PLAYER_NAME': 'Player', stat_choice: stat_choice},
                                      hover_data=['TEAM_ABBREVIATION', 'GP', 'MIN'])
            st.plotly_chart(fig_player_stats)
    else:
        st.warning("No player statistics data available for the selected season. Please try another season.")

with tab3:
    st.header(f"Team Performance Comparison ({selected_season} Season)")
    with st.spinner("Loading team statistics..."):
        team_stats_df = load_team_stats(selected_season)

    if not team_stats_df.empty:
        team_names = team_stats_df['TEAM_NAME'].tolist()
        if len(team_names) < 2:
            st.info("Not enough teams available for comparison in this season.")
        else:
            team1_name = st.selectbox("Select Team 1", team_names, index=0)
            # Ensure team2 default is different from team1, if possible
            default_index_team2 = 1 if len(team_names) > 1 and team_names[0] == team1_name else 0
            team2_name = st.selectbox("Select Team 2", team_names, index=default_index_team2 if default_index_team2 < len(team_names) else 0)

            if team1_name == team2_name:
                st.warning("Please select two different teams for comparison.")
            else:
                team1_data = team_stats_df[team_stats_df['TEAM_NAME'] == team1_name].iloc[0]
                team2_data = team_stats_df[team_stats_df['TEAM_NAME'] == team2_name].iloc[0]

                comparison_stats = ['PTS', 'REB', 'AST', 'FG_PCT', 'FT_PCT', 'FG3_PCT', 'OFF_RATING', 'DEF_RATING']
                # Filter comparison_stats to only include those present in the dataframe
                valid_comparison_stats = [stat for stat in comparison_stats if stat in team1_data.index and stat in team2_data.index]

                if not valid_comparison_stats:
                    st.warning("No common valid statistics found for comparison.")
                else:
                    comparison_df = pd.DataFrame({
                        team1_name: [team1_data[stat] for stat in valid_comparison_stats],
                        team2_name: [team2_data[stat] for stat in valid_comparison_stats]
                    }, index=valid_comparison_stats)
                    st.dataframe(comparison_df.transpose())

                    comparison_melted = comparison_df.reset_index().melt(id_vars='index', var_name='Team', value_name='Value')
                    fig_team_comp = px.bar(comparison_melted, x='index', y='Value', color='Team', barmode='group',
                                           title=f"Comparison of {team1_name} vs {team2_name}",
                                           labels={'index': 'Statistic', 'Value': 'Value'})
                    st.plotly_chart(fig_team_comp)
    else:
        st.warning("No team statistics data available for the selected season. Please try another season.")

with tab4:
    st.header("Team Trends & Player Distributions")

    # Team Win/Loss Trends
    st.subheader("Team Win/Loss Trend Over Season")
    # Ensure standings_df is not empty before attempting to get team names
    if not standings_df.empty:
        team_names_for_trend = standings_df['TEAM_NAME'].tolist()
        if team_names_for_trend: # Check if the list is not empty
            selected_trend_team = st.selectbox(
                "Select Team for Trend",
                team_names_for_trend,
                index=0
            )

            if selected_trend_team:
                # Use .get() with default to prevent KeyError if team not found (though unlikely here)
                # Or ensure a row exists before accessing .iloc[0]
                team_row = standings_df[standings_df['TEAM_NAME'] == selected_trend_team]
                if not team_row.empty:
                    team_id = team_row['TEAM_ID'].iloc[0]
                    with st.spinner(f"Loading game log for {selected_trend_team}..."):
                        game_log_df = load_team_game_log(team_id, selected_season)

                    if not game_log_df.empty:
                        game_log_df['GAME_DATE'] = pd.to_datetime(game_log_df['GAME_DATE'])
                        game_log_df = game_log_df.sort_values(by='GAME_DATE')
                        game_log_df['Cumulative_W'] = game_log_df['WL'].apply(lambda x: 1 if x == 'W' else 0).cumsum()
                        game_log_df['Cumulative_L'] = game_log_df['WL'].apply(lambda x: 1 if x == 'L' else 0).cumsum()

                        fig_trend = px.line(game_log_df, x='GAME_DATE', y=['Cumulative_W', 'Cumulative_L'],
                                            title=f"{selected_trend_team} Cumulative Wins/Losses ({selected_season})",
                                            labels={'value': 'Count', 'variable': 'Result', 'GAME_DATE': 'Date'})
                        st.plotly_chart(fig_trend)
                    else:
                        st.info(f"No game log data available for {selected_trend_team} in the selected season.")
                else:
                    st.warning(f"Could not find team ID for {selected_trend_team}.")
            else:
                st.info("Please select a team to view trends.")
        else:
            st.info("No teams available in standings to select for trend analysis.")
    else:
        st.warning("Standings data not available to load team names for trend analysis.")


    # Player Stat Distribution
    st.subheader("Player Statistic Distribution")
    if not player_stats_df.empty:
        # Filter for numeric columns to avoid errors with non-numeric data in histogram
        numeric_player_cols = player_stats_df.select_dtypes(include=['number']).columns.tolist()
        dist_stat_options = [stat for stat in ['PTS', 'REB', 'AST', 'MIN', 'AGE'] if stat in numeric_player_cols]

        if not dist_stat_options:
            st.warning("No suitable numeric player statistics found for distribution analysis.")
        else:
            dist_stat_choice = st.selectbox("Select Statistic for Distribution", dist_stat_options)
            fig_dist = px.histogram(player_stats_df, x=dist_stat_choice,
                                    title=f"Distribution of Player {dist_stat_choice} ({selected_season})",
                                    labels={dist_stat_choice: dist_stat_choice},
                                    nbins=20)
            st.plotly_chart(fig_dist)
    else:
        st.warning("No player statistics data available for distribution analysis.")