[🇬🇧 Read this guide in English](INSTALLATION.md)

# Ghid Detaliat de Instalare și Configurare

Acest ghid oferă toți pașii necesari pentru instalarea, configurarea și personalizarea integrării **Solars Systems** în Home Assistant.

---

## 📋 Cerințe Preliminare

1. **Cont Solars Systems:** Un cont activ pe [solars-systems.eu](https://solars-systems.eu) cu cel puțin un invertor înregistrat.
2. **Cheie API:** Generată din platforma Solars Systems:
   * Conectați-vă pe [solars-systems.eu](https://solars-systems.eu)
   * Mergeți la secțiunea **Chei API** (sau Profil -> Chei API)
   * Copiați cheia generată (un token unic securizat).
3. **Senzori Funcționali în Home Assistant:** Asigurați-vă că senzorii invertorului, ai bateriei, BMS-ului sau pompei de căldură sunt deja funcționali în Home Assistant (ex: din SolarAssistant, Huawei Solar, Solarman, Deye Modbus, Fronius, Victron, ESPHome, JK-BMS, Daly, Seplos, Sunclima, MQTT etc.). Entitățile create prin Helpers (Riemann sum / Integrale, Utility Meters, Template Sensors) sunt pe deplin suportate.

---

## 🚀 Metoda 1: Instalare prin HACS (Recomandată)

Dacă aveți [HACS (Home Assistant Community Store)](https://hacs.xyz/) instalat:

1. Deschideți **HACS** din bara laterală Home Assistant.
2. Accesați secțiunea **Integrations**.
3. În colțul din dreapta sus, apăsați pe meniul cu trei puncte (`⋮`) și selectați **Custom repositories**.
4. Completați:
   * **Repository:**
     ```text
     https://github.com/solars-systems/solars-systems-ha
     ```
   * **Tip / Categorie:** `Integration`
5. Apăsați pe **Add**.
6. Găsiți integrarea **Solars Systems** în lista HACS, apăsați pe ea și dați **Download** în colțul din dreapta jos.
7. **Reporniți Home Assistant:**
   * Mergeți la **Developer Tools** -> apăsați **Restart Home Assistant**.

---

## 📁 Metoda 2: Instalare Manuală

Dacă nu utilizați HACS:

1. Descărcați codul sursă din secțiunea GitHub Releases: [solars-systems-ha Releases](https://github.com/solars-systems/solars-systems-ha/releases) sau arhiva ZIP a repository-ului.
2. Dezarhivați fișierul descărcat.
3. Copiați întregul folder `custom_components/solars_systems` în directorul `config/custom_components/` al instanței dvs. Home Assistant.
   * Structura de directoare trebuie să arate astfel:
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
4. Reporniți Home Assistant.

---

## ⚙️ Asistentul de Configurare Pas cu Pas

După repornirea Home Assistant:

1. Mergeți la **Settings** -> **Devices & Services** -> apăsați butonul **Add Integration** din dreapta jos.
2. Căutați **Solars Systems** și selectați-l.
3. **Pasul 1 - Autentificare:**
   * Introduceți **Cheia API** obținută de pe [solars-systems.eu](https://solars-systems.eu).
4. **Pasul 2 - Arhitectură Sistem & Preset:**
   * Selectați invertorul din contul dvs.
   * Alegeți presetul: **SolarAssistant (Detectare automată)**, **Axpert / Voltronic / Easun (Detectare automată)** sau **Personalizat / Custom**.
   * Configurați numărul de invertoare (1 până la 6).
   * Bifați subsistemele prezente: Baterie de stocare, Pachete BMS integrate (JK, Daly, Seplos, Pylontech etc.) și Pompă de căldură / HVAC.
5. **Pasul 2b - Configurare MPPT per Invertor:**
   * Alegeți numărul de șiruri MPPT (între 1 și 4 intrări) în mod independent pentru fiecare invertor.
6. **Pasul 3 - Panouri Solare & Producție (PV):**
   * Confirmați senzorii de putere solară și tensiuni/curenți MPPT (detectați și pre-populați automat fără coliziuni).
   * Suport complet pentru ajutoare personalizate (Riemann sum, contoare Utility Meter, template sensors).
7. **Pasul 4 - Baterie & Stocare (Opțional):**
   * Confirmați senzorii principali ai bateriei (SOC %, tensiune pachet, curent, putere). *(Sutele de senzori de celule individuale sunt filtrate automat pentru o listă curată).*
8. **Pasul 4b - Pachete Baterii BMS & Celule (Opțional):**
   * Dacă ați activat opțiunea BMS, alegeți numărul de pachete (de la 1 la 16).
   * **Auto-Populare Inteligentă:** Home Assistant detectează și pre-completează automat:
     * **Toate celulele de la 1 la 16** (`cell_voltage_1` .. `cell_voltage_16`) folosind regex strict cu lookahead non-numeric.
     * **Tensiune minimă, maximă și diferență celule (Delta)**.
     * **Temperaturile** (Sonda 1, Sonda 2, MOSFET / Tube).
     * **Comutatoare și stări ON/OFF** (Încărcare, Descărcare, Balansare, Încălzire).
   * La schimbarea oricărui senzor ancoră din formular, toate celulele pachetului respectiv se redescoperă automat în timp real.
9. **Pasul 4c - Pompă de Căldură & HVAC (Opțional):**
   * Dacă pompa este activată, configurați debitul de apă (L/min), temperaturile Tur/Retur, puterea electrică (W/kW), COP, puterea termică instantă, temperaturile ACM/Puffer și stările de funcționare.
10. **Pasul 5 - Rețea, Consum Casă & Setări:**
    * Confirmați consumul casei și tensiunea/puterea rețelei (`putereAcIn`).
    * Alegeți dacă doriți **Import Istoric** (folosește delte statistice calculate precis fără spike-uri) și setați intervalul de transmitere live (implicit: 30 secunde).
11. Apăsați **Submit**. Telemetria dvs. solară live și istoricul de producție vor începe să se sincronizeze instant în Solars Systems!
