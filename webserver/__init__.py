import cv2
from flask import Flask, request, jsonify
from PIL import Image
from loguru import logger
import time
from typing import Dict, List, Tuple
import numpy as np
from webserver.object_detection_utils import ObjectDetectionUtils

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
        imageDetections = []
        file = request.files['image']
        image = Image.open(file).convert('RGB')
        image_height = image.height
        image_width = image.width


        devices = Device.scan()
        with VDevice(device_ids=devices) as target:
            hef = HEF(f'resources/{model}.hef')

            utils = ObjectDetectionUtils(f"resources/{model}.txt")
            ranges = []

            if(image_height == 1080):
                ranges.append([0,0, 640, 640])
                ranges.append([640, 0, 640, 640])
                ranges.append([1280, 0, 640, 640])
                ranges.append([0,440, 640, 640])
                ranges.append([640, 440, 640, 640])
                ranges.append([1280, 440, 640, 640])
            else:
                ranges.append([0,0, image_width, image_height])

            network_group = configure_and_get_network_group(hef, target)
            network_group_params = network_group.create_params()
            
            input_vstreams_params, output_vstreams_params = create_input_output_vstream_params(network_group)

            # print info of input & output
            input_vstream_info, output_vstream_info = print_input_output_vstream_info(hef)
            start_time = time.time()
            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                total_inference_time = 0
                with network_group.activate(network_group_params):
                    for range in ranges:
                        cropedImage = image.crop([range[0], range[1], range[2] + range[0], range[3] + range[1]])
                        input_data = {input_vstream_info[0].name: np.expand_dims(cropedImage, axis=0)}

                        raw_image = infer_pipeline.infer(input_data)
                        detections = utils.extract_detections(raw_image[next(iter(output_vstream_info)).name][0], range)
                        #print(detections)
                        for detection in detections:
                            imageDetections.append(detection)
                    end_time = time.time()
                    total_inference_time = (end_time - start_time)
                    logger.info("Total inference time: {} sec", total_inference_time)

        #im = Image.open(BytesIO(base64.b64decode(data['image'])))
        return jsonify(imageDetections)
    
    return app