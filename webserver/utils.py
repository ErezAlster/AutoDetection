import math

def crop_with_overlap(image, crop_width, crop_height, overlap):
    """
    Crops a large image into smaller images with overlapping areas.

    Parameters:
        path (str): Path to the input image.
        crop_width (int): Width of each cropped region.
        crop_height (int): Height of each cropped region.
        overlap (int): Number of pixels to overlap between adjacent crops.

    """

    cropped_areas = []
    # Load the image
    img_width, img_height = image.size
    
    # Calculate the number of crops along width and height
    x_steps = math.ceil((img_width - overlap) // (crop_width - overlap))
    y_steps = math.ceil((img_height - overlap) / (crop_height - overlap))
    for y in range(y_steps):
        for x in range(x_steps):
            # Calculate the cropping box with overlap
            left = x * (crop_width - overlap)
            upper = y * (crop_height - overlap)
            right = min(left + crop_width, img_width)
            lower = min(upper + crop_height, img_height)
            cropped_areas.append([left, upper, right, lower])

    return cropped_areas