import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import os
import argparse
import multiprocessing
import numpy as np
import cv2
import time
import hailo
#from track import (resetCamera, trackCamera, stopCamera)
from hailo_rpi_common import (
    get_default_parser,
    QUEUE,
    get_caps_from_pad,
    get_numpy_from_buffer,
    GStreamerApp,
    app_callback_class,
)

# -----------------------------------------------------------------------------------------------
# User-defined class to be used in the callback function
# -----------------------------------------------------------------------------------------------
# Inheritance from the app_callback_class
class user_app_callback_class(app_callback_class):
    def __init__(self):
        super().__init__()
        self.new_variable = 42  # New variable example

    def new_function(self):  # New function example
        return "The meaning of life is: "

# -----------------------------------------------------------------------------------------------
# User-defined callback function
# -----------------------------------------------------------------------------------------------

def generateYoloRow(label, bbox):
    return f'{label} {bbox.xmin()} {bbox.ymin()} {bbox.xmax()} {bbox.ymax()}\n'

# This is the callback function that will be called when data is available from the pipeline
def app_callback(pad, info, user_data):
   
    # Get the GstBuffer from the probe info
    buffer = info.get_buffer()
    # Check if the buffer is valid
    if buffer is None:
        return Gst.PadProbeReturn.OK

    # Using the user_data to count the number of frames
    user_data.increment()

    print(user_data.get_count())
    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad)

    # If the user_data.use_frame is set to True, we can get the video frame from the buffer
    frame = get_numpy_from_buffer(buffer, format, width, height)
    annotatedImage = frame.copy()

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    foundBall = False

    yoloLabels = "";

    # Parse the detections
    detection_count = 0
    for detection in detections:
        label = detection.get_label()
        bbox = detection.get_bbox()
        confidence = detection.get_confidence()
        if label == "sports ball":
            #cv2.rectangle(annotatedImage, [round(bbox.xmin()*width), round(bbox.ymin()*height)], [round(bbox.xmax()*width), round(bbox.ymax()*height)], color=(255,0,0), thickness=2)
            foundBall = True
        result = cv2.rectangle(frame, [round(bbox.xmin()*width), round(bbox.ymin()*height)], [round(bbox.xmax()*width), round(bbox.ymax()*height)], color=(255,255,65), thickness=2)

        #yoloLabels += generateYoloRow(label, bbox)

    #os.write(output, result.data)

    #print(yoloLabels)
    '''
    if(foundBall):
        frameCount = user_data.get_count()
        f = open(f'/home/erez/data/raw/1/labels/{frameCount}.txt', "a")
        f.write(yoloLabels)
        f.close()
        cv2.imwrite(f'/home/erez/data/raw/1/images/{frameCount}.jpg', frame)
        #cv2.imwrite(f'/home/erez/data/raw/1/{frameCount}_annotated.jpg', annotatedImage)
        
        stopCamera()
    '''
    
    return Gst.PadProbeReturn.OK


# -----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------

# This class inherits from the hailo_rpi_common.GStreamerApp class
class GStreamerDetectionApp(GStreamerApp):
    def __init__(self, args, user_data):
        # Call the parent class constructor
        super().__init__(args, user_data)
        # Additional initialization code can be added here
        # Set Hailo parameters these parameters should be set based on the model used
        self.batch_size = 8
        self.network_width = 640
        self.network_height = 640
        self.network_format = "RGB"
        nms_score_threshold = 0.1
        nms_iou_threshold = 0.1

        # Temporary code: new postprocess will be merged to TAPPAS.
        # Check if new postprocess so file exists
        new_postprocess_path = os.path.join(self.current_path, '../resources/libyolo_hailortpp_post.so')
        if os.path.exists(new_postprocess_path):
            self.default_postprocess_so = new_postprocess_path
        else:
            self.default_postprocess_so = os.path.join(self.postprocess_dir, 'libyolo_hailortpp_post.so')

        if args.hef_path is not None:
            self.hef_path = args.hef_path

        # User-defined label JSON file
        if args.labels_json is not None:
            self.labels_config = f' config-path={args.labels_json} '
        else:
            self.labels_config = ''

        self.app_callback = app_callback

        self.thresholds_str = (
            f"nms-score-threshold={nms_score_threshold} "
            f"nms-iou-threshold={nms_iou_threshold} "
            f"output-format-type=HAILO_FORMAT_TYPE_FLOAT32"
        )
        self.create_pipeline()

    def get_pipeline_string(self):
        tiles_along_x_axis=2
        tiles_along_y_axis=2
        overlap_x_axis=0.08
        overlap_y_axis=0.08
        iou_threshold=0.3

        DETECTION_PIPELINE=(
            "queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! "
            + f"hailonet hef-path={self.hef_path} ! "
            + "queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! "
            + f"hailofilter so-path={self.default_postprocess_so} {self.labels_config} qos=false ! "
            + "queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0"
        )

        TILE_CROPPER_ELEMENT=(
            "hailotilecropper internal-offset=false name=cropper "
            + f"tiles-along-x-axis={tiles_along_x_axis} tiles-along-y-axis={tiles_along_y_axis} overlap-x-axis={overlap_x_axis} overlap-y-axis={overlap_y_axis}"
        )

        name = "src_0"
        video_format = "RGB"
        if self.video_source.startswith("/dev/video"):
            source_element =(
                  f'v4l2src device={self.video_source} name={name} ! videoconvert qos=false ! '
                + f"video/x-raw,pixel-aspect-ratio=1/1,format=RGB ! queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! "
            )
        elif self.video_source == "rpi":
            source_element = (
                "libcamerasrc name={name} ! "
                f"video/x-raw, format={self.network_format}, width=1536, height=864 ! "
                + QUEUE("queue_src_scale")
                + "videoscale ! "
                f"video/x-raw, format={self.network_format}, width={self.network_width}, height={self.network_height}, framerate=30/1 ! "
            )
        else:
             source_element = (
                  f"filesrc location={self.video_source} name=src_0 ! decodebin ! videoconvert qos=false"
            )
        source_pipeline = (
            f'{source_element} '
        )

        pipeline_string = (
            "hailomuxer name=hmux "
            + source_pipeline
            + f"{TILE_CROPPER_ELEMENT} hailotileaggregator flatten-detections=true iou-threshold={iou_threshold} name=agg "
            + f"cropper. ! queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 "
            + f"cropper. ! {DETECTION_PIPELINE} ! agg. "
            + f"agg. ! queue leaky=no max-size-buffers=3 max-size-bytes=0 max-size-time=0 ! "
            + QUEUE("queue_hailo_python")
            + QUEUE("queue_user_callback")
            + "identity name=identity_callback ! "
        )
        match self.options_menu.output:
            case 'window':
                pipeline_string += (
                    QUEUE("queue_hailooverlay")
                    + "hailooverlay ! "
                    + QUEUE("queue_videoconvert")
                    + "videoconvert qos=false ! "
                    + QUEUE("queue_hailo_display")
                    + f"fpsdisplaysink video-sink={self.video_sink} name=hailo_display sync={self.sync} text-overlay={self.options_menu.show_fps} signal-fps-measurements=true"
                )
            case 'rtsp':
                pipeline_string += (
                     QUEUE("queue_hailooverlay")
                    + "hailooverlay ! "
                    + QUEUE("queue_videoconvert")
                    + "videoconvert qos=false ! "
                    + "x264enc tune=zerolatency bitrate=6000 speed-preset=ultrafast ! rtspclientsink location=rtsp://127.0.0.1:8554/hailo"
                )
            case None:
                pipeline_string += "fakesink sync=false"
        return pipeline_string

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = user_app_callback_class()
    parser = get_default_parser()
    # Add additional arguments here
    parser.add_argument(
        "--output",
        default=None,
        choices=[None, 'rtsp', 'window'],
        help="output results to",
    )
    parser.add_argument(
        "--hef-path",
        default="resources/starium-football.hef",
        help="Path to HEF file",
    )
    parser.add_argument(
        "--labels-json",
        default=None,
        help="Path to costume labels JSON file",
    )
    args = parser.parse_args()
    app = GStreamerDetectionApp(args, user_data)
    app.run()
