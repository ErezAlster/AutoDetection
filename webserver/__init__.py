import cv2
from flask import Flask, request, jsonify
from PIL import Image
from loguru import logger
import time
from typing import Dict, List, Tuple
import numpy as np
from webserver.object_detection_utils import ObjectDetectionUtils
from webserver.image_processor import ImageProcessor

from hailo_platform import (HEF, Device, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
                InputVStreamParams, OutputVStreamParams, FormatType)

from webserver.utils import crop_with_overlap

def configure_and_get_network_group(hef, target):
    configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
    network_group = target.configure(hef, configure_params)[0]
    return network_group


def create_input_output_vstream_params(network_group):
    input_vstreams_params = InputVStreamParams.make_from_network_group(network_group, quantized=False, format_type=FormatType.FLOAT32)
    output_vstreams_params = OutputVStreamParams.make_from_network_group(network_group, quantized=True, format_type=FormatType.FLOAT32)
    return input_vstreams_params, output_vstreams_params

def print_input_output_vstream_info(hef):
    input_vstream_info = hef.get_input_vstream_infos()
    output_vstream_info = hef.get_output_vstream_infos()
    
    return input_vstream_info, output_vstream_info

def create_app():
    app = Flask(__name__)

    @app.route('/api/inference/<model>', methods=["POST"])
    def inference(model):
        all_tile_detections = []
        file = request.files['image']
        original_image = Image.open(file).convert('RGB')

        overlap_x = request.form.get('overlap_x', default=128, type=int)
        overlap_y = request.form.get('overlap_y', default=128, type=int)
        iou_threshold_form = request.form.get('iou_threshold', default=0.5, type=float)
        
        image_processor = ImageProcessor()
        tiles = image_processor.tile_image(original_image, overlap_x=overlap_x, overlap_y=overlap_y)

        devices = Device.scan()
        with VDevice(device_ids=devices) as target:
            hef = HEF(f'resources/{model}.hef')
            utils = ObjectDetectionUtils(f"resources/{model}.txt")
            network_group = configure_and_get_network_group(hef, target)
            network_group_params = network_group.create_params()
            input_vstreams_params, output_vstreams_params = create_input_output_vstream_params(network_group)
            input_vstream_info, output_vstream_info = print_input_output_vstream_info(hef)
            
            start_time = time.time()
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                with network_group.activate(network_group_params):
                    for tile_info in tiles:
                        cropedImage = tile_info['image_data']
                        # Convert PIL Image to float32 numpy array for inference
                        numpy_image_data = np.array(cropedImage, dtype=np.float32)
                        input_data = {input_vstream_info[0].name: np.expand_dims(numpy_image_data, axis=0)}
                        raw_image_output = infer_pipeline.infer(input_data)
                        
                        range_for_extraction = [
                            tile_info['x'], 
                            tile_info['y'], 
                            image_processor.tile_width, 
                            image_processor.tile_height
                        ]
                        
                        detections_from_tile = utils.extract_detections(
                            raw_image_output[next(iter(output_vstream_info)).name][0],
                            range_for_extraction
                        )
                        all_tile_detections.extend(detections_from_tile)
                    
                    end_time = time.time()
                    total_inference_time = (end_time - start_time)
                    logger.info("Total inference time: {} sec", total_inference_time)

        logger.info(f"Collected {len(all_tile_detections)} detections before NMS.")
        final_detections = image_processor.deduplicate_detections(all_tile_detections, iou_threshold=iou_threshold_form)
        logger.info(f"Returning {len(final_detections)} detections after NMS.")

        return jsonify(final_detections)
    
    return app