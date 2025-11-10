import os
import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NewProjectHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            print(f"New project detected: {os.path.basename(event.src_path)}")
            # Run generate_projects_json.py to update the project list
            subprocess.run(['python3', 'generate_projects_json.py'])

if __name__ == "__main__":
    event_handler = NewProjectHandler()
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=False)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()