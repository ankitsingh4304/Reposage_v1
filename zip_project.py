import os
import zipfile

def zipdir(path, ziph):
    for root, dirs, files in os.walk(path):
        # Exclude heavy/unnecessary directories
        dirs[:] = [d for d in dirs if d not in {'.venv', 'node_modules', '.git', '__pycache__', 'dist', 'data'}]
        for file in files:
            file_path = os.path.join(root, file)
            # Add to zip with relative path starting from RepoSage folder
            arcname = os.path.relpath(file_path, os.path.join(path, '..'))
            ziph.write(file_path, arcname)

print("Starting to zip...")
with zipfile.ZipFile('../RepoSage.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipdir('.', zipf)
print("Project successfully zipped to X:/codes/agy/RepoSage.zip")
