import os
import gspread
from google.oauth2.service_account import Credentials

def get_gspread_client():
    """Initialize and return an authorized Google Sheets client."""
    try:
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(service_account_file, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Error initializing Google Sheets client: {e}")
        raise
    
# Google Sheets IDs
DAILY_COVERAGE_ID = os.getenv("DAILY_COVERAGE_ID")
MASTER_SCHEDULE_ID = os.getenv("MASTER_SCHEDULE_ID")

client = get_gspread_client()
daily_coverage_sheet = client.open_by_key(DAILY_COVERAGE_ID).sheet1
master_schedule_sheet = client.open_by_key(MASTER_SCHEDULE_ID).sheet1

FILL_VALUE = "NSN"  # Placeholder for inactive periods


def find_teacher_in_master(teacher_name, master_schedule_data):
    for row in master_schedule_data:
        if row and row[0] == teacher_name:
            return row
    return None


def add_manual_absence(teacher_name, duration, periods, sub_name=""):
    """Adds a manual absence entry to the daily_coverage sheet."""
    client = get_gspread_client()
    daily_coverage_sheet = client.open_by_key(DAILY_COVERAGE_ID).sheet1
    master_schedule_sheet = client.open_by_key(MASTER_SCHEDULE_ID).sheet1

    master_schedule_data = master_schedule_sheet.get_all_values()
    master_row = find_teacher_in_master(teacher_name, master_schedule_data)

    if not master_row:
        print(f"❌ Teacher {teacher_name} not found in master schedule")
        return

    try:
        def apply_full_day(master_row, new_row):
            new_row[1:11] = master_row[1:11]

        def apply_half_day_am(master_row, new_row):
            new_row[1:7] = master_row[1:7]
            new_row[7:11] = ["NSN"] * 4

        def apply_half_day_pm(master_row, new_row):
            new_row[1:6] = ["NSN"] * 5
            new_row[6:11] = master_row[6:11]

        def apply_periods(master_row, new_row, periods):
            for i in range(1, 11):
                new_row[i] = master_row[i] if str(i) in periods else "NSN"

        period_mapping = {
            "Full Day": apply_full_day,
            "Half Day AM": apply_half_day_am,
            "Half Day PM": apply_half_day_pm,
            "Period": apply_periods,
        }

        new_row = [""] * 13  # Initialize row
        new_row[0] = teacher_name  # Set teacher's name in column A

        if duration == "Period":
            period_mapping[duration](master_row, new_row, periods)
        else:
            period_mapping[duration](master_row, new_row)

        new_row[11] = sub_name  # Substitute name
        new_row[12] = duration  # Duration

        daily_coverage_sheet.append_row(new_row, value_input_option='USER_ENTERED')
        print(f"✅ Added manual absence for {teacher_name}")
    except Exception as e:
        print(f"❌ Error adding manual absence: {e}")
        raise
