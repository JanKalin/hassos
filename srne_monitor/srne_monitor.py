#!/usr/bin/python3

# Cole L - 1st May 2023 - https://github.com/cole8888/SRNE-Solar-Charge-Controller-Monitor
#
# Used to gather data from SRNE charge controllers via modbus over RS232 and publish the data to an MQTT broker.
#
# Enable serial on the raspberry pi, I used this guide: https://pimylifeup.com/raspberry-pi-serial/
# You may need to switch the serial device depending on what Pi or other device you are using.
#
# MAX3232 breakout board is connected to the raspberry pi serial headers and to the charge controller RS232.
#
# If you are having trouble getting this to work, create an issue and I'll see if I can help.

import atexit
import datetime
import time
import json
from pymodbus.client import ModbusSerialClient as ModbusClient
from paho.mqtt import client as mqtt_client

DELAY_BETWEEN_REQUESTS = 5        # Number of seconds to wait in between requests to the charge controller.
JSON_OR_TEXT = "JSON"             # Console output format, either "TEXT" or "JSON".
PUBLISH = True                    # Publish data to broker. Set to False if you just want to display stuff on screen
ECHO = True                       # Set to True if you want to see the text in console
TIMESTAMP = False                 # Set to True if you want to print a timestamo before each batch of data

with open('/data/options.json') as f:
    options = json.load(f)
DEVICE = options['serial_port']

MQTT_PORT = 1883
MQTT_SERVER_ADDR = 'core-mosquitto'
MQTT_USER = ''
MQTT_PASS = ''
MQTT_CLIENT_ID = 'SRNE_Monitor'
MQTT_TOPIC_NAME = 'solar'

# Array of charging mode strings.
# These are the states the charge controller can be in when charging the battery.
chargeModes = [
    "OFF",      #0
    "NORMAL",   #1
    "MPPT",     #2
    "EQUALIZE", #3
    "BOOST",    #4
    "FLOAT",    #5
    "CUR_LIM"   #6 (Current limiting)
]

# Array of fault codes.
# These are all the possible faults the charge controller can indicate.
# Multiple faults can be thrown at the same time.
faultCodes = [
    "Charge MOS short circuit",      #0
    "Anti-reverse MOS short",        #1
    "PV panel reversely connected",  #2
    "PV working point over voltage", #3
    "PV counter current",            #4
    "PV input side over-voltage",    #5
    "PV input side short circuit",   #6
    "PV input overpower",            #7
    "Ambient temp too high",         #8
    "Controller temp too high",      #9
    "Load over-power/current",       #10
    "Load short circuit",            #11
    "Battery undervoltage warning",  #12
    "Battery overvoltage",           #13
    "Battery over-discharge"         #14
]

# Create ModbusClient instance and connect
# MAX3232 Breakout board connects to the raspberry pi serial pins and to the charge controller RS232 port. See pictures for details.
modbus = ModbusClient(port=DEVICE, baudrate=9600, stopbits=1, bytesize=8, parity='N', timeout=5)
a = modbus.connect()

# Used to reconnect on controller timeout.
def reconnectModbus():
    global a
    global modbus
    modbus = ModbusClient(port=DEVICE, baudrate=9600, stopbits=1, bytesize=8, parity='N', timeout=5) 
    a = modbus.connect()

    # Retry connection to charge controller if it fails.
    while(not a):
        print("Failed to connect to the Charge Controller, retrying in 5 seconds...")
        time.sleep(5)
        a = modbus.connect()

# Connect to the MQTT Broker.
def connectMqtt():
    def onConnect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(MQTT_CLIENT_ID)
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = onConnect
    client.connect(MQTT_SERVER_ADDR, MQTT_PORT)
    return client

# Publish the controller data to the MQTT Broker.
def publish(client, response, error):
    result = client.publish(MQTT_TOPIC_NAME, convertToJson(response, error))
    status = result[0]
    if status == 0:
        print(f"Sent to topic `{MQTT_TOPIC_NAME}`")
    else:
        print(f"Failed to send message to topic {MQTT_TOPIC_NAME}")

# When program exits, close the modbus connection.
def exit_handler(client):
        print("\nClosing Modbus Connection...")
        modbus.close()
        client.disconnect()

# Account for negative temperatures.
def getRealTemp(temp):
    if(temp/int(128) > 1):
        return -(temp%128)
    return temp

# Display the output in text format.
def printDataText(response):
    # Offset to apply when determining the charging mode.
    # This only applies when the load is turned on since they share a register.
    loadOffset = 32768 if response.registers[32] > 6 else 0

    # Charging modes
    chargeMode = chargeModes[response.registers[32]-loadOffset]

    # Determine if there are any faults / what they mean.
    faults = "None :)"
    faultID = response.registers[34]
    if(faultID != 0):
        faults = ""
        count = 0
        while(faultID != 0):
            if(faultID >= pow(2, 15-count)):
                # If there is more than one error, make a new line.
                if(count > 0):
                    faults += '\n'
                faults += '- ' + faultCodes[count-1]
                faultID -= pow(2, 15-count)
            count += 1

    # Realtime information
    print("\n------------- Real Time Data -------------")
    print("Charging Mode:\t\t\t" + chargeMode)
    print("Battery SOC:\t\t\t" + str(response.registers[0]) + "%")
    print("Battery Voltage:\t\t" + str(round(float(response.registers[1]*0.1), 1)) + "V")
    print("Battery Charge Current:\t\t" + str(round(float(response.registers[2]*0.01), 2)) + "A")
    print("Controller Temperature:\t\t" + str(getRealTemp(int(hex(response.registers[3])[2:-2], 16))) + "*C")
    print("Battery Temperature:\t\t" + str(getRealTemp(int(hex(response.registers[3])[-2:], 16))) + "*C")
    print("Load Voltage:\t\t\t" + str(round(float(response.registers[4]*0.1), 1)) + " V")
    print("Load Current:\t\t\t" + str(round(float(response.registers[5]*0.01), 2)) + " A")
    print("Load Power:\t\t\t" + str(response.registers[6]) + " Watts")
    print("Load Enabled:\t\t\t" + str(response.registers[32] > 6))
    print("Panel Volts:\t\t\t" + str(round(float(response.registers[7]*0.1), 1)) + "V")
    print("Panel Amps:\t\t\t" + str(round(float(response.registers[8]*0.01), 2)) + "A")
    print("Panel Power:\t\t\t" + str(response.registers[9]) + "W")

    # Data accumulated over the day
    print("--------------- DAILY DATA ---------------")
    print("Battery Minimum Voltage:\t" + str(round(float(response.registers[11]*0.1), 1)) + "V")
    print("Battery Maximum Voltage:\t" + str(round(float(response.registers[12]*0.1), 1)) + "V")
    print("Maximum Charge Current:\t\t" + str(round(float(response.registers[13]*0.01), 2)) + "A")
    print("Maximum Charge Power:\t\t" + str(response.registers[15]) + "W")
    print("Maximum Load Discharge Current:\t" + str(float(response.registers[14])*0.01) + "A")
    print("Maximum Load Discharge Power:\t" + str(response.registers[16]) + "W")
    print("Charge Amp Hours:\t\t" + str(response.registers[17]) + "Ah")
    print("Charge Power:\t\t\t" + str(round(float(response.registers[19]*0.001), 3)) + "KWh")
    print("Load Amp Hours:\t\t\t" + str(response.registers[18]) + "Ah")
    print("Load Power:\t\t\t" + str(round(float(response.registers[20]*0.001), 3)) + "KWh")

    # Data from the lifetime of the charge controller
    print("------------- LIFETIME DATA --------------")
    print("Days Operational:\t\t" + str(response.registers[21]) + " Days")
    print("Times Over Discharged:\t\t" + str(response.registers[22]))
    print("Times Fully Charged:\t\t" + str(response.registers[23]))
    print("Cumulative Amp Hours:\t\t" + str(round(float((response.registers[24]*65536 + response.registers[25])*0.001), 3)) + "KAh")
    print("Cumulative Power:\t\t" + str(round(float((response.registers[28]*65536 + response.registers[29])*0.001), 3)) + "KWh")
    print("Load Amp Hours:\t\t\t" + str(round(float((response.registers[26]*65536 + response.registers[27])*0.001), 3)) + "KAh")
    print("Load Power:\t\t\t" + str(round(float((response.registers[30]*65536 + response.registers[31])*0.001), 3)) + "KWh")
    print("------------------------------------------")

    print("--------------- FAULT DATA ---------------")
    print(faults)
    print("RAW Fault Data:\t\t\t" + str(response.registers[34]))
    print("------------------------------------------")

# Convert the register data to a JSON string. (For JSON print option)
def convertToJson(response, error):
    json_string = ""
    nested_dict = {}

    if(error):
        nested_dict = {
            "modbusError": error,
        }
    else:
        # Offset to apply when determining the charging mode.
        # This only applies when the load is turned on since they share a register.
        loadOffset = 32768 if response.registers[32] > 6 else 0

        # Determine if there are any faults / what they mean.
        faults = []
        faultID = response.registers[34]
        if(faultID != 0):
            count = 0
            while(faultID != 0):
                if(faultID >= pow(2, 15-count)):
                    faults.append(faultCodes[count-1])
                    faultID -= pow(2, 15-count)
                count += 1

        nested_dict = {
            "modbusError": error,
            "controller": {
                "chargingMode": chargeModes[response.registers[32]-loadOffset],
                "temperature": getRealTemp(int(hex(response.registers[3])[2:-2], 16)),
                "days": response.registers[21],
                "overDischarges": response.registers[22],
                "fullCharges": response.registers[23]
            },
            "charging": {
                "amps": round(float(response.registers[2]*0.01), 2),
                "maxAmps": round(float(response.registers[13]*0.01), 2),
                "watts": response.registers[9],
                "maxWatts": response.registers[15],
                "dailyAmpHours": response.registers[17],
                "totalAmpHours": round(float((response.registers[24]*65536 + response.registers[25])*0.001), 3),
                "dailyPower": round(float(response.registers[19]*0.001), 3),
                "totalPower": round(float((response.registers[28]*65536 + response.registers[29])*0.001), 3)
            },
            "battery": {
                "stateOfCharge": response.registers[0],
                "volts": round(float(response.registers[1]*0.1), 1),
                "minVolts": round(float(response.registers[11]*0.1), 1),
                "maxVolts": round(float(response.registers[12]*0.1), 1),
                "temperature": getRealTemp(int(hex(response.registers[3])[-2:], 16))
            },
            "panels": {
                "volts": round(float(response.registers[7]*0.1), 1),
                "amps": round(float(response.registers[8]*0.01), 2)
            },
            "load": {
                "state": True if response.registers[10] else False,
                "volts": round(float(response.registers[4]*0.1), 1),
                "amps": round(float(response.registers[5]*0.01), 2),
                "watts": response.registers[6],
                "maxAmps": response.registers[14]*0.01,
                "maxWatts": response.registers[16],
                "dailyAmpHours": response.registers[18],
                "totalAmpHours": round(float((response.registers[26]*65536 + response.registers[27])*0.001), 3),
                "dailyPower": round(float(response.registers[20]*0.001), 3),
                "totalPower": str(round(float((response.registers[30]*65536 + response.registers[31])*0.001), 3))
            },
            "faults": faults
        }
    json_string = json.dumps(nested_dict, indent=4)
    return json_string

def run():
    if PUBLISH:
        client = connectMqtt()
    if not PUBLISH or client.is_connected:
        if PUBLISH:
            atexit.register(exit_handler, client)
        while True:
            try:
                # Read 35 registers from the controller starting at address 0x0100 (Decimal 256) until 0x0122 (Decimal 290)
                response = modbus.read_holding_registers(256, 35, slave=1)
                if ECHO:
                    if TIMESTAMP:
                        print(datetime.datetime.now().isoformat())
                    if(JSON_OR_TEXT == "TEXT"):
                        printDataText(response)
                    else:
                        print(convertToJson(response, False))
                if PUBLISH:
                    publish(client, response, False)
                time.sleep(DELAY_BETWEEN_REQUESTS)
            except Exception as e:
                if ECHO:
                    if(JSON_OR_TEXT == "TEXT"):
                        print("Failed to read data, reconnecting...", e)
                    else:
                        print(convertToJson(None, True))
                if PUBLISH:
                    publish(client, None, True)
                reconnectModbus()
                time.sleep(DELAY_BETWEEN_REQUESTS)
    else:
        print("Failed to connect to MQTT Broker.")

if __name__ == '__main__':
    run()
