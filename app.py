# this_file = "venv/bin/activate_this.py"
# exec(open(this_file).read(), {'__file__': this_file})
import os
import math
import io

from flask import Flask, render_template, send_file, abort, request
from PIL import Image

(MIN_X, MAX_X, MIN_Y, MAX_Y) = (-343646, 1704354, 5619537, 7667537)
MAX_TILE_SIZE = 500 * math.pow(2, 12)
SLIPPY_MAP_ORIGIN = (MIN_X, MAX_Y)
HIGH_QUALITY_TILE_PIXEL_SIZE = 1183

application = Flask(__name__)

# Config options - Make sure you created a 'config.py' file.
# application.config.from_object('config')
# To get one variable, tape app.config['MY_VARIABLE']


@application.route("/tiles/<zoom>/<x>/<y>/")
def tiles(zoom, y, x):
    filename = os.path.join("tiles", str(zoom), str(x), str(y) + ".png")
    if os.path.isfile(filename):
        return send_file(filename)
    else:
        abort(404)


@application.route("/facebook-banner/")
def facebook_banner():
    filename = os.path.join("tiles", "12_high_quality", "2557", "2151.png")
    return send_file(filename)


@application.route("/")
def index():
    return render_template("index.html")


@application.route("/about/")
def about():
    return render_template("about.html")


@application.route("/export/", methods=["POST"])
def export():
    content = request.get_json()
    x_1, y_1 = wgs84_to_tile_num(
        content["topLeft"][1], content["topLeft"][0], 12
    )
    x_2, y_2 = wgs84_to_tile_num(
        content["bottomRight"][1], content["bottomRight"][0], 12
    )

    if abs(x_1 - x_2) > 8 or abs(y_1 - y_2) > 8:
        print(
            content["topLeft"][0],
            content["topLeft"][1],
            content["bottomRight"][0],
            content["bottomRight"][1],
        )
        return "Area too large"
    # Blank image
    export = Image.new(
        "RGBA",
        (
            HIGH_QUALITY_TILE_PIXEL_SIZE * abs(x_2 - x_1 + 1),
            HIGH_QUALITY_TILE_PIXEL_SIZE * abs(y_2 - y_1 + 1),
        ),
    )

    # Merge images
    for x in range(x_1, x_2 + 1):
        x_image = Image.new(
            "RGBA",
            (
                HIGH_QUALITY_TILE_PIXEL_SIZE,
                HIGH_QUALITY_TILE_PIXEL_SIZE * abs(y_2 - y_1 + 1),
            ),
        )
        for y in range(y_1, y_2 + 1):
            filename = os.path.join(
                "tiles", "12_high_quality", str(x), str(y) + ".png"
            )
            if os.path.exists(filename):
                x_y_image = Image.open(filename)
            else:
                x_y_image = Image.new(
                    "RGBA",
                    (
                        HIGH_QUALITY_TILE_PIXEL_SIZE,
                        HIGH_QUALITY_TILE_PIXEL_SIZE,
                    ),
                    (255, 0, 0, 0),
                )
            x_image.paste(
                x_y_image, (0, abs(y - y_1) * HIGH_QUALITY_TILE_PIXEL_SIZE)
            )
        export.paste(x_image, (abs(x - x_1) * HIGH_QUALITY_TILE_PIXEL_SIZE, 0))

    # Crop image
    lon_1, lat_1 = tile_num_to_wgs84(x_1, y_1, 12)
    lon_1_plus_1, lat_1_plus_1 = tile_num_to_wgs84(x_1 + 1, y_1 + 1, 12)
    lon_2, lat_2 = tile_num_to_wgs84(x_2, y_2, 12)
    lon_2_plus_1, lat_2_plus_1 = tile_num_to_wgs84(x_2 + 1, y_2 + 1, 12)
    left = (
        abs((lon_1 - content["topLeft"][0]) / (lon_1 - lon_1_plus_1))
        * HIGH_QUALITY_TILE_PIXEL_SIZE
    )
    upper = (
        abs((lat_1 - content["topLeft"][1]) / (lat_1 - lat_1_plus_1))
        * HIGH_QUALITY_TILE_PIXEL_SIZE
    )
    right = (
        abs(x_2 - x_1) * HIGH_QUALITY_TILE_PIXEL_SIZE
        + abs((lon_2 - content["bottomRight"][0]) / (lon_2 - lon_2_plus_1))
        * HIGH_QUALITY_TILE_PIXEL_SIZE
    )
    lower = (
        abs(y_2 - y_1) * HIGH_QUALITY_TILE_PIXEL_SIZE
        + abs((lat_2 - content["bottomRight"][1]) / (lat_2 - lat_2_plus_1))
        * HIGH_QUALITY_TILE_PIXEL_SIZE
    )
    export_crop = export.crop((left, upper, right, lower))
    # Add Mapant template
    # return_data = io.BytesIO()
    # export_crop.save(return_data, 'PNG')
    # return send_file(return_data, mimetype='image/png', attachment_filename='export.png')
    export_filename = (
        "export_"
        + str(x_1)
        + "_"
        + str(y_1)
        + "_"
        + str(x_2)
        + "_"
        + str(y_2)
        + ".png"
    )
    export_crop.save(export_filename, "PNG")

    # Write image in memory
    return_data = io.BytesIO()
    with open(export_filename, "rb") as fo:
        return_data.write(fo.read())
    # Moving cursor to start
    return_data.seek(0)
    # Delete the image
    os.remove(export_filename)
    # Send data written in memory
    return send_file(
        return_data, mimetype="image/png", attachment_filename="export.png"
    )


# Helpers


def wgs84_to_tile_num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def tile_num_to_wgs84(xtile, ytile, zoom, invert=True):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    if invert == True:
        return (lon_deg, lat_deg)
    else:
        return (lat_deg, lon_deg)


if __name__ == "__main__":
    application.run(debug=True, host="localhost", port=8080)
