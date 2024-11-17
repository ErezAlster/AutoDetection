from typing import Dict, List
import numpy as np
import supervision as sv

from track import trackCamera

tracker = sv.ByteTrack()
last_track_id = None

def extract_detections(hailo_detections, w: int, h: int) -> Dict[str, np.ndarray]:
    xyxy: List[np.ndarray] = []
    confidence: List[float] = []
    class_id: List[int] = []
    num_detections: int = 0

    for detection in hailo_detections:
        class_id_num = detection.get_class_id()
        #take only person
        if class_id_num==1:
            bbox = detection.get_bbox()
            score = detection.get_confidence()
            print(class_id_num, detection.get_label(), score)

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


def postprocess_detections(detections: Dict[str, np.ndarray],) -> np.ndarray:
    if detections["num_detections"]>0:
        sv_detections = sv.Detections(
            xyxy=detections["xyxy"],
            confidence=detections["confidence"],
            class_id=detections["class_id"],
        )


        sv_detections = tracker.update_with_detections(sv_detections)

        trackCamera(detections["xyxy"][0])
