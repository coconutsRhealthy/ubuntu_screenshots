import os
import subprocess
from datetime import datetime

# 📌 Root folder van je screenshots
SCREENSHOT_DIR = "/home/lennart/screenshots"

# 📌 Git instellingen
GIT_REPO_DIR = SCREENSHOT_DIR  # repo root
BRANCH = "main"
COMMIT_MESSAGE = "Automated commit of new screenshots"

# 📌 Functie om alle bestanden te vinden
def get_all_files(root_dir):
    file_list = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for f in filenames:
            if f.endswith(".png"):  # alleen screenshots
                file_list.append(os.path.join(dirpath, f))
    return file_list

# 📌 Functie om te checken welke bestanden nog niet in git staan
def get_untracked_files():
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=GIT_REPO_DIR,
        capture_output=True,
        text=True
    )
    untracked = []
    for line in result.stdout.splitlines():
        # Git status porcelain: "?? path/to/file.png" = untracked
        if line.startswith("??"):
            file_path = line[3:].strip()
            untracked.append(file_path)
    return untracked

# 📌 Commit en push nieuwe bestanden
def commit_and_push(files_to_commit):
    if not files_to_commit:
        print("Geen nieuwe screenshots om te committen.")
        return

    # 1️⃣ Voeg bestanden toe
    subprocess.run(["git", "add"] + files_to_commit, cwd=GIT_REPO_DIR)

    # 2️⃣ Commit
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"{COMMIT_MESSAGE} @ {timestamp}"
    subprocess.run(["git", "commit", "-m", message], cwd=GIT_REPO_DIR)

    # 3️⃣ Push
    subprocess.run(["git", "push", "origin", BRANCH], cwd=GIT_REPO_DIR)
    print(f"{len(files_to_commit)} nieuwe screenshots gecommit en gepusht.")

# 🔹 Hoofdscript
if __name__ == "__main__":
    untracked_files = get_untracked_files()
    commit_and_push(untracked_files)
