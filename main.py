import re
import geopandas as gpd
from os import scandir
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from shapely.geometry import Point


def get_drone_stats(folder_name: str):
    drone_make = ""
    drone_model = ""
    drone_software = ""
    flight_date = ""

    with scandir(folder_name) as it:
        for file in it:
            if file.is_file():
                if file.name.endswith('.JPG'):
                    img = Image.open(file)
                    exif = img.getexif()
                    try:
                        for k, v in exif.items():
                            tag = TAGS.get(k, k)
                            if tag == 'Make':
                                drone_make = v
                            elif tag == 'Model':
                                drone_model = v
                            elif tag == 'Software':
                                drone_software = v
                            elif tag == 'DateTime':
                                flight_date = v
                    except KeyError:
                        pass
                    break

    return drone_make, drone_model, drone_software, flight_date


def get_gps_exif(folder_name: str):
    coordinate_list = []
    altitudes = []
    num_images = 0

    with scandir(folder_name) as it:
        for file in it:
            if file.is_file():
                if file.name.endswith('.JPG'):
                    num_images += 1
                    gps_dict = {}
                    img = Image.open(file)
                    exif = img.getexif()
                    for ifd_id in IFD:
                        try:
                            ifd = exif.get_ifd(ifd_id)

                            if ifd_id == IFD.GPSInfo:
                                resolve = GPSTAGS
                            else:
                                resolve = TAGS

                            for k, v in ifd.items():
                                tag = resolve.get(k, k)
                                if tag == 'GPSAltitude':
                                    altitudes.append(float(v))
                                    gps_dict.update({"GPSAltitude": float(v)})
                                    gps_dict.update({"id": file.name.replace('.JPG', "")})
                                if tag == 'GPSLatitude':
                                    gps_dict.update({"GPSLatitude": v})
                                if tag == 'GPSLongitude':
                                    gps_dict.update({"GPSLongitude": v})
                                if tag == 'GPSLatitudeRef':
                                    gps_dict.update({"GPSLatitudeRef": v})
                                if tag == 'GPSLongitudeRef':
                                    gps_dict.update({"GPSLongitudeRef": v})
                                # print(tag, v)
                        except KeyError:
                            pass

                    deg_lon, minutes_lon, seconds_lon, = re.split(',', str(gps_dict.get('GPSLongitude')))
                    deg_lat, minutes_lat, seconds_lat, = re.split(',', str(gps_dict.get('GPSLatitude')))
                    dd_lon = (float(deg_lon.replace("(", "")) + float(minutes_lon) / 60 + float(seconds_lon.replace(
                        ")", "")) / (60 * 60)) * (-1 if gps_dict.get('GPSLongitudeRef') in ['W', 'S'] else 1)
                    dd_lat = (float(deg_lat.replace("(", "")) + float(minutes_lat) / 60 + float(seconds_lat.replace(
                        ")", "")) / (60 * 60)) * (-1 if gps_dict.get('GPSLatitudeRef') in ['W', 'S'] else 1)

                    if file.name.replace('.JPG', "").endswith('_V'):
                        img_type = 'RGB'
                    if file.name.replace('.JPG', "").endswith('_T'):
                        img_type = 'Thermal'
                    if file.name.replace('.JPG', "").endswith('_D'):
                        img_type = 'RGB'
                    if file.name.replace('.JPG', "").endswith('_MS_G'):
                        img_type = 'Green'
                    if file.name.replace('.JPG', "").endswith('_MS_R'):
                        img_type = 'Red'
                    if file.name.replace('.JPG', "").endswith('_MS_RE'):
                        img_type = 'Red Edge'
                    if file.name.replace('.JPG', "").endswith('_MS_NIR'):
                        img_type = 'Near-infrared'

                    coordinate_list.append({
                        'geometry': Point(dd_lon, dd_lat, gps_dict.get("GPSAltitude")),
                        'id': num_images,
                        'name': gps_dict.get("id"),
                        'type': img_type
                    })

    gdf_coordinates = gpd.GeoDataFrame(coordinate_list, crs='EPSG:4326')
    alt_min = min(altitudes)
    alt_max = max(altitudes)
    return gdf_coordinates, alt_min, alt_max, num_images


if __name__ == "__main__":
    # For Testing
    get_gps_exif("C:/Users/speed/Downloads/")
