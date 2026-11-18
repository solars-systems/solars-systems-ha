[🇷🇴 Citiți această pagină în Română](README.ro.md)

# Solars Systems - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/solars-systems/solars-systems-ha?color=blue)](https://github.com/solars-systems/solars-systems-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The official Home Assistant integration for the [Solars Systems](https://solars-systems.eu) monitoring and management platform.

Allows owners of photovoltaic systems (SolarAssistant, Deye, Huawei, Growatt, Victron, Fronius, Sungrow, Infinisolar, etc.) using Home Assistant to stream live telemetry and synchronize historical production data seamlessly into the **Solars Systems** cloud platform.

---

## ✨ Key Features

* **📡 Real-Time Telemetry Streaming:**
  * Total Solar PV Power (W / kW) and individual power per inverter / MPPT
  * Individual MPPT / String voltages (`voltajPV1`, `voltajPV1_2`, `voltajPV2`, etc.)
  * Home Consumption / Load Power (W / kW)
  * Comprehensive Battery Storage Monitoring: State of Charge (SoC %), Pack Voltage (V), Current (A), and Charge/Discharge Power (W)
  * Grid AC Voltages: AC Input (Grid) and Inverter AC Output voltage
  * Energy Yield: Daily (today), Monthly (this month), and Yearly (this year) in kWh
* **⚡ SolarAssistant & Multi-Inverter Presets:**
  * **SolarAssistant Auto-Detect:** Automatically pre-maps standard SolarAssistant entity IDs in seconds
  * **Smart Anti-Cell Filter:** Automatically excludes hundreds of individual BMS cell sensors (`cell_1`..`cell_24`), preventing dropdown clutter
  * **Appliance & Heat Pump Shield:** Intelligent keyword filters prevent heat pumps, AC units, and wall-mounted dashboard tablets from being misidentified as solar entities
  * Supports cascading / parallel setups from 1 to 6 inverters and 1 to 4 MPPT strings per inverter
* **📊 Monotonic Historical Energy Import:**
  * Automatically extracts historical daily energy stats (kWh/day) from Home Assistant's long-term statistics (last 30 days, 90 days, 1 year, or all-time)
  * **Monotonic & Idempotent:** Never overwrites valid historical records with lower values; existing entries are only updated if Home Assistant provides a higher, more accurate value
  * Emits a persistent Home Assistant notification once history import completes
* **🔒 Secure Authentication:** Direct API Key authentication (`x-api-key`) generated from your Solars Systems account

---

## ⚡ Quick Installation

1. In **HACS** -> **Integrations** -> top-right menu (`⋮`) -> **Custom repositories**, add:
   ```text
   https://github.com/solars-systems/solars-systems-ha
   ```
   *(Category: `Integration`)*
2. Download the **Solars Systems** integration and restart Home Assistant.
3. Navigate to **Settings** -> **Devices & Services** -> **Add Integration**, search for **Solars Systems**, and follow the guided setup wizard.

> 📖 **Need step-by-step instructions?**  
> Check out the [**Detailed Installation & Configuration Guide (INSTALLATION.md)**](INSTALLATION.md) for manual installation, sensor mapping tips, and troubleshooting.

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).  
Developed and maintained by the [Solars Systems](https://solars-systems.eu) team.
