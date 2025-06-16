import sys
import re
import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.io.img_tiles as cimgt
from os import scandir
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS, IFD
from shapely.geometry import Point
from PySide6 import QtCore, QtWidgets


def get_drone_stats(folder_name: str):
    drone_make = ""
    drone_model = ""
    drone_software = ""
    flight_date = ""

    with scandir(folder_name) as it:
        for file in it:
            if file.is_file():
                if file.name.endswith('.JPG') or file.name.endswith('.TIF'):
                    img = Image.open(file)
                    exif = img.getexif()
                    try:
                        for k, v in exif.items():
                            tag = TAGS.get(k, k)
                            if tag == 'Make':
                                drone_make = v
                            if tag == 'Model':
                                drone_model = v
                            if tag == 'Software':
                                drone_software = v
                            if tag == 'DateTime':
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
                if file.name.endswith('.JPG') or file.name.endswith('.TIF'):
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
                                    gps_dict.update({"id": file.name.replace('.JPG', "").replace('.TIF', "")})
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

                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_V'):
                        img_type = 'RGB'
                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_T'):
                        img_type = 'Thermal'
                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_D'):
                        img_type = 'RGB'
                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_MS_G'):
                        img_type = 'Green'
                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_MS_R'):
                        img_type = 'Red'
                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_MS_RE'):
                        img_type = 'Red Edge'
                    if file.name.replace('.JPG', "").replace('.TIF', "").endswith('_MS_NIR'):
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


def export_gdf(gdf: gpd.GeoDataFrame, save_loc):
    gdf.to_file(save_loc)


class DroneWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.button_open = QtWidgets.QPushButton("Open Image Folder")
        self.button_export = QtWidgets.QPushButton("Export Flight Data")
        self.button_map = QtWidgets.QPushButton("Map Flight Data")

        self.dialog_import = QtWidgets.QFileDialog()
        self.dialog_import.setFileMode(QtWidgets.QFileDialog.FileMode.Directory)

        self.dialog_export = QtWidgets.QFileDialog()
        self.dialog_export.setFileMode(QtWidgets.QFileDialog.FileMode.AnyFile)

        self.text_h1 = QtWidgets.QLabel("Drone Information", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_make = QtWidgets.QLabel("Drone Make: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_model = QtWidgets.QLabel("Drone Model: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_soft = QtWidgets.QLabel("Drone Software: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_h2 = QtWidgets.QLabel("Path Information", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_date = QtWidgets.QLabel("Flight Date: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_num_img = QtWidgets.QLabel("Number of Images: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_alt_max = QtWidgets.QLabel("Max Altitude: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)
        self.text_alt_min = QtWidgets.QLabel("Min Altitude: ", alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        self.foldername = ""
        self.filename = ""
        self.gdp_pass = gpd.GeoDataFrame()

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.button_open)
        self.layout.addWidget(self.button_export)
        self.layout.addWidget(self.button_map)
        self.layout.addWidget(self.text_h1)
        self.layout.addWidget(self.text_make)
        self.layout.addWidget(self.text_model)
        self.layout.addWidget(self.text_soft)
        self.layout.addWidget(self.text_h2)
        self.layout.addWidget(self.text_date)
        self.layout.addWidget(self.text_num_img)
        self.layout.addWidget(self.text_alt_max)
        self.layout.addWidget(self.text_alt_min)

        self.button_open.clicked.connect(self.open_import_dir)
        self.button_export.clicked.connect(self.open_export_file)
        self.button_map.clicked.connect(self.open_map)

        self.request = cimgt.OSM()

    @QtCore.Slot()
    def open_import_dir(self):
        if self.dialog_import.exec():
            self.foldername = self.dialog_import.selectedUrls()

        drone_make, drone_model, drone_software, flight_date = get_drone_stats(self.foldername[0].toString().replace(
            'file:///', ''))
        gdf_coordinates, alt_min, alt_max, num_images = get_gps_exif(self.foldername[0].toString().replace(
            'file:///', ''))

        self.gdp_pass = gdf_coordinates

        self.text_make.setText("Drone Make: " + drone_make)
        self.text_model.setText("Drone Model: " + drone_model)
        self.text_soft.setText("Drone Software: " + drone_software)
        self.text_date.setText("Flight Date: " + flight_date)
        self.text_num_img.setText("Number of Images: " + str(num_images))
        self.text_alt_max.setText("Max Altitude: " + str(alt_max))
        self.text_alt_min.setText("Min Altitude: " + str(alt_min))

    @QtCore.Slot()
    def open_export_file(self):
        if self.dialog_export.exec():
            self.filename = self.dialog_export.selectedUrls()
        export_gdf(self.gdp_pass, self.filename[0].toString().replace('file:///', ''))

    @QtCore.Slot()
    def open_map(self):
        minx, miny, maxx, maxy = self.gdp_pass.total_bounds
        print(self.gdp_pass.columns)
        extent = [minx, maxx, miny, maxy]
        ax = plt.axes(projection=self.request.crs)
        ax.set_extent(extent)
        # ax.add_image(self.request, 8)
        # plt.scatter(self.gdp_pass, transform=ccrs.PlateCarree())
        self.gdp_pass.plot(ax=ax, transform=ccrs.PlateCarree())
        plt.show()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    app.setApplicationDisplayName("Drone Path Preview")

    widget = DroneWidget()
    widget.resize(400, 400)
    widget.show()

    sys.exit(app.exec())
