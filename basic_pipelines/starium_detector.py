from hailo_platform import (HEF, Device, VDevice, HailoStreamInterface, InferVStreams, ConfigureParams,
                InputVStreamParams, OutputVStreamParams, FormatType)
import numpy as np


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


class StariumDetector():
    def __init__(self, hef_path):
        self.devices = Device.scan()
        self.hef_path = hef_path
        self.hef = HEF(hef_path)
       
           
    def detect(self, image):
         with VDevice(device_ids=self.devices) as target:
            target = target
            
            input_vstream_info, output_vstream_info = print_input_output_vstream_info(self.hef)
        
            network_group = configure_and_get_network_group(self.hef, target)
            network_group_params = network_group.create_params()
                
            input_vstreams_params, output_vstreams_params = create_input_output_vstream_params(network_group)

            with InferVStreams(network_group, input_vstreams_params, output_vstreams_params) as infer_pipeline:
                with network_group.activate(network_group_params):
                    for range in [image]:
                        cropedImage = range #image.crop([range[0], range[1], range[2] + range[0], range[3] + range[1]])
                        input_data = {input_vstream_info[0].name: np.expand_dims(cropedImage, axis=0)}

                        raw_image = infer_pipeline.infer(input_data)
                        #detections = utils.extract_detections(raw_image[next(iter(output_vstream_info)).name][0], range)
                        detections = raw_image[next(iter(output_vstream_info)).name][0]
                        print(detections)
