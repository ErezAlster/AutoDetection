from flask import Flask, request, jsonify
from PIL import Image
from loguru import logger
import time
from typing import Dict, List, Tuple
import numpy as np
from webserver.object_detection_utils import ObjectDetectionUtils


from hailo_platform import (HEF, Device, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
                InputVStreamParams, OutputVStreamParams, FormatType)

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

    for layer_info in input_vstream_info:
        logger.info('Input layer: {} {}'.format(layer_info.name, layer_info.shape))
    for layer_info in output_vstream_info:
        logger.info('Output layer: {} {}'.format(layer_info.name, layer_info.shape))
    
    return input_vstream_info, output_vstream_info


def create_app():
    app = Flask(__name__)

    @app.route('/api/inference/<model>', methods=["POST"])
    def inference(model):
        start_time = time.time()
        imageDetections = []
        file = request.files['image']
        image = Image.open(file)
        devices = Device.scan()
        with VDevice(device_ids=devices) as target:
            hef = HEF(f'resources/{model}_h8l.hef')

            utils = ObjectDetectionUtils("labels.txt")

            image_height = image.height
            image_width = image.width

            ranges = []
            ranges.append([0,220, 640, 640])
            ranges.append([640,220, 640, 640])
            ranges.append([1280,220, 640, 640])

            input_height, input_width, input_channels = hef.get_input_vstream_infos()[0].shape
            output_height, output_width, output_channels = hef.get_output_vstream_infos()[0].shape

            #resize image to match network size (height and width)
            #scaledRawImage = utils.preprocess(image, input_width, input_height)
            #scaledimage = np.array(scaledRawImage).astype(np.float32)
            network_group = configure_and_get_network_group(hef, target)
            network_group_params = network_group.create_params()
            
            input_vstreams_params, output_vstreams_params = create_input_output_vstream_params(network_group)

            # print info of input & output
            input_vstream_info, output_vstream_info = print_input_output_vstream_info(hef)

            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                total_inference_time = 0
                i=0
                with network_group.activate(network_group_params):
                    for range in ranges:
                        cropedImage = image.crop([range[0], range[1], range[2] + range[0], range[3] + range[1]])
                        i = i +1
            
                        input_data = {input_vstream_info[0].name: np.expand_dims(cropedImage, axis=0)}

                        
                        raw_image = infer_pipeline.infer(input_data)
                       

                        detections = utils.extract_detections(raw_image[next(iter(output_vstream_info)).name][0], range)
                        imageDetections.extend(detections)

                        #utils.visualize(detections, cropedImage, i, "output", 640, 640)
                        raw_image = raw_image[next(iter(output_vstream_info)).name][0]
                    end_time = time.time()
                    total_inference_time = (end_time - start_time)
                    logger.info("Total inference time: {} sec", total_inference_time)

        #im = Image.open(BytesIO(base64.b64decode(data['image'])))
        return jsonify(imageDetections)
    
    return app