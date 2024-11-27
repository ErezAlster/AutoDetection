from typing import Dict, List
import numpy as np
import supervision as sv

from track import trackCamera

tracker = sv.ByteTrack()
last_track_id = None


CLASS_ID_TO_TRACK = 2

def extract_detections(hailo_detections, w: int, h: int) -> Dict[str, np.ndarray]:
    xyxy: List[np.ndarray] = []
    confidence: List[float] = []
    class_id: List[int] = []
    num_detections: int = 0


    for detection in hailo_detections:
        class_id_num = detection.get_class_id()
        #take only person
        #if class_id_num == CLASS_ID_TO_TRACK:
        #if class_id_num==CLASS_ID_TO_TRACK and detection.get_confidence() > 0.6:
        bbox = detection.get_bbox()
        score = detection.get_confidence()
        xyxy.append([bbox.xmin()* w, bbox.ymin() * h, bbox.xmax() * w, bbox.ymax() * h])
        confidence.append(score)
        class_id.append(class_id_num)
        num_detections += 1

    postprocess_detections({
        "xyxy": np.array(xyxy),
        "confidence": np.array(confidence),
        "class_id": np.array(class_id),
        "num_detections": num_detections,
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

    if detections["num_detections"]>0:
        sv_detections = sv.Detections(
            xyxy=detections["xyxy"],
            confidence=detections["confidence"],
            class_id=detections["class_id"],
        )
        
        focus_bbox = None
        sv_detections = tracker.update_with_detections(sv_detections)

        map_result = {item.external_track_id: item for item in tracker.tracked_tracks}

        #Previous 
        if(last_track_id is not None):
            tracked_bbox = map_result.get(last_track_id)
            if(tracked_bbox is not None):
                focus_bbox =  map_result.get(last_track_id).tlbr
                print("tracked!", last_track_id, focus_bbox)

            else:
                print("lost it")
                last_track_id = None #No object was found for last tracking id

        #Find best match object to center at incase not object were found before
        if(last_track_id is None):

            potentials_detections = [detection for detection in sv_detections if (detection[3] == CLASS_ID_TO_TRACK)]
            try:

                potentials_detections.sort(key=sortByDistanceFromXCenter)
                if(len(potentials_detections)>0):
                    focus_bbox = potentials_detections[0][0]
                    last_track_id = potentials_detections[0][4] #Get track id
                print("new ball", focus_bbox, potentials_detections)

            except Exception as error:
                print(error)
        if(focus_bbox is not None):
            trackCamera(focus_bbox)