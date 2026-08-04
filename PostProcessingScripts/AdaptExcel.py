import os
import re
from datetime import datetime
import pandas as pd
from pathlib import Path


def update_excel_dates(root_folder_path, excel_filename):
    base_path = Path(root_folder_path)
    excel_path = base_path / excel_filename

    # Regular expression to match the pattern: ddmmyyyy_hhmmss-name
    # Group 1 captures the date/time string (e.g., 02062026_164943)
    folder_pattern = re.compile(r'^(\d{8}_\d{6})-(.+)$')

    matched_folders = []

    # 1. Scan the directory tree for matching folder names
    for current_path, directories, _ in os.walk(base_path):
        for directory in directories:
            match = folder_pattern.match(directory)
            if match:
                date_string = match.group(1)
                try:
                    # Parse string into a datetime object for accurate sorting
                    date_obj = datetime.strptime(date_string, "%d%m%Y_%H%M%S")

                    # Format as required: yyyy-mm-dd hh:mm:ss
                    formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")

                    matched_folders.append({
                        'original_name': directory,
                        'date_obj': date_obj,
                        'formatted_date': formatted_date
                    })
                except ValueError:
                    print(f"Warning: Could not parse timestamp from folder '{directory}'")

    # 2. Sort folders chronologically using the datetime object
    matched_folders.sort(key=lambda x: x['date_obj'])

    print(f"Detected and sorted {len(matched_folders)} valid folders.")

    # 3. Load and modify the Excel file
    if not excel_path.exists():
        print(f"Error: Excel file not found at {excel_path}")
        return

    try:
        # Read the Excel file
        df = pd.read_excel(excel_path)

        # Verify that the 'Date' column exists
        if 'Date' not in df.columns:
            print("Error: The Excel file does not contain a 'Date' column.")
            return

        # Warn if there is a mismatch between row count and folder count
        if len(df) != len(matched_folders):
            print(f"Warning: Excel has {len(df)} rows, but {len(matched_folders)} folders were found.")
            print("Rows will be updated sequentially up to the available limit.")

        # Extract the sorted list of formatted date strings
        sorted_date_list = [f['formatted_date'] for f in matched_folders]

        # Update the 'Date' column in the DataFrame
        limit = min(len(df), len(sorted_date_list))
        df.loc[:limit - 1, 'Date'] = sorted_date_list[:limit]

        # Save changes to a new file to prevent accidental overwrite of the original
        output_path = base_path / f"Updated_{excel_filename}"
        df.to_excel(output_path, index=False)
        print(f"Success! File saved as: {output_path.name}")

    except Exception as e:
        print(f"An unexpected error occurred while processing the Excel file: {e}")


# ==========================================
# HOW TO USE
# ==========================================
# Replace these variables with your actual folder path and Excel filename
your_folder_path = r"C:\Path\To\Your\Folder"
your_excel_name = "Experiments.xlsx"

update_excel_dates(your_folder_path, your_excel_name)