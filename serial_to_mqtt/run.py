import os
import serial
import paho.mqtt.client as mqtt

import time

SERIAL_PORT = os.environ.get('SERIAL_PORT', '/dev/ttyACM0')
BAUD_RATE = int(os.environ.get('BAUD_RATE', '9600'))
MQTT_BROKER = os.environ.get('MQTT_BROKER', 'homeassistant')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))
MQTT_TOPIC = os.environ.get('MQTT_TOPIC', 'arduino/serial')

print(f"Starting serial-to-MQTT forwarder")
print(f"Serial: {SERIAL_PORT} @ {BAUD_RATE}")
print(f"MQTT: {MQTT_BROKER}:{MQTT_PORT} → {MQTT_TOPIC}")

# Wait for MQTT to be ready
time.sleep(5)

client = mqtt.Client()
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

