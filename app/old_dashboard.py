# dashboard.py
from flask import Flask, render_template, redirect, url_for, request, flash
import update_google_sheets   # Make sure update_google_sheets.py defines a callable main() function.
import cleandailycov          # Make sure cleandailycov.py defines a callable main() function.
import manual_load            # Already used in your manual load code.
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Needed for flash messages

# For the manual load page, we need to load teacher names.
# This function is similar to the one we used in app.py.
SERVICE_ACCOUNT_FILE = "/Users/bmcmanus/Documents/coverage_pulled_apart/teacher-absence-tracking/app/credentials.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gs_client = gspread.authorize(creds)
TEACHER_LIST_ID = "1t9rbXT-CMJQEhbwYMOSdvMOrQfajwKS1lnkSyhBxUGw"
PERIOD_OPTIONS = ["HR", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

def get_teacher_names():
    try:
        teacher_sheet = gs_client.open_by_key(TEACHER_LIST_ID).sheet1
        teacher_data = teacher_sheet.col_values(1)
        # Skip header if present:
        if teacher_data and teacher_data[0].lower() in ["teacher", "name"]:
            teacher_data = teacher_data[1:]
        return teacher_data
    except Exception as e:
        print(f"Error loading teacher list: {e}")
        return []

# Home/dashboard page with links to each process.
@app.route("/")
def home():
    return render_template("dashboard.html")

# Route to run update_google_sheets
@app.route("/update")
def update():
    try:
        update_google_sheets.main()
        flash("Google Sheets updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating Google Sheets: {e}", "danger")
    return redirect(url_for("home"))

# Route to run cleandailycov
@app.route("/clean")
def clean():
    try:
        cleandailycov.main()  # Make sure your cleandailycov.py defines a main() function, or refactor its logic into one.
        flash("Daily Coverage cleaned successfully!", "success")
    except Exception as e:
        flash(f"Error cleaning Daily Coverage: {e}", "danger")
    return redirect(url_for("home"))

# Route for manual absence entry (similar to your current manual load form)
@app.route("/manual", methods=["GET", "POST"])
def manual():
    if request.method == "POST":
        teacher_name = request.form.get("teacher_name")
        duration = request.form.get("duration")
        sub_name = request.form.get("sub_name")
        periods = request.form.getlist("periods")  # Will be a list from checkboxes.
        try:
            manual_load.add_manual_absence(teacher_name, duration, periods, sub_name)
            flash("Manual absence added successfully!", "success")
        except Exception as e:
            flash(f"Error adding manual absence: {e}", "danger")
        return redirect(url_for("manual"))
    teacher_names = get_teacher_names()
    return render_template("manual.html", teacher_names=teacher_names, period_options=PERIOD_OPTIONS)

if __name__ == "__main__":
    app.run(debug=True)
