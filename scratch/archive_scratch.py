import os
import shutil

scratch_dir = r'c:\Users\shiva\Desktop\AAA\scratch'
archive_dir = os.path.join(scratch_dir, 'archive')

os.makedirs(archive_dir, exist_ok=True)

# List of active scripts to KEEP in scratch/ (if any needed for reference)
keep_files = {'archive'}

files_moved = 0
for filename in os.listdir(scratch_dir):
    file_path = os.path.join(scratch_dir, filename)
    if filename in keep_files or filename == 'archive':
        continue
    if os.path.isfile(file_path):
        dest_path = os.path.join(archive_dir, filename)
        shutil.move(file_path, dest_path)
        files_moved += 1

print(f"Successfully archived {files_moved} scratch/debugging scripts into scratch/archive/.")
