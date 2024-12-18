import datetime
from typing import Dict, List
import numpy as np
import supervision as sv
import hailo
from track import trackCamera

CLASS_ID_TO_TRACK = 2
last_track_id = None

def extract_detections(hailo_detections, w: int, h: int) -> Dict[str, np.ndarray]:
    n = len(hailo_detections)
    confidence = np.zeros(n)
    class_id = np.zeros(n)
    tracker_id = np.empty(n)
    boxes = np.zeros((n, 4))

    for i,detection in enumerate(hailo_detections):
        detection_tracker = None
        smo = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if(smo is not None and len(smo)>0):
            detection_tracker = round(smo[0].get_id())
        class_id[i] = detection.get_class_id()
        confidence[i] = detection.get_confidence()
        tracker_id[i] = detection_tracker
        bbox = detection.get_bbox()
        boxes[i] = [bbox.xmin() * w, bbox.ymin() * h, bbox.xmax() * w, bbox.ymax() * h]

    postprocess_detections({
        "xyxy": boxes,
        "confidence": confidence,
        "class_id": class_id,
        "tracker_id": tracker_id,
        "num_detections": n,
    })

def sortByDistanceFromXCenter(detection):
    bbox = detection[0]
    xmin, xmax  = bbox[0], bbox[2]

    #get the pixel distance from the center of the image to the object
    #tracked objects should be closer to the distance as much as we can
    result = abs((1980 / 2) - ((xmax + xmin)/2))
    return result

def postprocess_detections(detections: Dict[str, np.ndarray],):
    global last_track_id
    last_track_id = None

    if detections["num_detections"]>0:
        sv_detections = sv.Detections(
            xyxy=detections["xyxy"],
            confidence=detections["confidence"],
            class_id=detections["class_id"],
            tracker_id=detections["tracker_id"]
        )
        
        focus_bbox = None
        map_result = {}

        for detection in sv_detections:
            map_result[np.round(detection[4]).astype(int)]=detection[0]
        
        #Previous 
        if(last_track_id is not None):
            focus_bbox = map_result.get(last_track_id)

            if(focus_bbox is  None):
                last_track_id = None #No object was found for last tracking id

        #Find best match object to center at incase not object were found before
        if(last_track_id is None):

            potentials_detections = [detection for detection in sv_detections if (detection[3] == CLASS_ID_TO_TRACK and detection[0][1]<(1080/3))]
            try:
                potentials_detections.sort(key=sortByDistanceFromXCenter)
                if(len(potentials_detections)>0):
                    focus_bbox = potentials_detections[0][0]
                    last_track_id = np.round(potentials_detections[0][4]).astype(int) #Get track id

            except Exception as error:
                print(error)
        if(focus_bbox is not None):
            #print(datetime.datetime.now(), last_track_id, focus_bbox)
            trackCamera(focus_bbox)
#        else:
#            print(datetime.datetime.now(), "no ball")
#    else:
#        print(datetime.datetime.now(), "no ball")