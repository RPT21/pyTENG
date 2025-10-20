import os
import pandas as pd
from collections import defaultdict
import warnings

def group_files_by_keyword(file_list, keywords):
    """
    Group files based on shared keywords found in their filenames.

    Parameters
    ----------
    file_list : list of str
        List of filenames or file paths to be grouped.
    keywords : list of str
        List of keywords that define the grouping criteria.

    Returns
    -------
    dict of str : list of str
        A dictionary where each key is a keyword and the corresponding value
        is a list of files containing that keyword in their name.

    Notes
    -----
    - Matching is case-sensitive by default. Use `str.lower()` on filenames and
      keywords before calling the function to make it case-insensitive.
    - A file will be added to the first group whose keyword it matches.
      Remove the `break` statement if you want files to belong to multiple groups.
    """
    groups = defaultdict(list)

    for file in file_list:
        isFound = False
        name = os.path.basename(file)
        for keyword in keywords:
            if keyword in name:
                groups[keyword].append(file)
                isFound = True
                break
        if not isFound:
            warnings.warn(f"{file} doesn't match with any keyword from {keywords}")

    return dict(groups)


def sort_function(string):
    return int(string.split("_")[-1].split(".")[0])

def sort_function_Pickle(string):
    split_string = string.split("_")
    return int(split_string[-2]) + int(split_string[-1].split(".")[0])

def CSV_merge(folder_path, exp_id):
    """This function merges the CSV files found in folder_path and saves the merged file in the parent directory."""
    files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

    if not files:
        return
 
    files.sort(key=sort_function)

    # Create an empty DataFrame
    combined_DataFrame = pd.DataFrame()

    # Iterate the CSV files found in the folder path
    print("\nMerging...")
    for file in files:
        # Read CSV
        df = pd.read_csv(os.path.join(folder_path, file), header=0, 
                         index_col=False, delimiter=';', decimal='.')

        print(file)

        # Concatenate CSV file
        combined_DataFrame = pd.concat([combined_DataFrame, df], ignore_index=True)
    
    # Save concatenated DataFrame
    rawdata_dir = os.path.dirname(folder_path)
    filename = f'Motor-{exp_id}.csv'
    combined_DataFrame.to_csv(os.path.join(rawdata_dir, filename), index=False)
    
    print("Data saved to location:", os.path.join(rawdata_dir, filename), "\n")
    
    return filename


def Pickle_merge(folder_path, exp_id, groupby=None):
    """This function merges the Pickle files found in folder_path and saves the merged file in the parent directory."""
    files = [f for f in os.listdir(folder_path) if f.endswith('.pkl')]

    if not files:
        return
    
    files.sort(key=sort_function_Pickle)

    if groupby:

        groups = group_files_by_keyword(files, groupby)
        filenames = []

        for n, group in enumerate(groups.keys()):

            # Create an empty DataFrame
            combined_DataFrame = pd.DataFrame()

            # Iterate the Excel files found in the folder path
            print(f"\nMerging grouped by keyword {group}...")
            for file in groups[group]:
                # Read Excel
                df = pd.read_pickle(os.path.join(folder_path, file))

                print(file)

                # Concatenate CSV file
                combined_DataFrame = pd.concat([combined_DataFrame, df], ignore_index=True)

            # Save concatenated DataFrame
            rawdata_dir = os.path.dirname(folder_path)
            filenames.append(f'DAQ-{group}-{exp_id}.pkl')
            combined_DataFrame.to_pickle(os.path.join(rawdata_dir, filenames[n]))

            print("Data saved to location:", os.path.join(rawdata_dir, filenames[n]))

        print("")

        return filenames

    else:

        # Create an empty DataFrame
        combined_DataFrame = pd.DataFrame()

        # Iterate the Excel files found in the folder path
        print("\nMerging...")
        for file in files:
            # Read Excel
            df = pd.read_pickle(os.path.join(folder_path, file))

            print(file)

            # Concatenate CSV file
            combined_DataFrame = pd.concat([combined_DataFrame, df], ignore_index=True)

        # Save concatenated DataFrame
        rawdata_dir = os.path.dirname(folder_path)
        filename = f'DAQ-{exp_id}.pkl'
        combined_DataFrame.to_pickle(os.path.join(rawdata_dir, filename))

        print("Data saved to location:", os.path.join(rawdata_dir, filename))

        return filename

        
        
        
        
        
        
        
        
        
        
        