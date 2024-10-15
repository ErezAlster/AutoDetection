import cv2
import numpy as np
print(cv2.getBuildInformation())
def main():
    # Open the webcam
    cap = cv2.VideoCapture(10)  # Change the index if you have multiple cameras

    # Check if the webcam is opened correctly
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    # GStreamer pipeline to output to a v4l2 loopback device
    gst_pipeline = (
        "appsrc ! "
        "videoconvert ! "
        "v4l2sink device=/dev/video11"
    )

    # Open the GStreamer video writer
    out = cv2.VideoWriter(gst_pipeline, cv2.CAP_GSTREAMER, 0, 30, (640, 480), True)
    if not out.isOpened():
        print("Error: Could not open video writer.")
        cap.release()
        return

    while True:
        # Capture frame-by-frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        # Optional: Convert to grayscale (as an example of processing)
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        processed_frame = cv2.cvtColor(gray_frame, cv2.COLOR_GRAY2BGR)

        # Write the processed frame to the GStreamer pipeline
        out.write(processed_frame)

        # Show the original and processed frames (optional)
        cv2.imshow('Original', frame)
        cv2.imshow('Processed', processed_frame)

        # Break the loop on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release resources
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()