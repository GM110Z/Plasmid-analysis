#Filter blast ouput


import pandas as pd
import os
import csv
# Load your BLAST data into a DataFrame
df = pd.read_csv("tab-sep.txt", sep="\t", header=None, 
                 names=["query_id", "subject_id", "identity", "alignment_length", 
                        "mismatches", "gap_opens", "q_start", "q_end", 
                        "s_start", "s_end", "evalue", "bit_score"])

# Clean any unwanted characters (e.g., non-breaking spaces) from 's_start' and 's_end' columns
df["s_start"] = df["s_start"].replace({r"\xa0": ""}, regex=True).str.strip()
df["s_end"] = df["s_end"].replace({r"\xa0": ""}, regex=True).str.strip()

# Convert 's_start' and 's_end' to integers, handle errors if conversion fails
df["s_start"] = pd.to_numeric(df["s_start"], errors="coerce")
df["s_end"] = pd.to_numeric(df["s_end"], errors="coerce")

# Step 1: Sort by subject and subject start position
df = df.sort_values(by=["subject_id", "s_start"])

# Step 2: Initialize variables to store regions
regions = []
current_region = None

# Step 3: Loop through the rows to group the hits into regions
for i, row in df.iterrows():
    subject_id = row["subject_id"]
    s_start = row["s_start"]
    s_end = row["s_end"]

    # Skip rows with invalid numeric values (NaN after coercion)
    if pd.isna(s_start) or pd.isna(s_end):
        continue

    # If it's the first hit, start a new region
    if current_region is None:
        current_region = {
            "subject_id": subject_id,
            "start": s_start,
            "end": s_end
        }
    else:
        # Check if the current hit is close enough to the last region
        if subject_id == current_region["subject_id"] and (s_start - current_region["end"] <= 110000):
            # Extend the current region if the current hit is close enough
            current_region["end"] = max(current_region["end"], s_end)
        else:
            # If the hits are far apart, save the current region and start a new one
            region_size = current_region["end"] - current_region["start"]
            if 20000 <= region_size <= 180000:  # Filter based on size
                regions.append(current_region)
            # Start a new region
            current_region = {
                "subject_id": subject_id,
                "start": s_start,
                "end": s_end
            }

# Final region check after loop finishes
if current_region is not None:
    region_size = current_region["end"] - current_region["start"]
    if 20000 <= region_size <= 180000:  # Filter based on size
        regions.append(current_region)

# Convert regions to a DataFrame for easy output as a table
regions_df = pd.DataFrame(regions)

# Convert start and end positions to integers (removing .0)
regions_df["start"] = regions_df["start"].astype(int)
regions_df["end"] = regions_df["end"].astype(int)

# Write the table to a CSV file
regions_df.to_csv("regions_output_table.csv", index=False)



#calculate size and split files by size intervals
# Path to your input file
input_file = "regions_output_table.csv"  # Replace with your file path
output_folder = "grouped_regions"
os.makedirs(output_folder, exist_ok=True)

# Define size ranges and corresponding file names
ranges = {
    "20-40k": (20000, 40000),
    "41-60k": (41000, 60000),
    "61-80k": (61000, 80000),
    "81-200k": (81000, 200000)
}

# Dictionary to store data for each range
grouped_data = {key: [] for key in ranges}

# List to store all region sizes for summary
all_sizes = []

# Ensure the output folder exists
output_folder = "grouped_regions"
os.makedirs(output_folder, exist_ok=True)

# Path to your input file
input_file = "regions_output_table.csv"  # Replace with your file path

# Process the input file
with open(input_file, "r", newline="") as infile:
    csv_reader = csv.reader(infile)
    header = next(csv_reader)  # Skip the header row

    for row in csv_reader:
        if len(row) < 3:  # Skip malformed rows
            print(f"Skipping malformed row: {row}")
            continue
        
        try:
            accession = row[0]
            start = int(row[1])
            stop = int(row[2])
            size = stop - start
            all_sizes.append((accession, start, stop, size))  # Collect all sizes for summary
        except ValueError:
            print(f"Skipping row with invalid data: {row}")
            continue

        # Assign the region to the appropriate range
        for range_name, (min_size, max_size) in ranges.items():
            if min_size <= size <= max_size:
                grouped_data[range_name].append((accession, start, stop, size))
                break

# Write data for each range to separate files
for range_name, regions in grouped_data.items():
    output_file = os.path.join(output_folder, f"{range_name}_regions.tsv")
    with open(output_file, "w", newline="") as out:
        tsv_writer = csv.writer(out, delimiter="\t")
        # Write header
        tsv_writer.writerow(["Accession", "Start", "Stop", "Size"])
        # Write regions
        tsv_writer.writerows(regions)

# Write summary file with all sizes
summary_file = os.path.join(output_folder, "summary_sizes.tsv")
with open(summary_file, "w", newline="") as summary_out:
    tsv_writer = csv.writer(summary_out, delimiter="\t")
    # Write header
    tsv_writer.writerow(["Accession", "Start", "Stop", "Size"])
    # Write all regions with their sizes
    tsv_writer.writerows(all_sizes)

print(f"Regions grouped by size and saved in folder: {output_folder}")
print(f"Summary of all region sizes saved in: {summary_file}")

