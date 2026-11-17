# Solars Systems - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/solars-systems/solars-systems-ha?color=blue)](https://github.com/solars-systems/solars-systems-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Integrarea oficială Home Assistant pentru platforma [Solars Systems](https://solars-systems.eu).

Această componentă permite proprietarilor de sisteme fotovoltaice (Deye, Huawei, Growatt, Victron, Fronius, Sungrow, etc.) care folosesc Home Assistant să transmită telemetria live și să importe istoricul complet de producție direct în platforma **Solars Systems**, chiar și fără modulul hardware dedicat ESP32.

---

## ✨ Funcționalități Principale

* **📡 Telemetrie în Timp Real:**
  * Putere fotovoltaică totală (W / kW) și putere defalcată per invertor / MPPT
  * Tensiuni individuale per MPPT / String (`voltajPV1`, `voltajPV1_2`, `voltajPV2`, etc.)
  * Consum locuință / Sarcină (W / kW)
  * Monitorizare completă baterie: Nivel (SoC %), Tensiune (V), Curent (A) și Putere încărcare/descărcare (W)
  * Tensiuni rețea: Tensiune intrare AC In (Grid) și tensiune ieșire invertor AC Out (Inverter Output)
  * Energie produsă: Zilnică (zi), Lunară (lună) și Anuală (an) în kWh
* **⚡ Arhitectură Flexibilă (Multi-Invertor & Multi-MPPT):**
  * Suportă de la 1 la 6 invertoare în cascadă / paralel
  * Suportă între 1 și 4 intrări MPPT per invertor
  * Generează dinamic câmpurile necesare pentru maparea fiecărui string fotovoltaic
* **📊 Import Istoric Inteligent (Monotonic Upsert):**
  * Extrage automat datele istorice de energie (kWh/zi) din modulul `recorder` al Home Assistant (30 zile, 90 zile, 1 an sau tot istoricul)
  * **Idempotent:** Nu suprascrie niciodată date bune existente cu valori mai mici; dacă o zi există deja, o actualizează doar dacă noua valoare din Home Assistant este mai mare
  * Trimite notificare persistentă în Home Assistant la finalizarea sincronizării istoricului
* **🔒 Securitate:**
  * Autentificare directă prin **Cheie API** (`x-api-key`) generată din contul Solars Systems

---

## 📋 Cerințe

1. Un cont activ pe [solars-systems.eu](https://solars-systems.eu) cu cel puțin un invertor adăugat în cont.
2. O **Cheie API** generată din platformă (**Meniu -> Chei API**).
3. Home Assistant (versiune minimă 2023.x sau mai nouă) cu integrarea `recorder` activă (activă implicit în HA).

---

## 🚀 Instalare

### Opțiunea 1: Prin HACS (Recomandat)

1. În interfața Home Assistant, deschideți **HACS**.
2. Faceți clic pe **Integrations** -> meniul din dreapta sus (cele trei puncte `⋮`) -> **Custom repositories**.
3. În câmpul **Repository**, introduceți:
   ```text
   https://github.com/solars-systems/solars-systems-ha
   ```
4. La **Type**, selectați **Integration** și apăsați **Add**.
5. Căutați integrarea **Solars Systems**, apăsați **Download** și selectați ultima versiune.
6. Reporniți Home Assistant (**Developer Tools** -> **Restart**).

### Opțiunea 2: Instalare Manuală

1. Descărcați arhiva repo-ului sau clonați proiectul.
2. Copiați întregul folder `custom_components/solars_systems` în directorul `/config/custom_components/` din instanța dumneavoastră de Home Assistant.
   *(Structura finală va fi: `/config/custom_components/solars_systems/...`)*
3. Reporniți Home Assistant.

---

## ⚙️ Configurare Pas cu Pas

După repornire:

1. Mergeți în Home Assistant la **Settings (Setări)** -> **Devices & Services (Dispozitive și servicii)** -> **Add Integration (Adăugare integrare)**.
2. Căutați **Solars Systems**.
3. **Pasul 1 - Autentificare:**
   * Introduceți **Cheia API** obținută din contul dumneavoastră Solars Systems.
4. **Pasul 2 - Arhitectură Instalație:**
   * **Invertor Solars Systems:** Selectați invertorul din contul dvs. în care se vor salva datele.
   * **Număr de invertoare:** Alegeți câte invertoare aveți instalate (1 - 6).
   * **Număr de MPPT-uri:** Alegeți numărul de MPPT-uri per invertor (1 - 4).
5. **Pasul 3 - Asignare Senzori:**
   * Asociați entitățile de senzori din Home Assistant pentru fiecare câmp disponibil (putere PV, consum, baterie, tensiuni rețea, producție zilnică/lunară/anuală și intrările MPPT configurate).
   * Integrarea detectează automat senzorii compatibili pe baza clasei de dispozitiv (`power`, `energy`, `voltage`, `battery`).
   * Bifați **Importă istoricul de energie din trecut** dacă doriți să preluați datele zilnice anterioare din baza de date a Home Assistant.
6. Apăsați **Submit**.

---

## 🔄 Funcționare și Transmisie Date

* Datele live sunt citite din senzorii selectați și transmise către server la fiecare **30 de secunde** (interval configurabil).
* Dacă ați optat pentru importul istoricului, un proces asincron în fundal va citi statisticile orare/zilnice din `recorder`, le va grupa pe zile calendaristice și le va trimite în pachete către platformă.
* Când importul este finalizat, veți primi o notificare în bara laterală a Home Assistant cu numărul de zile procesate cu succes.

---

## 🛠️ Depanare (Troubleshooting)

* **Eroare "Cheie API invalidă":** Verificați dacă ați copiat corect cheia din secțiunea **Chei API** din panoul Solars Systems și că utilizatorul are cel puțin un invertor asignat.
* **Datele nu apar pe grafic:** Verificați dacă senzorii selectați în pasul 3 au stări numerice valide în Home Assistant (**Developer Tools** -> **States**).
* **Consolă / Log-uri:** Pentru log-uri detaliate, puteți adăuga în `configuration.yaml`:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.solars_systems: debug
  ```

---

## 📄 Licență

Acest proiect este licențiat sub [Licența MIT](LICENSE).
Dezvoltat și menținut de comunitatea [Solars Systems](https://solars-systems.eu).
