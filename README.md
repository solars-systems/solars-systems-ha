# Solars Systems - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/solars-systems/solars-systems-ha?color=blue)](https://github.com/solars-systems/solars-systems-ha/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Integrarea oficială Home Assistant pentru platforma [Solars Systems](https://solars-systems.eu).

Permite proprietarilor de sisteme fotovoltaice (Deye, Huawei, Growatt, Victron, Fronius, Sungrow etc.) care utilizează Home Assistant să transmită telemetria în timp real și să sincronizeze istoricul complet de producție direct în platforma **Solars Systems**.

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
  * Extrage automat datele istorice de energie (kWh/zi) din statisticile Home Assistant (30 zile, 90 zile, 1 an sau tot istoricul)
  * **Idempotent:** Nu suprascrie niciodată date bune existente cu valori mai mici; dacă o zi există deja, o actualizează doar dacă noua valoare din Home Assistant este mai mare
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
3. Mergeți la **Settings** -> **Devices & Services** -> **Add Integration**, căutați **Solars Systems** și urmați pașii de configurare.

> 📖 **Aveți nevoie de ajutor sau instrucțiuni detaliate?**  
> Consultați [**Ghidul Detaliat de Instalare și Configurare (INSTALLATION.md)**](INSTALLATION.md) pentru pași amănunțiți, configurarea senzorilor, instalarea manuală și depanare.

---

## 📄 Licență

Acest proiect este licențiat sub [Licența MIT](LICENSE).  
Dezvoltat și menținut de echipa [Solars Systems](https://solars-systems.eu).
