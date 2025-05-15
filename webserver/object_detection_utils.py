from PIL import Image, ImageDraw, ImageFont
import numpy as np


def generate_color(class_id: int) -> tuple:
    """
    Generate a unique color for a given class ID.

    Args:
        class_id (int): The class ID to generate a color for.

    Returns:
        tuple: A tuple representing an RGB color.
    """
    np.random.seed(class_id)
    return tuple(np.random.randint(0, 255, size=3).tolist())


class ObjectDetectionUtils:
    def __init__(self, labels_path: str, padding_color: tuple = (114, 114, 114), label_font: str = "LiberationSans-Regular.ttf"):
        """
        Initialize the ObjectDetectionUtils class.

        Args:
            labels_path (str): Path to the labels file.
            padding_color (tuple): RGB color for padding. Defaults to (114, 114, 114).
            label_font (str): Path to the font used for labeling. Defaults to "LiberationSans-Regular.ttf".
        """
        self.labels = self.get_labels(labels_path)
        self.padding_color = padding_color
        self.label_font = label_font
    
    def get_labels(self, labels_path: str) -> list:
        """
        Load labels from a file.

        Args:
            labels_path (str): Path to the labels file.

        Returns:
            list: List of class names.
        """
        with open(labels_path, 'r', encoding="utf-8") as f:
            class_names = f.read().splitlines()
        return class_names

    def preprocess(self, image: Image.Image, model_w: int, model_h: int) -> Image.Image:
        """
        Resize image with unchanged aspect ratio using padding.

        Args:
            image (PIL.Image.Image): Input image.
            model_w (int): Model input width.
            model_h (int): Model input height.

        Returns:
            PIL.Image.Image: Preprocessed and padded image.
        """
        img_w, img_h = image.size
        scale = min(model_w / img_w, model_h / img_h)
        new_img_w, new_img_h = int(img_w * scale), int(img_h * scale)
        image = image.resize((new_img_w, new_img_h), Image.Resampling.BICUBIC)

        padded_image = Image.new('RGB', (model_w, model_h), self.padding_color)
        padded_image.paste(image, ((model_w - new_img_w) // 2, (model_h - new_img_h) // 2))
        return padded_image

    def draw_detection(self, draw: ImageDraw.Draw, box: list, cls: int, score: float, color: tuple, scale_factor: float):
        """
        Draw box and label for one detection.

        Args:
            draw (ImageDraw.Draw): Draw object to draw on the image.
            box (list): Bounding box coordinates.
            cls (int): Class index.
            score (float): Detection score.
            color (tuple): Color for the bounding box.
            scale_factor (float): Scale factor for coordinates.
        """
        label = f"{self.labels[cls]}: {score:.2f}%"
        ymin, xmin, ymax, xmax = box
        font = ImageFont.truetype(self.label_font, size=15)
        draw.rectangle([(xmin * scale_factor, ymin * scale_factor), (xmax * scale_factor, ymax * scale_factor)], outline=color, width=2)
        draw.text((xmin * scale_factor + 4, ymin * scale_factor + 4), label, fill=color, font=font)

    def visualize(self, detections: dict, image: Image.Image, image_id: int, output_path: str, width: int, height: int, min_score: float = 0.0, scale_factor: float = 1):
        """
        Visualize detections on the image.

        Args:
            detections (dict): Detection results.
            image (PIL.Image.Image): Image to draw on.
            image_id (int): Image identifier.
            output_path (str): Path to save the output image.
            width (int): Image width.
            height (int): Image height.
            min_score (float): Minimum score threshold. Defaults to 0.45.
            scale_factor (float): Scale factor for coordinates. Defaults to 1.
        """
        boxes = detections['detection_boxes']
        classes = detections['detection_classes']
        scores = detections['detection_scores']
        draw = ImageDraw.Draw(image)

        for idx in range(detections['num_detections']):
            color = generate_color(classes[idx])
            scaled_box = [x * width if i % 2 == 0 else x * height for i, x in enumerate(boxes[idx])]

            self.draw_detection(draw, scaled_box, classes[idx], scores[idx] * 100.0, color, scale_factor)
                
        image.save(f'{output_path}/output_image{image_id}.jpg', 'JPEG')

    def extract_detections(self, input_data: list, range) -> list:
        """
        Extract detections from the input data.

        Args:
            input_data (list): Raw detections from the model.
            range: [offsetX, offsetY, tile_content_width, tile_content_height] of the tile in the original image.
                   Note: tile_content_width and tile_content_height are the dimensions used for scaling model's relative bbox. 

        Returns:
            list: A list of detection dictionaries, each containing:
                  'confidence': confidence score (float)
                  'class_id': class index (int)
                  'label': class name (str)
                  'points': [x1, y1, x2, y2] absolute coordinates in the original image.
        """
        results = []
        offestX = range[0]
        offestY = range[1]
        # These are the dimensions the model's output bounding box coordinates (0.0-1.0) refer to.
        # In our current setup, this is image_processor.tile_width and image_processor.tile_height (e.g., 1280x1280)
        # because the image fed to the model is padded to that size.
        model_input_width = range[2]
        model_input_height = range[3]

        for class_idx, detections_for_class in enumerate(input_data):
            if not isinstance(detections_for_class, (list, np.ndarray)) or len(detections_for_class) == 0:
                continue

            for det_item in detections_for_class:
                if not isinstance(det_item, (list, np.ndarray)) or len(det_item) < 5:
                    print(f"Skipping malformed detection item: {det_item}")
                    continue
                
                bbox_relative, score_val = det_item[:4], det_item[4] # Renamed score to score_val to avoid conflict
                
                # bbox_relative is [ymin, xmin, ymax, xmax] relative to the model input (0.0-1.0)
                # Convert to absolute pixel values within the model input dimensions
                xmin_model_input = round(bbox_relative[1] * model_input_width)
                ymin_model_input = round(bbox_relative[0] * model_input_height)
                xmax_model_input = round(bbox_relative[3] * model_input_width)
                ymax_model_input = round(bbox_relative[2] * model_input_height)

                # Convert to absolute coordinates in the original image by adding tile offset
                # IMPORTANT: The offsets (offsetX, offsetY) are for the TOP-LEFT of the *content area*
                # of the tile. If the tile was padded, the detections are relative to the padded image.
                # The model sees a 1280x1280 image. Its coordinates are relative to that. We scale to pixels on that.
                # Then we add the offset of where this 1280x1280 (or its content part) started in the original image.
                abs_xmin = xmin_model_input + offestX
                abs_ymin = ymin_model_input + offestY
                abs_xmax = xmax_model_input + offestX
                abs_ymax = ymax_model_input + offestY
                
                label_name = "unknown"
                if class_idx < len(self.labels):
                    label_name = self.labels[class_idx]
                else:
                    print(f"Warning: class_idx {class_idx} is out of bounds for labels (len: {len(self.labels)}).")

                results.append({
                    "confidence": float(score_val),
                    "class_id": int(class_idx),
                    "label": label_name,
                    "points": [abs_xmin, abs_ymin, abs_xmax, abs_ymax],
                })
        return results