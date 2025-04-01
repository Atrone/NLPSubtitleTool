
import os

def get_directory_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_directory_size(entry.path)
    return total

# Get current directory size
size_bytes = get_directory_size()
size_mb = size_bytes / (1024 * 1024)

print(f"Current directory size: {size_mb:.2f} MB")
