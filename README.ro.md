[🇬🇧 Read this page in English](README.md)

# Solars Systems - Integrare Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/solars-systems/solars-systems-ha?color=blue)](https://github.com/solars-systems/solars-systems-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Integrarea oficială Home Assistant pentru platforma [Solars Systems](https://solars-systems.eu).

Permite proprietarilor de sisteme fotovoltaice, baterii de stocare și pompe de căldură (SolarAssistant, Deye, Huawei, Growatt, Victron, Fronius, Sungrow, Infinisolar, Axpert, Easun, Sunclima, Modbus etc.) care utilizează Home Assistant să transmită telemetria în timp real și să sincronizeze istoricul complet de producție direct în platforma **Solars Systems**.

---

## ✨ Funcționalități Principale

* **📡 Telemetrie în Timp Real:**
  * Putere fotovoltaică totală (W / kW) și putere defalcată per invertor / MPPT
  * Tensiuni și curenți individuali per MPPT / String (`voltajPV1`, `voltajPV2`, `curentPV1` etc.)
  * **Auto-Calculare Curenți PV:** Calculează automat $I = \frac{P}{V}$ pentru invertoarele care nu expun senzori fizici de curent MPPT (InfiniSolar, Axpert etc.)
  * Consum locuință / Sarcină (W / kW)
  * **Putere Rețea / Grid AC In (`putereAcIn`):** Suport dedicat pentru invertoare hibride și contoare inteligente externe (Shelly 3EM, Eastron SDM, Carlo Gavazzi etc.) cu conversie automată din kW în W
  * Monitorizare completă baterie: Nivel (SoC %), Tensiune (V), Curent (A) și Putere încărcare/descărcare (W)
  * Tensiuni rețea: Tensiune intrare AC In (Grid) și tensiune ieșire invertor AC Out (Inverter Output)
  * Energie produsă: Zilnică (azi), Lunară (luna curentă) și Anuală (anul curent) în kWh
* **🔥 Monitorizare Dedicată Pompe de Căldură & HVAC (Sunclima R290, Modbus etc.):**
  * **Putere Electrică & Termică:** Consum electric instant (W / kW), contorizare totală energie (kWh), căldură termică instant livrată (kW) și Coeficient de Performanță (COP)
  * **Debit Hidraulic & Temperaturi Circuit:** Monitorizare debit agent (L/min), temperatură tur apă (Tur), temperatură retur apă (Retur) și diferențial temperatură ($\Delta T$)
  * **Apă Caldă Menajeră & Puffer:** Monitorizare temperatură Boiler ACM și Puffer tampon
  * **Exterior & Diagnosticare Funcționare:** Temperatură ambient exterior, frecvență modulație compresor (Hz), mod funcționare (Încălzire, Răcire, ACM, Auto), stare pompă recirculare, cicluri de dezghețare (Defrost) și alarme avarii
* **🔋 Monitorizare Avansată Pachete BMS Multi-Cluster (JK-BMS, Daly, Seplos, JBD, Pylontech, ESPHome etc.):**
  * **Scalabilitate Multi-Pachet:** Configurare simultană de la 1 la 16 pachete de baterii BMS cu dezambiguizare clustere (ex: `Baterie Jos`, `Baterie Sus`, pachetele 9 și 10)
  * **Auto-Populare dintr-un Singur Senzor:** Selectarea unui singur senzor de bază populează automat toți ceilalți senzori ai pachetului (SoC, tensiune, curent, putere, temperaturi și celule)
  * **Mapează Automat Celulele 1 - 16:** Detectează și configurează automat toți senzorii individuali de celule (`cell_1` .. `cell_16`) în câteva secunde
  * **Analiză Celule:** Urmărire în timp real a celei mai mici celule (`cell_min`), celei mai mari celule (`cell_max`) și a diferenței dintre celule (`cell_delta`)
  * **Temperaturi:** Până la 2 sonde de temperatură baterie (`t1`, `t2`) și temperatura tranzistorilor de putere MOSFET / Tube (`tmos`)
  * **Comutatoare și Stări:** Monitorizare stări Încărcare (Charging), Descărcare (Discharging), Balansare (Balancing) și Încălzire (Heating)
* **⚡ Preseturi Inteligente & Arhitectură Flexibilă:**
  * **Preseturi Disponibile:** **SolarAssistant (Auto-Detectare)**, **Axpert / Voltronic / Easun** și **Personalizat / Custom** (Deye, Growatt, Huawei, Victron etc.)
  * **Păstrare Setări la Reconfigurare:** Toate configurările anterioare sunt păstrate permanent la reconfigurare (nu sunt suprascrise de auto-detectare)
  * **Filtru Inteligent Anti-Celule:** Exclude automat sutele de senzori de celule individuale în pașii de invertor și baterie principală, păstrând listele curate
  * **Protecție Electrocasnice & Pompe de Căldură:** Filtre avansate care împiedică asocierea eronată a pompelor de căldură, climatizării sau tabletelor de perete la invertoare
  * Suportă de la 1 la 6 invertoare în paralel / cascadă și între 1 și 4 intrări MPPT per invertor
* **🌐 Experiență Bilingvă Nativă (RO / EN):**
  * Se adaptează automat la limba setată în Home Assistant (100% Română sau 100% Engleză)
  * Meniuri dropdown bilingve clare în asistentul de configurare
* **📊 Import Istoric Inteligent (Monotonic Upsert):**
  * Extrage automat datele istorice de energie (kWh/zi) din statisticile Home Assistant (30 zile, 90 zile, 1 an sau tot istoricul)
  * **Idempotent & Monotonic:** Nu suprascrie niciodată date bune existente cu valori mai mici; dacă o zi există deja, o actualizează doar dacă noua valoare din Home Assistant este mai mare
  * Notificare persistentă în Home Assistant la finalizarea sincronizării
* **🔒 Securitate:** Autentificare directă prin **Cheie API** (`x-api-key`) generată din contul Solars Systems

---

## ⚡ Instalare Rapidă

1. În **HACS** -> **Integrations** -> meniul din dreapta sus (`⋮`) -> **Custom repositories**, adăugați:
   ```text
   https://github.com/solars-systems/solars-systems-ha
   ```
   *(Categoria: `Integration`)*
2. Descărcați integrarea **Solars Systems** și reporniți Home Assistant.
3. Mergeți la **Settings** -> **Devices & Services** -> **Add Integration**, căutați **Solars Systems** și urmați pașii din asistentul de configurare.

> 📖 **Aveți nevoie de ajutor sau instrucțiuni detaliate?**  
> Consultați [**Ghidul Detaliat de Instalare și Configurare (INSTALLATION.ro.md)**](INSTALLATION.ro.md) pentru pași amănunțiți, configurarea senzorilor, instalarea manuală și depanare.

---

## 📄 Licență

Acest proiect este licențiat sub [Licența MIT](LICENSE).  
Dezvoltat și menținut de echipa [Solars Systems](https://solars-systems.eu).
