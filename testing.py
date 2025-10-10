from PIL import Image
from PIL.ExifTags import TAGS, IFD

image_p = 'D:/DufferinThermalJuly2Raw/DJI_20250702125148_0001_T.jpg'

img = Image.open(image_p)
exif = img.getexif()

for ifd_id in IFD:
    ifd = exif.get_ifd(ifd_id)
    for k, v in ifd.items():
        print(ifd)

