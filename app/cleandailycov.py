import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import re

# === Configuration ===
SERVICE_ACCOUNT_FILE = "/Users/bmcmanus/Documents/coverage_pulled_apart/teacher-absence-tracking/app/credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Google Sheets IDs
DAILY_COVERAGE_ID = "1vIpDw6erO5dO8IlMfoQlvfSS8fVd76WSaj28uwEZwuk"
MASTER_SCHEDULE_ID = "12XNbaa4AvahxYxR7D6Qa6DfrEeZPgrSiTTo5V9uFTsg"

# === Authentication ===
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

# === Callable main() function ===
def main():
    # Open the spreadsheets.
    daily_coverage_sheet = client.open_by_key(DAILY_COVERAGE_ID).sheet1
    master_schedule_sheet = client.open_by_key(MASTER_SCHEDULE_ID).sheet1

    # Load data.
    daily_coverage_data = daily_coverage_sheet.get_all_values()
    master_schedule_data = master_schedule_sheet.get_all_values()

    # Convert to DataFrame, skipping header row.
    df = pd.DataFrame(daily_coverage_data[1:], columns=daily_coverage_data[0])

    # For reference (if needed).
    valid_teachers = {row[0].split(',')[0].strip(): row[0] for row in master_schedule_data[1:] if row}

    # --- Helper Functions ---
    def clean_teacher_name(name):
        match = re.match(r"([^,]+,\s+\S+)", name)  # Keeps "Last, First"
        return match.group(0) if match else name

    def clean_sub_name(name):
        return re.sub(r"\(\d{3}\) \d{3}-\d{4}", "", name).strip()

    # This function ensures that cells containing these non-teaching blocks are preserved.
    def should_replace_with_sub(cell):
        if cell in ["Prep", "Plan/Duty", "Duty/Plan", "Lunch"] or re.match(r"w/\s*\w+", cell):
            return False
        return True

    # Apply cleaning functions.
    df["Teacher/TA"] = df["Teacher/TA"].apply(clean_teacher_name)
    df["Subs"] = df["Subs"].apply(clean_sub_name)

    # Replace cell values with "sub" where appropriate (for periods columns C-K).
    for col in df.columns[2:11]:
        df[col] = df[col].apply(lambda x: "sub" if should_replace_with_sub(x) else x)

    # Sort the DataFrame.
    teachers_with_schedule = df[df.iloc[:, 2:].notna().any(axis=1)]
    teachers_without_schedule = df[~df.index.isin(teachers_with_schedule.index)]
    sorted_df = pd.concat([teachers_with_schedule, teachers_without_schedule.sort_values(by="Teacher/TA")])

    # Rebuild the data with header.
    updated_data = [daily_coverage_data[0]] + sorted_df.values.tolist()

    # Update the sheet with cleaned data.
    daily_coverage_sheet.clear()
    daily_coverage_sheet.update(updated_data)
    print("✅ daily_coverage cleaned and updated successfully!")

    # === Apply Dark Gray Fill to Target Cells ===
    # Define the dark gray color (RGB values in 0–1 range; adjust if needed).
    dark_gray_fill = {"red": 0.41, "green": 0.41, "blue": 0.41}

    # Build a list of formatting requests.
    requests = []
    sheet_id = daily_coverage_sheet.id
    num_rows = len(updated_data)
    num_cols = len(updated_data[0])
    target_values = {"4", "Prep", "Plan/Duty", "Duty/Plan", "Lunch"}

    # Iterate over each cell.
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
        daily_coverage_sheet.spreadsheet.batch_update({"requests": requests})
        print("✅ Applied dark gray fill to target cells.")
    else:
        print("No target cells found for formatting.")

# Allow the function to be callable when imported.
if __name__ == "__main__":
    main()
