# Solars Systems - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/solars-systems/solars-systems-ha?color=blue)](https://github.com/solars-systems/solars-systems-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The official Home Assistant integration for the [Solars Systems](https://solars-systems.eu) monitoring and management platform.

---

<details open>
<summary><b>🇬🇧 English Version (Click to collapse)</b></summary>
<br>

Allows owners of photovoltaic systems, battery storage systems, and heat pumps (SolarAssistant, Deye, Huawei, Growatt, Victron, Fronius, Sungrow, Infinisolar, Axpert, Easun, Sunclima, Modbus, etc.) using Home Assistant to stream live telemetry and synchronize historical production data seamlessly into the **Solars Systems** cloud platform.

### ✨ Key Features

* **📡 High-Performance Parallel Telemetry Streaming (`asyncio.gather`):**
  * Dispatches Inverter, BMS Battery Packs, and Heat Pump payloads concurrently, cutting update cycle latency by 3x.
  * Total Solar PV Power (W / kW) and individual power per inverter / MPPT.
  * Individual MPPT / String voltages and currents (`voltajPV1`, `voltajPV2`, `curentPV1`, etc.).
  * **Auto-Computed PV Currents:** Automatically derives $I = \frac{P}{V}$ for inverters lacking physical MPPT current sensors (InfiniSolar, Axpert, etc.).
  * Home Consumption / Load Power (W / kW).
  * **Grid / AC Input Power (`putereAcIn`):** Dedicated support for Hybrid inverters and external Smart Meters (Shelly 3EM, Eastron SDM, Carlo Gavazzi, etc.) with automatic kW to W conversion.
  * Comprehensive Battery Storage Monitoring: State of Charge (SoC %), Pack Voltage (V), Current (A), and Charge/Discharge Power (W).
  * Grid AC Voltages: AC Input (Grid) and Inverter AC Output voltage.
  * Energy Yield: Daily (today), Monthly (this month), and Yearly (this year) in kWh.
  * **Heat Pump Power in Main Power Flow (`puterePompa`):** Seamlessly passes heat pump electrical consumption into the primary inverter telemetry for live visualization in the animated Power Flow diagram.
* **🔥 Dedicated Heat Pump & HVAC Monitoring (Sunclima R290, Modbus, etc.):**
  * **Electrical & Thermal Power:** Live electrical power consumption (W / kW), cumulative total energy (kWh), instant thermal heat power (kW), and Coefficient of Performance (COP).
  * **Hydraulic Flow & Circuit Temperatures:** Real-time monitoring of Water Flow Rate (L/min), Flow Water Temp (Tur), Return Water Temp (Retur), and temperature differential ($\Delta T$).
  * **Hot Water & Buffer Storage:** Domestic Hot Water (Boiler ACM) and Thermal Buffer (Puffer) temperatures.
  * **Outdoor Ambient & Operating Status:** Ambient outdoor temperature, compressor modulation frequency (Hz), operating mode (Heating, Cooling, DHW, Auto), water circulation pump status, defrost cycle tracking, and fault alarms.
* **🔋 Advanced BMS & Multi-Cluster Battery Diagnostics (JK-BMS, Daly, Seplos, JBD, Pylontech, ESPHome, etc.):**
  * **Multi-Pack Scalability:** Configure from 1 to 16 BMS battery packs simultaneously with strict device-registry isolation and natural sorting (`natural_sort_key`) (e.g., `Baterie Jos`, `Baterie Sus`, pack 9 vs 10 vs 16).
  * **Single-Sensor Autopopulation & Dynamic Refresh:** Selecting one base sensor automatically maps all other pack metrics (SoC, voltage, current, power, temperatures, and individual cells). Changing an anchor entity immediately rediscovers and populates that pack's entities.
  * **Cell Voltage Mapping 1 - 16:** Automatically detects and maps up to 16 individual cell voltage sensors per pack (`cell_1` .. `cell_16`) using strict regex lookahead to prevent `cell_1` capturing `cell_10..16`.
  * **Cell Analytics:** Real-time tracking of lowest cell voltage (`cell_min`), highest cell voltage (`cell_max`), and cell delta (`cell_delta`).
  * **Temperatures & MOSFET:** Up to 2 battery cell temperature probes (`t1`, `t2`) and BMS power tube / MOSFET temperature (`tmos`).
  * **Switch & Binary Controls:** Monitor Charging, Discharging, Balancing, and Heating states.
* **⚡ Smart Presets & Multi-Inverter Architecture:**
  * **Presets Available:** **SolarAssistant (Auto-Detect)**, **Axpert / Voltronic / Easun (Auto-Detect)**, and **Custom** (Deye, Growatt, Huawei, Victron, etc.).
  * **Independent MPPT Configuration per Inverter:** Configure individual MPPT counts (1 to 4 MPPTs) per inverter independently, with collision prevention ensuring Inverter 2 never conflicts with Inverter 1.
  * **Flexible Entity Selection:** Full compatibility with standard sensors, custom Riemann sum helpers, Utility Meters, and template sensors without rigid Home Assistant `device_class` restrictions.
  * **Non-Destructive Re-configuration:** All previously saved sensor mappings are permanently preserved when adjusting settings via the Options Flow.
  * **Smart Anti-Cell Filter & Appliance Shield:** Excludes individual BMS cell sensors during inverter/battery selection and prevents appliances or heat pumps from being misidentified as solar entities.
  * Supports cascading / parallel setups from 1 to 6 inverters and 1 to 4 MPPT strings per inverter.
* **🌐 Native Bilingual Experience (RO / EN):**
  * Seamlessly adapts to your Home Assistant language setting (100% Romanian or 100% English).
  * Clear bilingual configuration dropdown menus, preset selection, and labels for up to 16 BMS packs and 6 inverters.
* **📊 Monotonic Historical Energy Import:**
  * Automatically extracts historical daily energy stats (kWh/day) from Home Assistant's long-term statistics (last 30 days, 90 days, 1 year, or all-time) using statistical deltas (`max - min`).
  * **Monotonic & Idempotent:** Never overwrites valid historical records with lower values; existing entries are only updated if Home Assistant provides a higher, more accurate value.
  * Emits a persistent Home Assistant notification once history import completes.
* **🔒 Secure Authentication:** Direct API Key authentication (`x-api-key`) generated from your Solars Systems account.

### ⚡ Quick Installation

1. In **HACS** -> **Integrations** -> top-right menu (`⋮`) -> **Custom repositories**, add:
   ```text
   https://github.com/solars-systems/solars-systems-ha
   ```
   *(Category: `Integration`)*
2. Download the **Solars Systems** integration and restart Home Assistant.
3. Navigate to **Settings** -> **Devices & Services** -> **Add Integration**, search for **Solars Systems**, and follow the guided setup wizard.

> 📖 **Need step-by-step instructions?**  
> Check out the [**Detailed Installation & Configuration Guide (INSTALLATION.md)**](INSTALLATION.md) for manual installation, sensor mapping tips, and troubleshooting.

### 📄 License

This project is licensed under the [MIT License](LICENSE).  
Developed and maintained by the [Solars Systems](https://solars-systems.eu) team.

</details>

<br>

<details>
<summary><b>🇷🇴 Versiunea în Limba Română (Apasă pentru a deschide)</b></summary>
<br>

Permite proprietarilor de sisteme fotovoltaice, baterii de stocare și pompe de căldură (SolarAssistant, Deye, Huawei, Growatt, Victron, Fronius, Sungrow, Infinisolar, Axpert, Easun, Sunclima, Modbus etc.) care utilizează Home Assistant să transmită telemetria în timp real și să sincronizeze istoricul complet de producție direct în platforma **Solars Systems**.

### ✨ Funcționalități Principale

* **📡 Streaming Paralel de Înaltă Performanță (`asyncio.gather`):**
  * Transmite simultan și concurent telemetria invertorului, pachetele de baterii BMS și pompa de căldură, reducând timpul ciclului de actualizare de 3 ori.
  * Putere fotovoltaică totală (W / kW) și putere defalcată per invertor / MPPT.
  * Tensiuni și curenți individuali per MPPT / String (`voltajPV1`, `voltajPV2`, `curentPV1` etc.).
  * **Auto-Calculare Curenți PV:** Calculează automat $I = \frac{P}{V}$ pentru invertoarele care nu expun senzori fizici de curent MPPT (InfiniSolar, Axpert etc.).
  * Consum locuință / Sarcină (W / kW).
  * **Putere Rețea / Grid AC In (`putereAcIn`):** Suport dedicat pentru invertoare hibride și contoare inteligente externe (Shelly 3EM, Eastron SDM, Carlo Gavazzi etc.) cu conversie automată din kW în W.
  * Monitorizare completă baterie: Nivel (SoC %), Tensiune (V), Curent (A) și Putere încărcare/descărcare (W).
  * Tensiuni rețea: Tensiune intrare AC In (Grid) și tensiune ieșire invertor AC Out (Inverter Output).
  * Energie produsă: Zilnică (azi), Lunară (luna curentă) și Anuală (anul curent) în kWh.
  * **Putere Pompă de Căldură în Fluxul Principal (`puterePompa`):** Integrează consumul electric al pompei direct în diagrama animată Power Flow de pe panoul principal Solars Systems.
* **🔥 Monitorizare Dedicată Pompe de Căldură & HVAC (Sunclima R290, Modbus etc.):**
  * **Putere Electrică & Termică:** Consum electric instant (W / kW), contorizare totală energie (kWh), căldură termică instant livrată (kW) și Coeficient de Performanță (COP).
  * **Debit Hidraulic & Temperaturi Circuit:** Monitorizare debit agent (L/min), temperatură tur apă (Tur), temperatură retur apă (Retur) și diferențial temperatură ($\Delta T$).
  * **Apă Caldă Menajeră & Puffer:** Monitorizare temperatură Boiler ACM și Puffer tampon.
  * **Exterior & Diagnosticare Funcționare:** Temperatură ambient exterior, frecvență modulație compresor (Hz), mod funcționare (Încălzire, Răcire, ACM, Auto), stare pompă recirculare, cicluri de dezghețare (Defrost) și alarme avarii.
* **🔋 Monitorizare Avansată Pachete BMS Multi-Cluster (JK-BMS, Daly, Seplos, JBD, Pylontech, ESPHome etc.):**
  * **Scalabilitate Multi-Pachet:** Configurare simultană de la 1 la 16 pachete de baterii BMS cu izolare strictă pe bază de Device Registry și sortare naturală (`natural_sort_key`) (ex: `Baterie Jos`, `Baterie Sus`, pachetele 9, 10 până la 16).
  * **Auto-Populare și Re-populare Dinamică:** Selectarea unui singur senzor de bază populează automat toți ceilalți senzori ai pachetului (SoC, tensiune, curent, putere, temperaturi și celule). Schimbarea senzorului ancoră redescoperă instant componentele acelui pachet.
  * **Mapează Automat Celulele 1 - 16:** Detectează și configurează automat toți senzorii individuali de celule (`cell_1` .. `cell_16`) folosind regex strict cu lookahead non-numeric pentru a preveni suprapunerea celulei 1 peste 10..16.
  * **Analiză Celule:** Urmărire în timp real a celei mai mici celule (`cell_min`), celei mai mari celule (`cell_max`) și a diferenței dintre celule (`cell_delta`).
  * **Temperaturi & MOSFET:** Până la 2 sonde de temperatură baterie (`t1`, `t2`) și temperatura tranzistorilor de putere MOSFET / Tube (`tmos`).
  * **Comutatoare și Stări:** Monitorizare stări Încărcare (Charging), Descărcare (Discharging), Balansare (Balancing) și Încălzire (Heating).
* **⚡ Preseturi Inteligente & Arhitectură Flexibilă:**
  * **Preseturi Disponibile:** **SolarAssistant (Auto-Detectare)**, **Axpert / Voltronic / Easun (Auto-Detectare)** și **Personalizat / Custom** (Deye, Growatt, Huawei, Victron etc.).
  * **Configurare Independentă MPPT per Invertor:** Setați numărul de intrări MPPT (1 până la 4) individual pentru fiecare invertor, cu mecanism anti-coliziune între invertoare.
  * **Selectoare Flexibile de Entități:** Compatibilitate completă cu senzori standard, ajutoare Riemann Sum (Integrale), Utility Meters și senzori Template fără blocaje de tip `device_class`.
  * **Păstrare Setări la Reconfigurare:** Toate configurările anterioare sunt păstrate permanent la reconfigurare (nu sunt suprascrise de auto-detectare).
  * **Filtru Inteligent Anti-Celule & Protecție Echipamente:** Exclude automat celulele BMS din pașii de invertor și previne asocierea eronată a electrocasnicelor sau a pompelor de căldură ca panouri solare.
  * Suportă de la 1 la 6 invertoare în paralel / cascadă și între 1 și 4 intrări MPPT per invertor.
* **🌐 Experiență Bilingvă Nativă (RO / EN):**
  * Se adaptează automat la limba setată în Home Assistant (100% Română sau 100% Engleză).
  * Meniuri dropdown bilingve clare, selecție preseturi și etichete complete pentru până la 16 BMS-uri și 6 invertoare.
* **📊 Import Istoric Inteligent (Monotonic Upsert):**
  * Extrage automat datele istorice de energie (kWh/zi) din statisticile Home Assistant (30 zile, 90 zile, 1 an sau tot istoricul) pe baza deltelor statistice reale (`max - min`).
  * **Idempotent & Monotonic:** Nu suprascrie niciodată date bune existente cu valori mai mici; dacă o zi există deja, o actualizează doar dacă noua valoare din Home Assistant este mai mare.
  * Notificare persistentă în Home Assistant la finalizarea sincronizării.
* **🔒 Securitate:** Autentificare directă prin **Cheie API** (`x-api-key`) generată din contul Solars Systems.

### ⚡ Instalare Rapidă

1. În **HACS** -> **Integrations** -> meniul din dreapta sus (`⋮`) -> **Custom repositories**, adăugați:
   ```text
   https://github.com/solars-systems/solars-systems-ha
   ```
   *(Categoria: `Integration`)*
2. Descărcați integrarea **Solars Systems** și reporniți Home Assistant.
3. Mergeți la **Settings** -> **Devices & Services** -> **Add Integration**, căutați **Solars Systems** și urmați pașii din asistentul de configurare.

> 📖 **Aveți nevoie de ajutor sau instrucțiuni detaliate?**  
> Consultați [**Ghidul Detaliat de Instalare și Configurare (INSTALLATION.ro.md)**](INSTALLATION.ro.md) pentru pași amănunțiți, configurarea senzorilor, instalarea manuală și depanare.

### 📄 Licență

Acest proiect este licențiat sub [Licența MIT](LICENSE).  
Dezvoltat și menținut de echipa [Solars Systems](https://solars-systems.eu).

</details>
