[🇷🇴 Citiți acest ghid în Română](INSTALLATION.ro.md)

# Detailed Installation & Configuration Guide

This guide provides all the necessary steps to install, configure, and customize the **Solars Systems** integration in Home Assistant.

---

## 📋 Prerequisites

1. **Solars Systems Account:** An active account on [solars-systems.eu](https://solars-systems.eu) with at least one registered inverter.
2. **API Key:** Generated from the Solars Systems platform:
   * Log in to [solars-systems.eu](https://solars-systems.eu)
   * Go to **API Keys** (or Profile -> API Keys)
   * Copy your generated key (a unique secure token).
3. **Functional Sensors in Home Assistant:** Ensure your inverter, battery, BMS, or heat pump sensors are already working in Home Assistant (e.g. from SolarAssistant, Huawei Solar, Solarman, Deye Modbus, Fronius, Victron, ESPHome, JK-BMS, Daly, Seplos, Sunclima, MQTT, etc.). Custom helpers like Riemann sum (integral) and Utility Meters are fully supported.

---

## 🚀 Method 1: Installation via HACS (Recommended)

If you have [HACS (Home Assistant Community Store)](https://hacs.xyz/) installed:

1. Open **HACS** from the Home Assistant sidebar.
2. Go to **Integrations**.
3. In the top-right corner, click the three-dots menu (`⋮`) and select **Custom repositories**.
4. Fill in:
   * **Repository:**
     ```text
     https://github.com/solars-systems/solars-systems-ha
     ```
   * **Type / Category:** `Integration`
5. Click **Add**.
6. Find the **Solars Systems** integration in the HACS list, click on it, and hit **Download** in the bottom-right corner.
7. **Restart Home Assistant:**
   * Go to **Developer Tools** -> click **Restart Home Assistant**.

---

## 📁 Method 2: Manual Installation

If you are not using HACS:

1. Download the release source code from GitHub: [solars-systems-ha Releases](https://github.com/solars-systems/solars-systems-ha/releases) or download the repository ZIP.
2. Extract the archive.
3. Copy the entire `custom_components/solars_systems` directory into your Home Assistant's `config/custom_components/` directory.
   * The directory structure should look like:
     ```text
     /config/
       └── custom_components/
           └── solars_systems/
               ├── __init__.py
               ├── manifest.json
               ├── config_flow.py
               ├── const.py
               └── ...
     ```
4. Restart Home Assistant.

---

## ⚙️ Step-by-Step Configuration Wizard

After restarting Home Assistant:

1. Go to **Settings** -> **Devices & Services** -> click the **Add Integration** button in the bottom right.
2. Search for **Solars Systems** and select it.
3. **Step 1 - Authentication:**
   * Enter the **API Key** obtained from [solars-systems.eu](https://solars-systems.eu).
4. **Step 2 - System Layout & Preset:**
   * Select your inverter from your account.
   * Choose your preset: **SolarAssistant (Auto-Detect)**, **Axpert / Voltronic / Easun (Auto-Detect)**, or **Custom**.
   * Configure the number of inverters (1 to 6).
   * Toggle optional subsystems: Battery Storage, BMS Battery Packs (JK, Daly, Seplos, Pylontech, etc.), and Heat Pump / HVAC.
5. **Step 2b - MPPT Layout per Inverter:**
   * Configure the exact number of MPPT strings (1 to 4 MPPTs) independently for each inverter.
6. **Step 3 - Solar PV Panels & Yield:**
   * Review and confirm your solar power and MPPT voltage/current/power sensors (auto-detected and pre-filled).
   * Full support for custom Riemann sum helpers, Utility Meters, and template sensors.
7. **Step 4 - Battery Storage (Optional):**
   * Confirm your battery State of Charge (SoC %), pack voltage, current, and charge/discharge power. *(Hundreds of individual BMS cell sensors are automatically filtered out to keep your list clean).*
8. **Step 4b - BMS Battery Packs & Cells (Optional):**
   * If BMS packs are enabled, select the number of packs (1 to 16).
   * **Intelligent Auto-Population:** Home Assistant automatically detects and pre-fills:
     * **Individual Cells 1 - 16** (`cell_voltage_1` .. `cell_voltage_16`) using strict non-digit regex boundary checks.
     * **Min & Max cell voltages** (`min_cell_voltage`, `max_cell_voltage`) and **Cell Delta**.
     * **Temperatures** (Probe 1, Probe 2, MOSFET / Tube).
     * **Switches & Binary Statuses** (Charging, Discharging, Balancing, Heating).
   * Changing a pack's anchor sensor in the UI dynamically rediscovers that pack's entities in real-time.
9. **Step 4c - Heat Pump & HVAC (Optional):**
   * If Heat Pump is enabled, configure water flow (L/min), flow/return temperatures (Tur/Retur), electrical power (W/kW), COP, thermal heat power, buffer/DHW temperatures, and operating statuses.
10. **Step 5 - Grid, House Load & Settings:**
    * Confirm house load consumption and grid AC voltage/power (`putereAcIn`).
    * Choose whether to **Import Historical Data** (uses robust statistical delta calculations without spikes) and configure live streaming interval (default: 30 seconds).
11. Click **Submit**. Your live solar telemetry and production history will begin streaming immediately to Solars Systems!
