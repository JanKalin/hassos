import datetime
import json
import os
import serial
import time
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import paho.mqtt.client as mqtt

with open("/data/options.json", "r") as f:
    options = json.load(f)

MQTT_TOPIC = options.get("mqtt_topic", "arduino/serial")
MQTT_BROKER = options.get("mqtt_broker", "localhost")
MQTT_PORT = options.get('mqtt_port', '1883')
BAUD_RATE = options.get("baud_rate", 9600)
SERIAL_PORT = options.get("serial_port", "/dev/ttyACM0")

print(f"{datetime.datetime.now().isoformat()} Starting serial-to-MQTT forwarder")
print(f"{datetime.datetime.now().isoformat()} Serial: {SERIAL_PORT} @ {BAUD_RATE}")
print(f"{datetime.datetime.now().isoformat()} MQTT: {MQTT_BROKER}:{MQTT_PORT} → {MQTT_TOPIC}")

# Wait for MQTT to be ready
time.sleep(5)

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.connect(MQTT_BROKER, MQTT_PORT, 60)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
except Exception as e:
    print(f"{datetime.datetime.now().isoformat()} Failed to open serial port: {e}")
    exit(1)

print(f"{datetime.datetime.now().isoformat()} Requesting discovery")
ser.write(b"discovery\n")

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        if line:
            print(f"{datetime.datetime.now().isoformat()} Publishing: {line}")
            client.publish(MQTT_TOPIC, line)
    except Exception as e:
        print(f"Error: {e}")

