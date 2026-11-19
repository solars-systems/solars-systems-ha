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
3. **Senzori Funcționali în Home Assistant:** Asigurați-vă că senzorii invertorului, ai bateriei sau ai BMS-ului sunt deja funcționali în Home Assistant (ex: din SolarAssistant, Huawei Solar, Solarman, Deye Modbus, Fronius, Victron, ESPHome, JK-BMS, Daly, MQTT etc.).

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
   * Alegeți presetul: **SolarAssistant (Detectare automată)**, **Axpert / Voltronic / Easun** sau **Personalizat / Custom**.
   * Configurați numărul de invertoare și bifați dacă aveți pachete BMS integrate în Home Assistant (JK, Daly, Seplos, Pylontech etc.).
   * Specificați dacă sistemul include baterie de stocare.
5. **Pasul 3 - Panouri Solare & Producție (PV):**
   * Confirmați senzorii de putere solară și tensiuni MPPT (detectați și pre-populați automat).
6. **Pasul 4 - Baterie & Stocare (Opțional):**
   * Confirmați senzorii principali ai bateriei (SOC %, tensiune pachet, curent). *(Sutele de senzori de celule individuale sunt filtrate automat pentru o listă curată).*
7. **Pasul 4b - Pachete Baterii BMS & Celule (Opțional):**
   * Dacă ați activat opțiunea BMS, alegeți numărul de pachete (de la 1 la 10).
   * **Auto-Populare Automată:** Home Assistant detectează și pre-completează automat:
     * **Toate celulele de la 1 la 16** (`cell_voltage_1` .. `cell_voltage_16`)
     * **Tensiune minimă, maximă și diferență celule (Delta)**
     * **Temperaturile** (Sonda 1, Sonda 2, MOSFET / Tube)
     * **Comutatoare și stări ON/OFF** (Încărcare, Descărcare, Balansare, Încălzire)
8. **Pasul 5 - Rețea, Consum Casă & Setări:**
   * Confirmați consumul casei și tensiunea rețelei.
   * Alegeți dacă doriți **Import Istoric** și setați intervalul de transmitere live (implicit: 30 secunde).
9. Apăsați **Submit**. Telemetria dvs. solară live și istoricul de producție vor începe să se sincronizeze instant în Solars Systems!
