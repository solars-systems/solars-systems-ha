# Ghid Detaliat de Instalare și Configurare

Acest ghid vă oferă toți pașii necesari pentru instalarea și configurarea integrării **Solars Systems** în Home Assistant.

---

## 📋 Cerințe Prealabile

1. **Cont Solars Systems:** Un cont activ pe [solars-systems.eu](https://solars-systems.eu) cu cel puțin un invertor înregistrat.
2. **Cheie API:** Generată din platforma Solars Systems:
   * Autentificați-vă pe [solars-systems.eu](https://solars-systems.eu)
   * Mergeți în meniu la secțiunea **Chei API** (sau Profil -> Chei API)
   * Copiați cheia generată (un șir unic de caractere).
3. **Senzori funcționali în Home Assistant:** Asigurați-vă că aveți deja senzorii invertorului/bateriei disponibili în Home Assistant (din integrări precum Huawei Solar, Solarman, Deye Modbus, Fronius, Victron, MQTT etc.).

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
   * Mergeți la **Developer Tools (Instrumente de dezvoltare)** -> fila **YAML** (sau butonul Restart) -> **Restart Home Assistant**.

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
               ├── config_flow.py
               ├── const.py
               ├── manifest.json
               ├── strings.json
               └── translations/
                   ├── en.json
                   └── ro.json
     ```
4. **Reporniți Home Assistant**.

---

## ⚙️ Configurare Pas cu Pas

După repornirea Home Assistant:

### Pasul 1: Adăugarea integrării
1. Mergeți la **Settings (Setări)** -> **Devices & Services (Dispozitive și servicii)**.
2. Apăsați pe butonul albastru **Add Integration (Adăugare integrare)** din colțul din dreapta jos.
3. Tastați **Solars Systems** în caseta de căutare și selectați integrarea.

### Pasul 2: Autentificarea cu Cheia API
* În fereastra apărută, introduceți **Cheia API** copiată de pe [solars-systems.eu](https://solars-systems.eu).
* Apăsați **Submit**. Integrarea va valida cheia și va încărca lista de invertoare din contul dumneavoastră.

### Pasul 3: Arhitectura Instalației (Layout)
Configurați structura fizică a sistemului fotovoltaic:
* **Invertor Solars Systems:** Selectați invertorul țintă din contul dvs. în care doriți să fie trimise datele.
* **Număr de invertoare:** Dacă aveți mai multe invertoare legate în cascadă / paralel, alegeți numărul total (1 - 6).
* **Număr de MPPT-uri per invertor:** Alegeți numărul de intrări MPPT utilizate per invertor (1 - 4).
* Apăsați **Submit**.

### Pasul 4: Asignarea Senzorilor
Integrarea va genera dinamic câmpurile necesare și va pre-selecta senzorii compatibili detectați automat în Home Assistant:
* **Putere Totală Solară (W / kW):** Senzorul de putere PV combinată.
* **Tensiuni și Puteri MPPT:** Câmpuri dedicate pentru fiecare MPPT/string (`MPPT 1 Voltaj`, `MPPT 1 Putere`, `MPPT 2 Voltaj`, etc.).
* **Consum Casă (W / kW):** Puterea consumată de sarcinile locuinței.
* **Baterie:**
  * Nivel SoC (%)
  * Tensiune (V)
  * Curent (A)
  * Putere (W)
* **Rețea & Ieșire:**
  * Tensiune Rețea AC In (V)
  * Tensiune Ieșire Invertor AC Out (V)
* **Energie Produsă (kWh):**
  * Zilnică (zi)
  * Lunară (opțional)
  * Anuală (opțional)
* **Import istoric din trecut:** Bifați această opțiune dacă doriți să preluați datele zilnice anterioare stocate în istoricul Home Assistant (`30 zile`, `90 zile`, `1 an` sau `Tot istoricul`).
* **Interval actualizare:** Implicit 30 secunde.

Apăsați **Submit**. Configurația este salvată, iar telemetria începe să fie trimisă automat.

---

## 🛠️ Depanare (Troubleshooting)

### Cheie API invalidă
* Asigurați-vă că ați copiat întreaga cheie API fără spații libere la început sau la sfârșit.
* Verificați dacă pe [solars-systems.eu](https://solars-systems.eu) aveți cel puțin un invertor activ în cont.

### Datele nu se actualizează pe platformă
1. Mergeți în Home Assistant la **Developer Tools** -> **States** și verificați dacă senzorii selectați au valori numerice valide (nu `unknown` sau `unavailable`).
2. Verificați conexiunea la internet a instanței Home Assistant (trebuie să poată accesa `https://api.solars-systems.eu`).
3. Activați jurnalizarea de depanare adăugând în `configuration.yaml`:
   ```yaml
   logger:
     default: info
     logs:
       custom_components.solars_systems: debug
   ```
4. Reporniți Home Assistant și consultați fișierul `home-assistant.log`.
