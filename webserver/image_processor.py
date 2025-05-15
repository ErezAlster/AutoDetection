from PIL import Image
from typing import List, Dict, Tuple
import numpy as np # Added for NMS

class ImageProcessor:
    def __init__(self, tile_size: Tuple[int, int] = (1280, 1280)):
        self.tile_width = tile_size[0]
        self.tile_height = tile_size[1]

    def tile_image(self, image: Image.Image, overlap_x: int, overlap_y: int) -> List[Dict]:
        """
        Splits an image into tiles with specified overlap.

        Args:
            image: The Pillow Image object to tile.
            overlap_x: The overlap in pixels for the x-axis.
            overlap_y: The overlap in pixels for the y-axis.

        Returns:
            A list of dictionaries, where each dictionary contains:
                'x': x-coordinate of the tile's top-left corner in the original image.
                'y': y-coordinate of the tile's top-left corner in the original image.
                'width': width of the tile.
                'height': height of the tile.
                'image_data': The cropped Pillow Image object for the tile.
        """
        tiles = []
        img_width, img_height = image.size

        stride_x = self.tile_width - overlap_x
        stride_y = self.tile_height - overlap_y
        
        # Ensure strides are at least 1 to prevent infinite loops with large overlaps
        stride_x = max(1, stride_x)
        stride_y = max(1, stride_y)

        for y_start in range(0, img_height, stride_y):
            for x_start in range(0, img_width, stride_x):
                # Define the tile boundaries, ensuring they don't exceed image dimensions
                # These are initial estimates for cropping
                x1 = x_start
                y1 = y_start
                x2 = x_start + self.tile_width
                y2 = y_start + self.tile_height

                # Adjust if the tile goes out of bounds, by shifting the tile window
                # This ensures all tiles are of size self.tile_width x self.tile_height
                # unless the image itself is smaller.
                if x2 > img_width:
                    x1 = max(0, img_width - self.tile_width)
                    x2 = img_width
                
                if y2 > img_height:
                    y1 = max(0, img_height - self.tile_height)
                    y2 = img_height
                
                # If image is smaller than tile, crop what's available
                actual_crop_x1 = x1
                actual_crop_y1 = y1
                actual_crop_x2 = min(x1 + self.tile_width, img_width) 
                actual_crop_y2 = min(y1 + self.tile_height, img_height)
                
                cropped_width = actual_crop_x2 - actual_crop_x1
                cropped_height = actual_crop_y2 - actual_crop_y1

                if cropped_width == 0 or cropped_height == 0:
                    continue

                tile_img_cropped = image.crop((actual_crop_x1, actual_crop_y1, actual_crop_x2, actual_crop_y2))

                # Pad the cropped tile to self.tile_width x self.tile_height
                padded_tile_img = Image.new('RGB', (self.tile_width, self.tile_height), (0, 0, 0)) # Black padding
                # Paste the cropped image onto the top-left corner of the padded image
                padded_tile_img.paste(tile_img_cropped, (0,0))
                
                tiles.append({
                    'x': actual_crop_x1, # x-coordinate of content in the original image
                    'y': actual_crop_y1, # y-coordinate of content in the original image
                    'width': cropped_width, # actual width of the content area before padding
                    'height': cropped_height, # actual height of the content area before padding
                    'image_data': padded_tile_img # Image is now self.tile_width x self.tile_height
                })
        
        # Post-process to remove duplicate tiles that might arise from adjustments at edges
        unique_tiles = []
        seen_coords = set()
        for tile in tiles:
            coord_tuple = (tile['x'], tile['y'])
            if coord_tuple not in seen_coords:
                unique_tiles.append(tile)
                seen_coords.add(coord_tuple)
        
        return unique_tiles

    def _calculate_iou(self, box1, box2):
        """
        Calculates Intersection over Union (IoU) for two bounding boxes.
        Each box is expected to be in [x1, y1, x2, y2] format.
        Assumes box coordinates are absolute in the original image.
        """
        # Determine the coordinates of the intersection rectangle
        x_left = max(box1[0], box2[0])
        y_top = max(box1[1], box2[1])
        x_right = min(box1[2], box2[2])
        y_bottom = min(box1[3], box2[3])

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        iou = intersection_area / float(box1_area + box2_area - intersection_area)
        return iou

    def deduplicate_detections(self, detections: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
        """
        Removes duplicate detections using Non-Maximum Suppression (NMS).
        Detections are expected to be a list of dictionaries, each with at least:
        'bbox': [x1, y1, x2, y2] (absolute coordinates in the original image)
        'score': detection confidence score
        'class_id': class identifier
        """
        if not detections:
            return []

        # Ensure detections have score, bbox, and class_id
        # This is a simplified check; more robust validation might be needed.
        for det in detections:
            if not all(k in det for k in ('points', 'confidence', 'class_id')):
                # Or raise an error, or handle default values
                print(f"Warning: Detection missing required keys: {det}")
                # For now, we'll try to proceed if bbox is there, assuming score/class_id might be optional for some NMS
                # but proper NMS usually needs scores.
                # If we cannot proceed, we might return detections as is or filter out malformed ones.

        # Sort detections by score in descending order (higher score first)
        # Assuming 'score' exists. If not, this will fail or need adjustment.
        try:
            detections_sorted = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        except KeyError:
            # If 'score' is not present, we cannot perform score-based NMS.
            # Fallback: process without sorting or return as is, or use a different strategy.
            # For now, let's assume if no score, we can't effectively NMS across classes without more info.
            # A simple NMS might still be possible if all detections are of the same class or class is ignored.
            print("Warning: 'score' key not found in all detections. NMS might be suboptimal or fail.")
            # We will proceed, but IoU will be the main factor. This is not standard NMS.
            detections_sorted = detections # Process as is if no scores

        final_detections = []
        while detections_sorted:
            current_detection = detections_sorted.pop(0)
            final_detections.append(current_detection)

            # Filter out other detections that significantly overlap with current_detection
            # and are of the same class.
            remaining_detections = []
            for det in detections_sorted:
                # Only compare if class_id is the same, if class_id is present
                # If class_id is not present, NMS is class-agnostic (might merge different objects)
                if 'class_id' in current_detection and 'class_id' in det and current_detection['class_id'] != det['class_id']:
                    remaining_detections.append(det)
                    continue
                
                if 'bbox' not in current_detection or 'bbox' not in det:
                    remaining_detections.append(det) # Keep if bbox is missing, can't compare
                    continue

                iou = self._calculate_iou(current_detection['bbox'], det['bbox'])
                if iou < iou_threshold:
                    remaining_detections.append(det)
            detections_sorted = remaining_detections
        
        return final_detections 