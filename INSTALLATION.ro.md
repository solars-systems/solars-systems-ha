[🇬🇧 Read this guide in English](INSTALLATION.md)

# Ghid Detaliat de Instalare și Configurare

Acest ghid vă oferă toți pașii necesari pentru instalarea și configurarea integrării **Solars Systems** în Home Assistant.

---

## 📋 Cerințe Prealabile

1. **Cont Solars Systems:** Un cont activ pe [solars-systems.eu](https://solars-systems.eu) cu cel puțin un invertor înregistrat.
2. **Cheie API:** Generată din platforma Solars Systems:
   * Autentificați-vă pe [solars-systems.eu](https://solars-systems.eu)
   * Mergeți în meniu la secțiunea **Chei API** (sau Profil -> Chei API)
   * Copiați cheia generată (un șir unic de caractere).
3. **Senzori funcționali în Home Assistant:** Asigurați-vă că aveți deja senzorii invertorului/bateriei disponibili în Home Assistant (din integrări precum SolarAssistant, Huawei Solar, Solarman, Deye Modbus, Fronius, Victron, MQTT etc.).

---

## 🚀 Metoda 1: Instalare prin HACS (Recomandat)

Dacă aveți [HACS (Home Assistant Community Store)](https://hacs.xyz/) instalat:

1. Deschideți **HACS** din meniul lateral al Home Assistant.
2. Navigați la secțiunea **Integrations**.
3. În colțul din dreapta sus, apăsați pe meniul cu trei puncte (`⋮`) și alegeți **Custom repositories** (Depozite personalizate).
4. Completați câmpurile:
   * **Repository (Depozit):**
     ```text
     https://github.com/solars-systems/solars-systems-ha
     ```
   * **Type (Categorie):** `Integration`
5. Apăsați **Add** (Adăugare).
6. Căutați integrarea **Solars Systems** în lista HACS, apăsați pe ea, apoi apăsați **Download** (Descărcare) în colțul din dreapta jos.
7. **Reporniți Home Assistant:**
   * Mergeți la **Developer Tools** -> fila **YAML** (sau butonul Restart) -> **Restart Home Assistant**.

---

## 📁 Metoda 2: Instalare Manuală

Dacă nu utilizați HACS:

1. Descărcați codul sursă de pe GitHub: [solars-systems-ha Releases](https://github.com/solars-systems/solars-systems-ha/releases) sau descărcați arhiva ZIP a repository-ului.
2. Dezarhivați fișierul.
3. Copiați întregul director `custom_components/solars_systems` în folderul `config/custom_components/` al instalării dumneavoastră Home Assistant.
   * Structura căilor trebuie să fie:
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

## ⚙️ Configurare Pas cu Pas

După repornirea Home Assistant:

1. Mergeți la **Settings (Setări)** -> **Devices & Services (Dispozitive și servicii)** -> apăsați pe butonul **Add Integration (Adăugare integrare)** din dreapta jos.
2. Căutați **Solars Systems** și selectați integrarea.
3. **Pasul 1 - Autentificare:**
   * Introduceți **Cheia API** obținută de pe [solars-systems.eu](https://solars-systems.eu).
4. **Pasul 2 - Arhitectură Instalație & Preset:**
   * Selectați invertorul din contul dumneavoastră.
   * Alegeți presetul: **SolarAssistant (Detectare automată)** sau **Personalizat**.
   * Configurați numărul de invertoare și stringuri MPPT.
   * Bifați dacă sistemul are baterie de stocare.
5. **Pasul 3 - Panouri Solare & Producție (PV):**
   * Confirmați senzorii de putere solară și tensiuni MPPT (pre-selectați automat).
6. **Pasul 4 - Baterie & Stocare:**
   * Confirmați senzorii de SOC, tensiune pack și curent. *(Celulele individuale sunt filtrate automat).*
7. **Pasul 5 - Rețea, Consum & Setări:**
   * Confirmați senzorul de consum locuință și tensiune rețea.
   * Alegeți dacă doriți **Import Istoric** și intervalul live (implicit 30 secunde).
8. Apăsați **Submit**. Sistemul va începe imediat transmiterea datelor!
