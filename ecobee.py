import sys, os
import json
import requests
import json
import time
import RPi.GPIO as GPIO

RELAY_PIN = 11

GPIO.setmode(GPIO.BOARD)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.HIGH)

# load env vars
with open(os.path.join(sys.path[0], "config.json"), "r") as f:
    config = json.load(f)


# ecobee API
apiUrlBase = "https://api.ecobee.com/1/"
auth_url_base = "https://api.ecobee.com/token"

# parameters
hvacMode = None
currentTemp = None
setHeatTemp = None
setCoolTemp = None
currentHumidity = 100
equipmentStatus = ""


def convertToCelsius(temp):
    return (int(temp) - 320) * 5 / 90


def getStatus():
    global hvacMode
    global currentTemp
    global setHeatTemp
    global setCoolTemp
    global currentHumidity
    global equipmentStatus

    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer {0}".format(config["TKN"]),
    }

    params = [
        {
            "selection": {
                "selectionType": "thermostats",
                "selectionMatch": config["METER_ID"],
                "includeRuntime": True,
                "includeEquipmentStatus": True,
            }
        }
    ]
    params_json = json.dumps(params[0])

    # api_url = '{0}thermostat?format=json&body='.format(apiUrlBase)
    api_url = "{0}thermostat?json=".format(apiUrlBase)

    response = requests.get(api_url + params_json, headers=headers)
    if response.status_code == 500:
        response = refreshTkn()

        if response.status_code != 200:
            print("error")
            sys.stdout.flush()
            return
        else:
            print("Refresh Succesful")
            sys.stdout.flush()
            refreshDict = json.loads(response.text)
            config["TKN"] = refreshDict["access_token"]

            with open(os.path.join(sys.path[0], "config.json"), "w") as f:
                json.dump(config, f)

            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer {0}".format(config["TKN"]),
            }

            response = requests.get(api_url + params_json, headers=headers)

    dict = json.loads(response.text)
    print(dict)
    sys.stdout.flush()
    currentTemp = convertToCelsius(
        str(dict["thermostatList"][0]["runtime"]["actualTemperature"])
    )
    currentHumidity = int(str(dict["thermostatList"][0]["runtime"]["actualHumidity"]))
    setHeatTemp = convertToCelsius(
        str(dict["thermostatList"][0]["runtime"]["desiredHeat"])
    )
    setCoolTemp = convertToCelsius(
        str(dict["thermostatList"][0]["runtime"]["desiredCool"])
    )
    equipmentStatus = str(dict["thermostatList"][0]["equipmentStatus"])

    print("Current Temperature: ", currentTemp)
    print("Current Humidity: ", currentHumidity)
    print("Set Heating Temperature: ", setHeatTemp)
    print("Set Cooling Temperature: ", setCoolTemp)
    print("Equpment on: ", equipmentStatus)
    sys.stdout.flush()


def refreshTkn():
    params = {
        "grant_type": "refresh_token",
        "refresh_token": config["REFRESH_TKN"],
        "client_id": config["API_KEY"],
    }

    return requests.post(auth_url_base, params=params)


def runWater():
    if currentHumidity < 40 and equipmentStatus.find("auxHeat1") != -1:
        currentTime = time.time()
        print("Running now")
        sys.stdout.flush()
        GPIO.output(RELAY_PIN, GPIO.LOW)
        while time.time() - currentTime < 2:
            pass
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        currentTime = time.time()
        while time.time() - currentTime < 28:
            pass
    else:
        currentTime = time.time()
        print("Waiting for next api call")
        sys.stdout.flush()
        while time.time() - currentTime < 180:
            pass


while True:
    getStatus()
    timeNow = time.time()
    print(equipmentStatus)
    print(equipmentStatus.find("auxHeat1"))
    sys.stdout.flush()
    while time.time() - timeNow < 180:
        runWater()
