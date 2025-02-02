import pdfplumber
import csv
import sys
import os

# Ensure Automator is passing the file
if len(sys.argv) < 2 or not sys.argv[1]:
    print("❌ Error: No PDF file was provided by Automator.")
    sys.exit(1)

pdf_path = sys.argv[1]

# Verify that the file exists
if not os.path.exists(pdf_path):
    print(f"❌ Error: The file '{pdf_path}' does not exist.")
    sys.exit(1)

# Define output CSV path
output_csv = "/Users/bmcmanus/Documents/coverage_pulled_apart/teacher-absence-tracking/data/Aesop - Daily Report.csv"

# Extract table data from PDF
with pdfplumber.open(pdf_path) as pdf:
    with open(output_csv, "w", newline="") as f:
        writer = csv.writer(f)
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table:
                    writer.writerow(row)

print(f"✅ CSV saved at: {output_csv}")
