from PIL import Image
from io import BytesIO, StringIO


def bytes_to_discfile(byte_arr, filename):
    iobytes = BytesIO(byte_arr)
    iobytes.seek(0)
    return discord.File(iobytes, filename=filename)


def img_to_bytearray(img):
    byte_arr = BytesIO()
    img.save(byte_arr, format="PNG")
    return byte_arr.getvalue()


def stitch_images_horz(images, buf_horz=0, buf_vert=0, bgcolor=(255, 255, 255)):
    new_img_size = (
        sum([img.width for img in images]) + buf_horz * (len(images) + 1),
        max([img.height for img in images]) + buf_vert * 2,
    )
    new_img = Image.new("RGB", new_img_size, color=bgcolor)
    for idx, paste_img in enumerate(images):
        paste_img_loc = (
            sum([img.width for img in images[:idx]]) + buf_horz * (idx + 1),
            buf_vert,
        )
        new_img.paste(paste_img, paste_img_loc)
    return new_img


def stitch_images_vert(images, buf_horz=0, buf_vert=0, bgcolor=(255, 255, 255)):
    new_img_size = (
        max([img.width for img in images]) + buf_horz * 2,
        sum([img.height for img in images]) + buf_vert * (len(images) + 1),
    )
    new_img = Image.new("RGB", new_img_size, color=bgcolor)
    for idx, paste_img in enumerate(images):
        paste_img_loc = (
            buf_horz,
            sum([img.height for img in images[:idx]]) + buf_vert * (idx + 1),
        )
        new_img.paste(paste_img, paste_img_loc)
    return new_img
