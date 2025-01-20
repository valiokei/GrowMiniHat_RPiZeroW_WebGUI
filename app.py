import json
import os
import random
import threading

from flask import Flask, jsonify, render_template, request

# Definizione del percorso per il file di configurazione
CONFIG_FILE = "config.json"

# Valori di default per wet_point e dry_point
default_config = {"wet_point": 70.0, "dry_point": 30.0}


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
    from pimoroni_grow import GrowHatMini

    class RealGrowHatMini(GrowHatMini):
        def __init__(self):
            super().__init__()
            self.light = ltr559.LTR559()

except ImportError:
    # Definizione delle classi Mock se le librerie non sono disponibili
    class MockMoistureSensor:
        def read(self):
            return random.uniform(0, 100)

    class MockLightSensor:
        def get_lux(self):
            return random.uniform(100, 1000)  # Valore in lux

    class MockGrowHatMini:
        def __init__(self):
            self.moisture = [MockMoistureSensor() for _ in range(3)]
            self.light = MockLightSensor()

    RealGrowHatMini = MockGrowHatMini  # Alias per utilizzare la classe mock

# Creazione dell'istanza GrowHatMini (reale o mock)
grow = RealGrowHatMini()

# Creazione dell'app Flask
app = Flask(__name__)


@app.route("/")
def index():
    """Ritorna la pagina HTML principale."""
    return render_template("index.html")


@app.route("/sensor_data")
def sensor_data():
    """Endpoint che restituisce i valori dei sensori in formato JSON."""
    # Lettura dei sensori di umidità
    try:
        s1 = grow.moisture[0].read()
    except Exception as e:
        print(f"Error reading sensor1: {e}")
        s1 = None
    try:
        s2 = grow.moisture[1].read()
    except Exception as e:
        print(f"Error reading sensor2: {e}")
        s2 = None
    try:
        s3 = grow.moisture[2].read()
    except Exception as e:
        print(f"Error reading sensor3: {e}")
        s3 = None

    # Lettura del sensore di luce
    try:
        light = grow.light.get_lux()
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
