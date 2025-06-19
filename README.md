# nba-dashboard

🏀 NBA Stats Dashboard
This is a Streamlit-powered web application designed to provide interactive access to NBA player statistics. Users can explore various statistical categories for league leaders and view detailed career breakdowns for individual players.

✨ Features
League Leaders: View the top players in different statistical categories for the 2024-2025 NBA season. (Note: This feature was part of the original request and is included, though it was noted as potentially having issues during development.)

Player Search: Search for any NBA player active in the 2024-2025 season.

Detailed Career Stats: For selected players, display their season-by-season statistics in a tabular format.

Per-Game Charting: Visualize a player's season-by-season per-game averages for Points, Rebounds, and Assists using interactive line charts.

Clean Data Presentation: Handles cases where players might have played for multiple teams in a season by prioritizing 'Total' (TOT) stats for a unified season entry.

🛠️ Technologies Used
Python: The core programming language.

Streamlit: For building the interactive web application interface.

nba_api: An unofficial NBA API client for fetching data directly from stats.nba.com.

Pandas: For data manipulation and analysis.

🚀 Setup and Installation
To run this dashboard locally, follow these steps:

Clone or Download the Project:
Save the nba_dashboard.py file to your local machine.

Create a requirements.txt file:
In the same directory as nba_dashboard.py, create a new file named requirements.txt and add the following content to it:

streamlit
nba_api
pandas

Create a Virtual Environment (Recommended):

python -m venv nba_env
source nba_env/bin/activate  # On Windows: .\nba_env\Scripts\activate

Install Dependencies:
Install all required Python libraries from the requirements.txt file. This is the most reliable way to ensure all dependencies are met.

pip install -r requirements.txt --upgrade --no-cache-dir

🏃 How to Run the Dashboard
Navigate to the Project Directory:
Open your terminal or command prompt and change your current directory to where you saved nba_dashboard.py and requirements.txt.

cd path/to/your/nba_dashboard_project

Run the Streamlit Application:

streamlit run nba_dashboard.py

This command will open the NBA Stats Dashboard in your default web browser.

💡 Usage
Use the dropdown to select a player active in the 2024-2025 season. Their career statistics, broken down by season, will be displayed in a table, along with charts visualizing their per-game averages over the years.

