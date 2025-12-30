# Adaptive Thermostat

Adaptive Thermostat is a custom Home Assistant integration that creates virtual thermostats which control real thermostats using external room temperature sensors and optional electricity price awareness.

It is designed for setups where the physical thermostat’s built-in sensor is in the wrong place (e.g. hallway instead of bathroom), or where more advanced control logic is required.


## ✨ Features

* ✅ Uses a real temperature sensor (no fake/shifted values shown)
* ✅ Controls an existing real thermostat (Zigbee, MQTT, etc.)
* ✅ Fully offline
* ✅ Adjustable hysteresis (tolerance)
* ✅ Optional temperature shift logic
* ✅ Optional electricity price awareness
* ✅ One virtual thermostat per room
* ✅ Appears as a native climate entity in Home Assistant UI
* ✅ Scales cleanly to many rooms

## 🧠 How it works

Each Adaptive Thermostat:
1.	Reads the current room temperature from a sensor
2.	Reads the target temperature set by the user
3.	Applies the control formula:
```
ON  when: current < target - tolerance + shift
OFF when: current > target + tolerance + shift
```

4.	Controls the real thermostat by setting it to:
* a high setpoint (force heating ON)
* or a low setpoint (force heating OFF)

The real thermostat remains responsible for:
* Hardware safety
* Floor temperature limits
* Zigbee/MQTT communication

## 🏗 Architecture
```
Room temperature sensor  ─┐
Electricity price sensor ─┼─▶ Adaptive Thermostat ─▶ Real thermostat
User target temperature ──┘
```

The Adaptive Thermostat acts as a controller, not a hardware device.

## 📦 Installation

Manual installation
1.	Copy the integration folder:
```
custom_components/adaptive_thermostat/
```
into:
```
/config/custom_components/
```
2.	Restart Home Assistant
3.	Go to:
```
Settings → Devices & Services → Add Integration
```
4.	Search for Adaptive Thermostat

## ⚙️ Configuration

Configuration is done entirely via the UI (config flow).

When adding a new Adaptive Thermostat, you will select:
* Real thermostat (climate.*)
* Temperature sensor (sensor.*)
* (Optional) Electricity price sensor
* Tolerance (°C)
* Base shift (°C)
* High / low fallback setpoints

Each configuration creates one virtual thermostat.

## 🌡 Example use cases

* Bathroom floor heating where the thermostat is mounted outside
* Bedroom heating controlled by a sensor near the bed
* Price-aware heating that delays heating during peak prices
* Night setback using negative shift
* Pre-heating when electricity is cheap

## 🧪 Status

This integration is currently:
* 🚧 Under active development
* 🧪 Intended for personal use
* ❌ Not yet published to HACS

Breaking changes may occur until a stable release is reached.
 
## ⚠️ Disclaimer

This integration controls heating systems.

Always ensure:
* Your real thermostat enforces safe temperature limits
* Floor heating systems have built-in protection
* You test changes carefully

Use at your own risk.
