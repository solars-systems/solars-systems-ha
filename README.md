# Solars Systems - Home Assistant Integration

Integrare oficială Home Assistant pentru platforma [Solars Systems](https://solars-systems.eu).

Permite conectarea oricărui invertor sau contor monitorizat în Home Assistant direct cu platforma Solars Systems:
* **Sincronizare în timp real** (putere PV, consum, baterie, tensiuni rețea)
* **Import automat de istoric** din statisticile Home Assistant (recuperează zilele din urmă fără duplicate!)

---

## 🚀 Instalare

### Metoda 1: Prin HACS (Recomandat)
1. Deschide **HACS** în Home Assistant.
2. Mergi la **Integrations** -> meniul din dreapta sus (3 puncte) -> **Custom repositories**.
3. Adaugă linkul acestui repository, iar la categorie alege **Integration**.
4. Apasă **Download** și repornește Home Assistant.

### Metoda 2: Copiere Manuală
1. Copiază folderul `custom_components/solars_systems` în directorul `/config/custom_components/` din Home Assistant.
2. Repornește Home Assistant.

---

## ⚙️ Configurare

1. Mergi în Home Assistant la **Settings** -> **Devices & Services** -> **Add Integration**.
2. Caută **Solars Systems**.
3. Introdu **Cheia API** (API Key) din contul tău de pe [solars-systems.eu](https://solars-systems.eu) (Secțiunea Chei API).
4. Selectează invertorul din contul tău și asociază senzorii doriți (Putere PV, Consum casă, Baterie, etc.).
5. Dacă dorești, bifează **Importă istoricul de energie din trecut** pentru a transfera datele anterioare.
