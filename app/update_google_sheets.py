import gspread
import re
import os
from fuzzywuzzy import fuzz
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

client = get_gspread_client()

# Google Sheets IDs
DAILY_REPORT_ID = "1xLysLjaHLvXl7BxtnO3xZZoxseICjeYgRrgWgnuTMLM"
DAILY_COVERAGE_ID = "1vIpDw6erO5dO8IlMfoQlvfSS8fVd76WSaj28uwEZwuk"
MASTER_SCHEDULE_ID = "12XNbaa4AvahxYxR7D6Qa6DfrEeZPgrSiTTo5V9uFTsg"

def clean_teacher_name(name):
    """
    Cleans the teacher name string by removing any newlines and extra information.
    Assumes name is in the format "Last, First" (or similar).
    """
    name = re.sub(r'\n.*', '', name).strip()
    parts = name.split(',')
    if len(parts) >= 2:
        return f"{parts[0].strip()}, {parts[1].strip()}"
    return name

def clean_sub_name(name):
    """
    Cleans the substitute name string by removing phone numbers and extra whitespace.
    """
    name = re.sub(r'\(\d{3}\) \d{3}-\d{4}', '', name).strip()
    return name

def find_teacher_in_master(teacher_name, master_data):
    """
    Finds a matching teacher row in the master schedule data using fuzzy matching.
    Expects the teacher's name to be in the first column of master_data.
    """
    highest_ratio = 0
    best_match = None
    
    # Cache lowercased teacher names from master data (skip header if present)
    # Assuming that master_data might include a header row; adjust the slicing if needed.
    for row in master_data[1:]:
        if row and row[0]:
            lowercased_name = row[0].lower()
            ratio = fuzz.ratio(teacher_name.lower(), lowercased_name)
            if ratio > highest_ratio and ratio > 85:
                highest_ratio = ratio
                best_match = row
    return best_match

def main():
    try:
        client = get_gspread_client()
        # Set header row for the daily_coverage sheet
        coverage_header = ["Teacher/TA", "HR", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Subs", "Duration"]

        # Open all sheets
        daily_report_sheet = client.open_by_key(DAILY_REPORT_ID).sheet1
        daily_coverage_sheet = client.open_by_key(DAILY_COVERAGE_ID).sheet1
        master_schedule_sheet = client.open_by_key(MASTER_SCHEDULE_ID).sheet1

        # Get raw data from daily_report (which has no header row)
        daily_report_data = daily_report_sheet.get_all_values()
        master_schedule_data = master_schedule_sheet.get_all_values()

        # Filter valid absence rows:
        # We expect valid rows to have data in column C (index 2). (Adjust filtering as needed.)
        valid_rows = [row for row in daily_report_data if len(row) > 2 and row[2].strip()]

        update_data = [coverage_header]

        for row in valid_rows:
            # Extract data using fixed column positions:
            # Column C (index 2): Teacher info
            # Column F (index 5): Duration
            # Column I (index 8): Substitute info
            teacher_raw = row[2] if len(row) > 2 else ""
            duration_raw = row[5] if len(row) > 5 else ""
            sub_raw = row[8] if len(row) > 8 else ""

            # Clean the extracted data
            teacher_name = clean_teacher_name(teacher_raw)
            sub_name = clean_sub_name(sub_raw)
            duration = duration_raw.strip()

            # Initialize a new row for daily_coverage (13 columns total)
            new_row = [""] * 13
            new_row[0] = teacher_name       # Teacher/TA in column A
            new_row[12] = duration          # Duration in column M
            new_row[11] = sub_name          # Substitute info in column L

            # Look up the teacher's schedule in the master schedule
            master_row = find_teacher_in_master(teacher_name, master_schedule_data)
            if master_row:
                # Copy columns B through K (indices 1 to 10) from the master schedule row into daily_coverage
                for i in range(1, 11):
                    if i < len(master_row):
                        new_row[i] = master_row[i]
            update_data.append(new_row)

        # Clear existing data on daily_coverage and update with the new data
        daily_coverage_sheet.clear()
        if len(update_data) > 1:
            daily_coverage_sheet.update(values=update_data, range_name='A1', value_input_option='USER_ENTERED')
            print(f"✅ Successfully updated {len(update_data)-1} rows in daily_coverage!")
        else:
            print("⚠️ No data to update in daily_coverage")
            
    except gspread.exceptions.APIError as e:
        print(f"❌ Google Sheets API error occurred: {str(e)}")
    except gspread.exceptions.SpreadsheetNotFound as e:
        print(f"❌ Spreadsheet not found: {str(e)}")
    except gspread.exceptions.WorksheetNotFound as e:
        print(f"❌ Worksheet not found: {str(e)}")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()
