
from replit.object_storage import Client
import io

def read_mp4_from_storage(object_name):
    """
    Reads an MP4 file from Replit Object Storage into memory
    Args:
        object_name: Name of the MP4 file in storage
    Returns:
        bytes: The MP4 file contents as bytes
    """
    # Create object storage client
    client = Client()
    
    # Download the file into a bytes buffer
    buffer = io.BytesIO()
    client.download_to_buffer(object_name, buffer)
    
    # Get the bytes content
    video_bytes = buffer.getvalue()
    buffer.close()
    
    return video_bytes

# Example usage:
if __name__ == "__main__":
    video_data = read_mp4_from_storage("example.mp4")
    print(f"Read {len(video_data)} bytes from storage")
