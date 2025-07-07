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
    data = leaguestandings.LeagueStandings(season=season).get_data_frames()[0]
    return data

@st.cache_data
def load_player_stats(season):
    data = leaguedashplayerstats.LeagueDashPlayerStats(season=season).get_data_frames()[0]
    return data

@st.cache_data
def load_team_stats(season):
    data = leaguedashteamstats.LeagueDashTeamStats(season=season).get_data_frames()[0]
    return data

@st.cache_data
def load_team_game_log(team_id, season):
    data = teamgamelog.TeamGameLog(team_id=team_id, season=season).get_data_frames()[0]
    return data

# --- Sidebar for global controls ---
st.sidebar.header("NBA Dashboard Controls")
selected_season = st.sidebar.selectbox("Select Season", [f"{i}-{i+1}" for i in range(2023, 2010, -1)], index=0) # Example seasons

# --- Main Dashboard Layout ---
st.title("Interactive NBA Dashboard")

# --- Tabbed Interface ---
tab1, tab2, tab3, tab4 = st.tabs(["Team Standings", "Player Statistics", "Team Comparison", "Trends & Distributions"])

with tab1:
    st.header(f"NBA Team Standings ({selected_season} Season)")
    standings_df = load_standings(selected_season)
    if not standings_df.empty:
        st.dataframe(standings_df[['TEAM_NAME', 'W', 'L', 'W_PCT', 'CONF_RANK', 'DIV_RANK', 'HOME_RECORD', 'ROAD_RECORD']].sort_values(by='W_PCT', ascending=False))
    else:
        st.warning("No standings data available for the selected season.")

with tab2:
    st.header(f"Top Player Statistics ({selected_season} Season)")
    player_stats_df = load_player_stats(selected_season)

    if not player_stats_df.empty:
        stat_choice = st.selectbox("Select Statistic", ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG_PCT', 'AST_PCT', 'USG_PCT', 'PLUS_MINUS'])
        top_n = st.slider("Show Top N Players", 5, 50, 10)

        sorted_players = player_stats_df.sort_values(by=stat_choice, ascending=False).head(top_n)
        st.dataframe(sorted_players[['PLAYER_NAME', 'TEAM_ABBREVIATION', stat_choice, 'GP', 'MIN']])

        fig_player_stats = px.bar(sorted_players, x='PLAYER_NAME', y=stat_choice,
                                  title=f"Top {top_n} Players by {stat_choice}",
                                  labels={'PLAYER_NAME': 'Player', stat_choice: stat_choice},
                                  hover_data=['TEAM_ABBREVIATION', 'GP', 'MIN'])
        st.plotly_chart(fig_player_stats)
    else:
        st.warning("No player statistics data available for the selected season.")

with tab3:
    st.header(f"Team Performance Comparison ({selected_season} Season)")
    team_stats_df = load_team_stats(selected_season)

    if not team_stats_df.empty:
        team_names = team_stats_df['TEAM_NAME'].tolist()
        team1_name = st.selectbox("Select Team 1", team_names, index=0)
        team2_name = st.selectbox("Select Team 2", team_names, index=1)

        team1_data = team_stats_df[team_stats_df['TEAM_NAME'] == team1_name].iloc[0]
        team2_data = team_stats_df[team_stats_df['TEAM_NAME'] == team2_name].iloc[0]

        comparison_stats = ['PTS', 'REB', 'AST', 'FG_PCT', 'FT_PCT', 'FG3_PCT', 'OFF_RATING', 'DEF_RATING']
        comparison_df = pd.DataFrame({
            team1_name: [team1_data[stat] for stat in comparison_stats],
            team2_name: [team2_data[stat] for stat in comparison_stats]
        }, index=comparison_stats)
        st.dataframe(comparison_df.transpose())

        # Radar chart for comparison (conceptual, requires more complex Plotly go)
        # For simplicity, let's use a grouped bar chart
        comparison_melted = comparison_df.reset_index().melt(id_vars='index', var_name='Team', value_name='Value')
        fig_team_comp = px.bar(comparison_melted, x='index', y='Value', color='Team', barmode='group',
                               title=f"Comparison of {team1_name} vs {team2_name}",
                               labels={'index': 'Statistic', 'Value': 'Value'})
        st.plotly_chart(fig_team_comp)
    else:
        st.warning("No team statistics data available for the selected season.")

with tab4:
    st.header("Team Trends & Player Distributions")

    # Team Win/Loss Trends
    st.subheader("Team Win/Loss Trend Over Season")
    team_names_for_trend = standings_df['TEAM_NAME'].tolist() if not standings_df.empty else []
    selected_trend_team = st.selectbox("Select Team for Trend", team_names_for_trend, index=0 if team_names_for_trend else None)

    if selected_trend_team:
        team_id = standings_df[standings_df['TEAM_NAME'] == selected_trend_team]['TEAM_ID'].iloc[0]
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
        st.info("Please select a team to view trends.")

    # Player Stat Distribution
    st.subheader("Player Statistic Distribution")
    if not player_stats_df.empty:
        dist_stat_choice = st.selectbox("Select Statistic for Distribution", ['PTS', 'REB', 'AST', 'MIN', 'AGE'])
        fig_dist = px.histogram(player_stats_df, x=dist_stat_choice,
                                title=f"Distribution of Player {dist_stat_choice} ({selected_season})",
                                labels={dist_stat_choice: dist_stat_choice},
                                nbins=20)
        st.plotly_chart(fig_dist)
    else:
        st.warning("No player statistics data available for distribution analysis.")
