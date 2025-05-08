import mss
import cv2
import numpy as np
import time
from datetime import datetime

def record_window(window_title, output_path=None):
    """
    Continuously record a window with the given title.
    
    Args:
        window_title (str): The title of the window to record
        output_path (str, optional): Path to save the recording. If None, will use timestamp
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"window_recording_{timestamp}.mp4"
    
    # Initialize screen capture
    with mss.mss() as sct:
        # Get the monitor that contains the window
        monitor = sct.monitors[1]  # Primary monitor
        
        # Get window dimensions
        window = sct.grab(monitor)
        height, width = window.height, window.width
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, 30.0, (width, height))
        
        print(f"Recording window '{window_title}' to {output_path}")
        print("Press 'q' to stop recording")
        
        try:
            while True:
                # Capture the screen
                frame = np.array(sct.grab(monitor))
                
                # Convert from BGRA to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                
                # Write the frame
                out.write(frame)
                
                # Display the frame (optional)
                cv2.imshow('Recording', frame)
                
                # Break the loop if 'q' is pressed
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                
                # Small delay to control frame rate
                time.sleep(1/30)
                
        finally:
            # Clean up
            out.release()
            cv2.destroyAllWindows()
            print("Recording stopped")

if __name__ == "__main__":
    # Example usage
    window_title = "Your Window Title"  # Replace with the title of the window you want to record
    record_window(window_title)
