import os
from git import Repo
import shutil
import time
import stat

def handle_remove_readonly(func, path, exc):
    """Handle permission issues when removing files"""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def upload_folder_to_github(source_folder, github_url, username, token):
    temp_dir = "temp_git_folder"
    
    try:
        # Remove temp directory if it exists
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
        
        # Construct the authenticated URL
        auth_url = f"https://{username}:{token}@github.com/{username}/{github_url.split('/')[-1]}"
        
        print(f"Cloning repository...")
        repo = Repo.clone_from(auth_url, temp_dir)
        
        print("Copying files...")
        # Copy all contents from source folder to the git repo
        for item in os.listdir(source_folder):
            if item != '.git' and item != temp_dir:  # Skip .git folder and temp directory
                source_item = os.path.join(source_folder, item)
                dest_item = os.path.join(temp_dir, item)
                
                if os.path.isdir(source_item):
                    if os.path.exists(dest_item):
                        shutil.rmtree(dest_item, onerror=handle_remove_readonly)
                    shutil.copytree(source_item, dest_item)
                else:
                    if os.path.exists(dest_item):
                        os.remove(dest_item)
                    shutil.copy2(source_item, dest_item)
        
        # Add all files to git
        print("Adding files to git...")
        repo.git.add(all=True)
        
        # Create commit
        print("Creating commit...")
        repo.index.commit("Added all files and folders")
        
        # Push to remote
        print("Pushing to GitHub...")
        origin = repo.remote('origin')
        origin.push()
        
        print("\nAll files have been successfully pushed to GitHub!")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    
    finally:
        # Cleanup with delay and error handling
        print("Cleaning up...")
        time.sleep(1)  # Give system time to release file handles
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, onerror=handle_remove_readonly)
        except Exception as e:
            print(f"Cleanup error (can be ignored): {str(e)}")

def main():
    # Get inputs from user
    source_folder = input("Enter the path to your source folder: ").strip()
    github_url = input("Enter the GitHub repository URL: ").strip()
    username = input("Enter your GitHub username: ").strip()
    token = input("Enter your GitHub personal access token: ").strip()
    
    # Validate source folder
    if not os.path.exists(source_folder):
        print(f"Source folder {source_folder} does not exist!")
        return
    
    upload_folder_to_github(source_folder, github_url, username, token)

if __name__ == "__main__":
    main()