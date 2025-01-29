import json
import mimetypes
import os
import random
import threading

import pillow_heif
from flask import Flask, jsonify, render_template, request
from PIL import Image

# Definizione del percorso per il file di configurazione
CONFIG_FILE = "config.json"

# Directory delle immagini
IMAGE_FOLDER = "static/images/carousel"

# Valori di default per wet_point e dry_point
default_config = {"wet_point": 70.0, "dry_point": 30.0}


def convert_heic_to_jpeg(heic_file):
    heif_file = pillow_heif.open_heif(heic_file)
    image = Image.frombytes(
        heif_file.mode, heif_file.size, heif_file.data, "raw", heif_file.mode
    )
    jpeg_path = heic_file.replace(".heic", ".jpg")
    image.save(jpeg_path, "JPEG")
    return jpeg_path


# Funzione per caricare la configurazione
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        return default_config.copy()


# Funzione per salvare la configurazione
def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)


# Carica la configurazione all'avvio
config = load_config()

# Tentativo di importare le librerie reali
try:
    import ltr559
    from grow.moisture import Moisture

    class RealSensors:
        def __init__(self):
            self.moisture = [
                Moisture(channel=1),
                Moisture(channel=2),
                Moisture(channel=3),
            ]
            self.light = ltr559.LTR559()

    sensors = RealSensors()

except ImportError as e:
    print(f"Error importing libraries: {e}")

    # Definizione delle classi Mock se le librerie non sono disponibili
    class MockMoistureSensor:
        def read(self):
            return random.uniform(0, 100)

    class MockLightSensor:
        def get_lux(self):
            return random.uniform(100, 1000)  # Valore in lux

    class MockSensors:
        def __init__(self):
            self.moisture = [MockMoistureSensor() for _ in range(3)]
            self.light = MockLightSensor()

    sensors = MockSensors()  # Alias per utilizzare la classe mock

# Creazione dell'app Flask
app = Flask(__name__)


@app.route("/")
def index():
    """Ritorna la pagina HTML principale."""
    return render_template("index.html")


@app.route("/carousel")
def carousel():
    # Converte eventuali file HEIC in JPEG
    for f in os.listdir(IMAGE_FOLDER):
        if f.lower().endswith(".heic"):
            heic_path = os.path.join(IMAGE_FOLDER, f)
            convert_heic_to_jpeg(heic_path)

    # Lista dei file nella cartella immagini
    valid_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4")
    image_files = [
        os.path.join(IMAGE_FOLDER, f)
        for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith(valid_extensions)
    ]

    # Identifica il tipo MIME dei file
    media_files = [
        {"path": file, "type": mimetypes.guess_type(file)[0] or ""}
        for file in image_files
    ]

    return render_template("carousel.html", media_files=media_files)


@app.route("/sensor_data")
def sensor_data():
    """Endpoint che restituisce i valori dei sensori in formato JSON."""
    # Lettura dei sensori di umidità
    try:
        s1 = sensors.moisture[0].moisture
        s2 = sensors.moisture[1].moisture
        s3 = sensors.moisture[2].moisture
    except Exception as e:
        print(f"Error reading sensors: {e}")
        s1, s2, s3 = None, None, None

    # Lettura del sensore di luce
    try:
        light = sensors.light.get_lux() if sensors.light else None
    except AttributeError:
        # Se il metodo non esiste (nel caso del mock), genera un valore casuale
        light = random.uniform(100, 1000)

    # Restituzione dei dati in formato JSON
    return jsonify({"sensor1": s1, "sensor2": s2, "sensor3": s3, "light": light})


@app.route("/settings", methods=["GET", "POST"])
def settings():
    """Endpoint per ottenere e impostare wet_point e dry_point."""
    global config
    if request.method == "POST":
        data = request.json
        wet_point = data.get("wet_point")
        dry_point = data.get("dry_point")

        # Validazione dei dati
        if wet_point is not None and isinstance(wet_point, (int, float)):
            config["wet_point"] = float(wet_point)
        if dry_point is not None and isinstance(dry_point, (int, float)):
            config["dry_point"] = float(dry_point)

        # Salva la configurazione
        save_config(config)

        return jsonify({"status": "success", "config": config}), 200

    else:
        # Metodo GET: restituisce la configurazione attuale
        return jsonify(config), 200


if __name__ == "__main__":
    # Avvio del server Flask: host='0.0.0.0' per essere raggiungibile in LAN,
    # port=5000 (o qualunque altra porta preferisci).
    app.run(host="0.0.0.0", port=5000, debug=True)
