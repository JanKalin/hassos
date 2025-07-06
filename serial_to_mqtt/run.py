import os
import serial
import paho.mqtt.client as mqtt

import time
import json

with open("/data/options.json", "r") as f:
    options = json.load(f)

MQTT_TOPIC = options.get("mqtt_topic", "arduino/serial")
MQTT_BROKER = options.get("mqtt_broker", "localhost")
MQTT_PORT = options.get('mqtt_port', '1883')
BAUD_RATE = options.get("baud_rate", 9600)
SERIAL_PORT = options.get("serial_port", "/dev/ttyACM0")

print(f"Starting serial-to-MQTT forwarder")
print(f"Serial: {SERIAL_PORT} @ {BAUD_RATE}")
print(f"MQTT: {MQTT_BROKER}:{MQTT_PORT} → {MQTT_TOPIC}")

# Wait for MQTT to be ready
time.sleep(5)

client = mqtt.Client(protocol=mqtt.MQTTv311)
client.connect(MQTT_BROKER, MQTT_PORT, 60)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
except Exception as e:
    print(f"Failed to open serial port: {e}")
    exit(1)

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        if line:
            print(f"Publishing: {line}")
            client.publish(MQTT_TOPIC, line)
    except Exception as e:
        print(f"Error: {e}")

