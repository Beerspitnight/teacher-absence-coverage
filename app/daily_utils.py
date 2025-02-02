import gspread
import os
import pandas as pd
import re
from google.oauth2.service_account import Credentials

# === Configuration ===
def get_gspread_client():
    """Initialize and return an authorized Google Sheets client."""
    try:
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(service_account_file, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Error initializing Google Sheets client: {e}")
        raise

# Gspread client and Google Sheets IDs
DAILY_COVERAGE_ID = os.getenv("DAILY_COVERAGE_ID")
MASTER_SCHEDULE_ID = os.getenv("MASTER_SCHEDULE_ID")
TEACHER_LIST_ID = os.getenv("TEACHER_LIST_ID")

client = get_gspread_client()
daily_coverage_sheet = client.open_by_key(DAILY_COVERAGE_ID).sheet1
master_schedule_sheet = client.open_by_key(MASTER_SCHEDULE_ID).sheet1
teacher_list_sheet = client.open_by_key(TEACHER_LIST_ID).sheet1

# === Data Cleaning Functions ===
def clean_teacher_name(name):
    """Clean teacher name to 'Last, First' format."""
    match = re.match(r"([^,]+,\s+\S+)", name)
    return match.group(0) if match else name

def clean_sub_name(name):
    """Remove phone numbers and extra whitespace from substitute name."""
    return re.sub(r"\(\d{3}\) \d{3}-\d{4}", "", name).strip()

def should_replace_with_sub(cell):
    """Check if a cell value should be replaced with 'sub'."""
    if cell in ["Prep", "Plan/Duty", "Duty/Plan", "Lunch", "NSN"] or re.match(r"w/\s*\w+", cell):
        return False
    return True

# === Sheet Access Functions ===
def get_sheet_data(client, sheet_id):
    """Get all values from a Google Sheet."""
    try:
        sheet = client.open_by_key(sheet_id).sheet1
        return sheet.get_all_values()
    except Exception as e:
        print(f"❌ Error getting sheet data: {e}")
        raise

def get_teacher_names():
    """Get list of teacher names from teacher list sheet."""
    try:
        client = get_gspread_client()
        teacher_sheet = client.open_by_key(TEACHER_LIST_ID).sheet1
        teacher_data = teacher_sheet.col_values(1)
        if teacher_data and teacher_data[0].lower() in ["teacher", "name"]:
            return teacher_data[1:]
        return teacher_data
    except Exception as e:
        print(f"❌ Error loading teacher list: {e}")
        return []

# === Data Processing Functions ===
def process_daily_coverage_data(data):
    """Process and clean daily coverage data."""
    if not data:
        return None, None
    
    # Convert to DataFrame, skipping header row
    df = pd.DataFrame(data[1:], columns=data[0])
    
    # Clean teacher and sub names
    df["Teacher/TA"] = df["Teacher/TA"].apply(clean_teacher_name)
    df["Subs"] = df["Subs"].apply(clean_sub_name)
    
    # Replace cell values with "sub" where appropriate
    for col in df.columns[2:11]:
        df[col] = df[col].apply(lambda x: "sub" if should_replace_with_sub(x) else x)
    
    # Sort the DataFrame
    teachers_with_schedule = df[df.iloc[:, 2:].notna().any(axis=1)]
    teachers_without_schedule = df[~df.index.isin(teachers_with_schedule.index)]
    sorted_df = pd.concat([teachers_with_schedule, teachers_without_schedule.sort_values(by="Teacher/TA")])
    
    # Rebuild the data with header
    return [data[0]] + sorted_df.values.tolist()

# === Formatting Functions ===
def apply_cell_formatting(sheet, updated_data):
    """Apply dark gray fill to specific cells."""
    dark_gray_fill = {"red": 0.41, "green": 0.41, "blue": 0.41}
    requests = []
    sheet_id = sheet.id
    num_rows = len(updated_data)
    num_cols = len(updated_data[0])
    target_values = {"NSN", "Prep", "Plan/Duty", "Duty/Plan", "Lunch"}

    for i in range(num_rows):
        for j in range(num_cols):
            if updated_data[i][j] in target_values:
                requests.append({
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_id,
                            "startRowIndex": i,
                            "endRowIndex": i + 1,
                            "startColumnIndex": j,
                            "endColumnIndex": j + 1
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": dark_gray_fill
                            }
                        },
                        "fields": "userEnteredFormat.backgroundColor"
                    }
                })

    if requests:
        sheet.spreadsheet.batch_update({"requests": requests})
        return True
    return False

# === Main Operations ===
def clean_daily_coverage():
    """Main function to clean and format daily coverage sheet."""
    try:
        client = get_gspread_client()
        daily_coverage_sheet = client.open_by_key(DAILY_COVERAGE_ID).sheet1
        
        # Load and process data
        daily_coverage_data = get_sheet_data(client, DAILY_COVERAGE_ID)
        updated_data = process_daily_coverage_data(daily_coverage_data)
        
        if updated_data:
            # Update sheet with cleaned data
            daily_coverage_sheet.clear()
            daily_coverage_sheet.update(updated_data)
            
            # Apply formatting
            if apply_cell_formatting(daily_coverage_sheet, updated_data):
                print("✅ Applied formatting to cells")
            
            print("✅ Daily coverage cleaned and updated successfully!")
            return True
    except Exception as e:
        print(f"❌ Error in clean_daily_coverage: {e}")
        raise
    
    return False