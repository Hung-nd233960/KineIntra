import os

def remove_first_n_lines_from_csv(folder_path, n_lines=3):
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".csv"):
            file_path = os.path.join(folder_path, filename)

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Skip files that are too short
            if len(lines) <= n_lines:
                print(f"Skipped (too short): {filename}")
                continue

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines[n_lines:])

            print(f"Processed: {filename}")

if __name__ == "__main__":
    folder = input("Enter folder path containing CSV files: ").strip()
    remove_first_n_lines_from_csv(folder)

