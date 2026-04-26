# Import libraries
import requests
import csv
import os   #Claude taught me this, a way to check if a file already exists on my computer to avoid duplicates.
import json
from datetime import datetime, timedelta    #I used Claude here, I didn't know how to work with dates within my dataset

# ESPN MLB scoreboard API 
BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard"

# File names inside the final_project folder
csv_file = "final_project/rockies_games.csv"
json_file = "final_project/results.json"


#Function to check if the dates are part of the regular season games, Claude helped me work 
# with the datetime funtions because I didn't want to include spring training games in the analysis
def is_regular_season(date_str):
    date = datetime.strptime(date_str[:10], "%Y-%m-%d")

    if datetime(2025, 3, 28) <= date <= datetime(2025, 9, 28):
        return True

    if date >= datetime(2026, 3, 27):
        return True

    return False


existing_game_ids = set()  #load existing game ideas to avoid duplicates

if os.path.isfile(csv_file):  #will only read the file if it exists
    with open(csv_file, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            existing_game_ids.add(row["game_id"])


start_date = datetime(2025, 3, 28)  #Opening day of the 2025 baseball season
end_date = datetime.today()    #uses the datetime.today function to have up to date reports

dates_to_fetch = []
current = start_date
while current <= end_date:
    if is_regular_season(current.strftime("%Y-%m-%d")):   #converts to string
        dates_to_fetch.append(current.strftime("%Y%m%d"))
    current += timedelta(days=1)  #advacnes the date by one in the loop to get all the data

print(f"Fetching data for {len(dates_to_fetch)} regular season dates (this may take a moment)...")  


file_exists = os.path.isfile(csv_file)  #checks to see if the csv exists
new_games_added = 0    #marker variable
 
with open(csv_file, "a", newline="", encoding="utf-8") as file:   #Claude recommended added the encoding utf-8 to avoid a program crash in case there were non standard characters from the API data
    writer = csv.writer(file)

    # Write header row only if the file is brand new
    if not file_exists:
        writer.writerow([
            "game_id",
            "date",
            "opponent",
            "home_away",
            "rockies_score",
            "opponent_score",
            "result"
        ])

    for date_str in dates_to_fetch:
        # Call the API with the date parameter to get games on that day
        try:
            response = requests.get(BASE_URL, params={"dates": date_str})
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            print(f"API error on {date_str}: {e}")
            continue

        games = data.get("events", [])

        for game in games:
            game_name = game.get("name", "")

            # Only process  Colorado Rockies games
            if "Colorado Rockies" not in game_name:
                continue

            game_id = game["id"]

            # Skip if we already have this game saved to avoid duplicates
            if game_id in existing_game_ids:
                continue

            # Only save completed games so it doesn't show postponed or in progress games
            status = game["competitions"][0]["status"]["type"]["name"]
            if status != "STATUS_FINAL":
                print(f"Skipping in-progress or scheduled game on {date_str}.")
                continue

            game_date = game["date"]
            competitors = game["competitions"][0]["competitors"]   #this pulls the date and the Rockies and opponent from the API

            rockies_score = 0   #starts the variables as 0 or empty before data is added to them
            opponent_score = 0
            opponent_name = ""
            home_away = ""

            for team in competitors:  #loops through the Rockies and their opponent from all the games of the day
                team_name = team["team"]["displayName"]
                score = int(team["score"])  #converts the score to an integer
                location = team["homeAway"]

                if team_name == "Colorado Rockies":
                    rockies_score = score
                    home_away = location
                else:
                    opponent_name = team_name
                    opponent_score = score

            # Skip postponed or unplayed games (both scores are 0)
            if rockies_score == 0 and opponent_score == 0:
                print(f"Skipping postponed/unplayed game on {date_str}.")
                continue

           #display if the Rockies won, lost, or tied in the game
            if rockies_score > opponent_score:
                result = "Win"
            elif rockies_score < opponent_score:
                result = "Loss"
            else:
                result = "Tie"

            writer.writerow([    #Claude helped me here to save all the game data as one new row in the csv
                game_id,
                game_date,
                opponent_name,
                home_away,
                rockies_score,
                opponent_score,
                result
            ])

            existing_game_ids.add(game_id)  #adds the new game id so the game isn't added twice
            new_games_added += 1  #increment counter by one each time a game is added

print(f"Done fetching! {new_games_added} new game(s) added to the CSV.")  #shows how many new games were added.

#these are all variables to run analyses on the Rockies' performance, start all as empty variables
total_games = 0
wins = 0
losses = 0
runs_scored = 0
runs_allowed = 0

home_wins = 0
home_losses = 0
away_wins = 0
away_losses = 0

biggest_win_margin = 0
biggest_win_opponent = ""
biggest_loss_margin = 0
biggest_loss_opponent = ""

#create an empty dictionary to store the opponent's record
opponent_record = {}

#opens the file in read mode rather than append
with open(csv_file, "r", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    rows = list(reader)

#loops through the rows in the list to anaylze the Rockies' record home and away and the score margin
for row in rows:
    total_games += 1  #increase counter by 1 for every row
    rockies_score = int(row["rockies_score"])   #convert the score to integers to be able to make calculations
    opponent_score = int(row["opponent_score"])
    result = row["result"]
    home_away = row["home_away"]
    opponent = row["opponent"]
    margin = abs(rockies_score - opponent_score)  #run difference in the games (use abs so no neg.)

    runs_scored += rockies_score   #add the overall total runs scored for the rockies
    runs_allowed += opponent_score  #same but for the opponent's score

    # Win/loss totals calculations
    if result == "Win":
        wins += 1
    elif result == "Loss":
        losses += 1

    # Home vs. away breakdown to know how the Rockies perform based on the game location
    if result == "Win" and home_away == "home":
        home_wins += 1
    elif result == "Loss" and home_away == "home":
        home_losses += 1
    elif result == "Win" and home_away == "away":
        away_wins += 1
    elif result == "Loss" and home_away == "away":
        away_losses += 1

    # Biggest win and biggest loss (min/max analysis)
    if result == "Win" and margin > biggest_win_margin:  #if statement to find the biggest margin
        biggest_win_margin = margin  #if the new game has a higher scoring margin than the previous max it becomes new biggest win game
        biggest_win_opponent = opponent   #shows the opponent of that game
    if result == "Loss" and margin > biggest_loss_margin:
        biggest_loss_margin = margin  #if Rockies lose with new high margin
        biggest_loss_opponent = opponent  #tracks the opponent of that game

    # Track record against each opponent in the MLB
    if opponent not in opponent_record:  #if a new team for the first team
        opponent_record[opponent] = {"wins": 0, "losses": 0}
    if result == "Win":  #when the Rockies win add 1 win to their overall record against the team
        opponent_record[opponent]["wins"] += 1
    elif result == "Loss":   #when the Rockies lose add 1 loss to their overall record against the team
        opponent_record[opponent]["losses"] += 1

# Calculate averages and win percentage
if total_games > 0:   #this makes sure the total is greater than 0 to avoid errors (can't divide by 0)
    avg_runs_scored = round(runs_scored / total_games, 2)    #rounding two decimals
    avg_runs_allowed = round(runs_allowed / total_games, 2)
    win_percentage = round(wins / total_games, 3)
else:
    avg_runs_scored = 0
    avg_runs_allowed = 0
    win_percentage = 0

# Find current win/loss streak  Claude helped me here, I was stuck with figuring out how to loop through the data backwards to show the most recent data to find the current winning/losing streak
if rows:
    last_result = rows[-1]["result"]
    streak_count = 0
    for row in reversed(rows):  #reverse to loop through backwards
        if row["result"] == last_result:
            streak_count += 1  #increase the streak count if they win or lose multiples times in a row
        else:
            break
    current_streak_str = f"{streak_count} game {last_result.lower()} streak"
else:
    current_streak_str = "No games yet"

# Find best and hardest opponent (must play at least 2 games against the team)
best_opponent = ""
best_win_pct = -1   #set to impossible value so the real value will replace without any issues
worst_opponent = ""
worst_win_pct = 2   #set to impossible value so the real value will replace without any issues

for opp, record in opponent_record.items():  #loops through the dictionary and gives you the opponent and the record
    opp_total = record["wins"] + record["losses"]
    if opp_total < 2:  #skips if less than 2 games
        continue
    opp_win_pct = record["wins"] / opp_total  #keeps a running comparison
    if opp_win_pct > best_win_pct:  #if record against a team becomes the new best record it replaces the old data
        best_win_pct = opp_win_pct
        best_opponent = opp
    if opp_win_pct < worst_win_pct:  #if record against a team becomes the new worst record it replaces the old data
        worst_win_pct = opp_win_pct
        worst_opponent = opp

#save the results to a json file
results = {   #start dictionary
    "team": "Colorado Rockies",
    "analysis_last_run": datetime.today().strftime("%Y-%m-%d"),   #using datetime.today function to get most current data and converts to a string to know when it was last run
    "overall_record": {  #shows record with details, total games, wins, losses, and win %
        "total_games": total_games,
        "wins": wins,
        "losses": losses,
        "win_percentage": win_percentage
    },
    "scoring": {   #scoring and details, avg runs scored and allowed and total runs scored and allowed
        "average_runs_scored": avg_runs_scored,
        "average_runs_allowed": avg_runs_allowed,
        "total_runs_scored": runs_scored,
        "total_runs_allowed": runs_allowed
    },
    "home_away_split": {   #shows overall performance both home and away
        "home_wins": home_wins,
        "home_losses": home_losses,
        "away_wins": away_wins,
        "away_losses": away_losses
    },
    "notable_games": {  #notable games for the Rockies, both good and bad
        "biggest_win": {#shows the biggest win and who the Rockies were playing
            "margin": biggest_win_margin,
            "opponent": biggest_win_opponent
        },
        "biggest_loss": {  #shows the biggest loss and who the Rockies were playing
            "margin": biggest_loss_margin,
            "opponent": biggest_loss_opponent
        }
    },
    "current_streak": current_streak_str,  #shows the current streak calculated above
    "opponent_matchups": opponent_record,
    "best_matchup": {  #which team the Rockies beat the most (%), shows team name and win% against them rounded
        "opponent": best_opponent,
        "win_percentage_vs_them": round(best_win_pct, 3) if best_opponent else None  #if there is no best opponent it will display none to avoid errors.
    },
    "toughest_matchup": {
        "opponent": worst_opponent,  #which team the Rockies lose to the most in terms of winning %
        "win_percentage_vs_them": round(worst_win_pct, 3) if worst_opponent else None   #if there is no worst opponent it will display none to avoid errors.
    }
}

with open(json_file, "w", encoding="utf-8") as file:  #opens the JSON in write mode to add the analysis
    json.dump(results, file, indent=5)  #coverts the dictionary to a JSON file with the lines spaced out

#print a summary to the user (basically all the same data saved to the JSON file but printed)
print("\n===== Colorado Rockies Regular Season Analysis =====")  #title
print(f"Record: {wins}-{losses} ({win_percentage:.1%} win rate)")  #overall record and win %
print(f"Home: {home_wins}-{home_losses} | Away: {away_wins}-{away_losses}")  #home and away records
print(f"Avg runs scored: {avg_runs_scored} | Avg runs allowed: {avg_runs_allowed}")  #avg runs scored and allowed
print(f"Biggest win: +{biggest_win_margin} vs {biggest_win_opponent}")   #best win/opponent
print(f"Biggest loss: -{biggest_loss_margin} vs {biggest_loss_opponent}") #worst loss/opponent
print(f"Current streak: {current_streak_str}") #winning/losing streak
if best_opponent: #best matchup
    print(f"Best matchup: {best_opponent} ({best_win_pct:.1%} win rate)")
if worst_opponent: #worst matchup
    print(f"Toughest matchup: {worst_opponent} ({worst_win_pct:.1%} win rate)")
print(f"\nAnalysis saved to {json_file}") #let the user know the data was saved in a json
