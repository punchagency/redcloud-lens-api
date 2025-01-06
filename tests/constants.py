import base64
from io import BytesIO

from PIL import Image


def image_to_base64(image_path: str) -> str:
    """
    Converts an image to a Base64-encoded string.

    Args:
        image_path (str): The file path of the image.

    Returns:
        str: The Base64-encoded string of the image.
    """
    # Open the image file
    with Image.open(image_path) as img:
        # Create a BytesIO buffer
        buffer = BytesIO()
        # Save the image to the buffer in its original format
        img.save(buffer, format=img.format)
        # Get the binary data from the buffer
        img_bytes = buffer.getvalue()
        # Convert the binary data to a Base64 string
        base64_string = base64.b64encode(img_bytes).decode("utf-8")

    return base64_string


# Example usage
if __name__ == "__main__":
    image_path = "path/to/your/image.jpg"  # Replace with the path to your image
    base64_image = image_to_base64(image_path)
    print("Base64 Encoded Image:")
    print(base64_image)



