import os
import gspread
import update_google_sheets
import manual_load
import daily_utils  # Import the utility module
from google.oauth2.service_account import Credentials
from flask import Flask, render_template, redirect, url_for, request, flash

def get_gspread_client():
    """Initialize and return an authorized Google Sheets client."""
    try:
        service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(service_account_file, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Error initializing Google Sheets client: {e}")
        raise
    
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-key")  # Needed for flash messages

PERIOD_OPTIONS = ["HR", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

# Use the function from daily_utils
get_teacher_names = daily_utils.get_teacher_names

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/update")
def update():
    try:
        update_google_sheets.main()
        flash("Google Sheets updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating Google Sheets: {e}", "danger")
    return redirect(url_for("home"))

@app.route("/clean")
def clean():
    try:
        if daily_utils.clean_daily_coverage():
            flash("Daily Coverage cleaned successfully!", "success")
        else:
            flash("Error cleaning Daily Coverage (No data or other issue). Check logs.", "danger")
    except Exception as e:
        flash(f"Error cleaning Daily Coverage: {e}", "danger")  # Handle any unexpected errors.
    return redirect(url_for("home"))

# Updating the Flask redirect in dashboard.py
@app.route("/manual", methods=["GET", "POST"])
def manual():
    if request.method == "POST":
        teacher_name = request.form.get("teacher_name")
        duration = request.form.get("duration")
        sub_name = request.form.get("sub_name", "")
        periods = request.form.getlist("periods")
        
        try:
            manual_load.add_manual_absence(teacher_name, duration, periods, sub_name)
            flash("Manual absence added successfully!", "success")
        except Exception as e:
            flash(f"Error adding manual absence: {e}", "danger")
        
        return redirect(url_for("home"))  # Redirect to dashboard instead of reloading manual
    
    teacher_names = get_teacher_names()
    return render_template("manual.html", teacher_names=teacher_names, period_options=PERIOD_OPTIONS)
if __name__ == "__main__":
    app.run(debug=True)
