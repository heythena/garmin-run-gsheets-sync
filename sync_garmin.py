import os
import json
import datetime
from garminconnect import Garmin
from google.oauth2.service_account import Credentials
import gspread

def main():
    print("Starting Garmin Health Stats sync...")
    
    # 1. Get credentials from environment variables
    garmin_email = os.environ.get('GARMIN_EMAIL')
    garmin_password = os.environ.get('GARMIN_PASSWORD')
    google_creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    sheet_id = os.environ.get('SHEET_ID')
    
    if not all([garmin_email, garmin_password, google_creds_json, sheet_id]):
        print("❌ Missing required environment variables")
        return
    
    # 2. Connect to Garmin
    print("Connecting to Garmin...")
    try:
        garmin = Garmin(garmin_email, garmin_password)
        garmin.login()
        print("✅ Connected to Garmin")
    except Exception as e:
        print(f"❌ Failed to connect to Garmin: {e}")
        return
    
    # 3. Fetch Health Data for Today (NZ Time friendly)
    today = datetime.date.today().isoformat() # YYYY-MM-DD
    print(f"Fetching health stats for {today}...")
    
    try:
        # Get Sleep Data
        sleep_data = garmin.get_sleep_data(today)
        sleep_score = sleep_data.get('dailySleepDTO', {}).get('sleepScore', 0)

        # Get Training Readiness
        readiness_data = garmin.get_training_readiness(today)
        readiness_score = readiness_data[0].get('score', 0) if readiness_data else 0
        
        print(f"Stats found -> Sleep: {sleep_score}, Readiness: {readiness_score}")
    except Exception as e:
        print(f"❌ Failed to fetch health data: {e}")
        return

    # 4. Connect to Google Sheets
    print("Connecting to Google Sheets...")
    try:
        creds_dict = json.loads(google_creds_json)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        client = gspread.authorize(creds)
        
        # Opens by ID to avoid "Garmin Data" vs "Training Plan" naming confusion
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.get_worksheet(0) # Targets the first tab
        print("✅ Connected to Google Sheets")
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheets: {e}")
        return

    # 5. Find Today's Row and Update
    try:
        # Find the cell matching today's date in Column A
        cell = sheet.find(today)
        row_index = cell.row
        
        # UPDATE: Column H (8) for Sleep and Column I (9) for Readiness
        # We use update_cell to avoid overwriting your whole row
        sheet.update_cell(row_index, 8, sleep_score)
        sheet.update_cell(row_index, 9, readiness_score)
        
        print(f"🎉 Successfully updated Row {row_index} for {today}!")
    except gspread.exceptions.CellNotFound:
        print(f"❌ Could not find {today} in Column A. Ensure your date format is YYYY-MM-DD.")
    except Exception as e:
        print(f"❌ Error updating sheet: {e}")

if __name__ == "__main__":
    main()
