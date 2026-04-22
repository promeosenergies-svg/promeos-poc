# Protocoles de communication — sous-comptage électrique & intégration GTB/BMS

**Source** : Base de connaissance ChatGPT (doc utilisateur, avril 2026, 21p)
**Cible PROMEOS** : informer les modules Flex Ready, Capacité, Site360 (scoring protocol-readiness), roadmap intégration GTB multisite (parcs bancaires/ETI)
**Statut** : référence technique, non réglementaire

---

## Taxonomie (6 familles)

| Famille | Protocoles | Couche | Usage |
|---|---|---|---|
| Sous-comptage | Modbus RTU/TCP/Security, M-Bus (EN 13757-2/3), Wireless M-Bus/OMS, DLMS/COSEM (IEC 62056), IEC 62056-21, S0, IR | Physique → Application | Relevé index, puissances, télérelève |
| GTB/BMS | BACnet (MS/TP, IP, SC), KNX (TP/IP/RF, Secure), LonWorks/LonTalk, DALI/DALI-2/D4i, OPC UA, SNMP v1/v2c/v3, MQTT, Modbus TCP, PROFINET, EtherNet/IP, IEC 61850 | Liaison → Application | CVC, éclairage, supervision |
| Cloud/IT | OPC UA, MQTT, HTTP/REST, SNMP v3, BACnet/SC | Transport TLS + Application | Agrégation multisite, API SaaS |
| Radio/LPWAN/IoT | Wireless M-Bus, LoRaWAN, Wi-SUN, Zigbee Smart Energy, KNX RF, BLE | Sub-GHz / 2.4 GHz | Collecte sans fil, sites difficiles à câbler |
| Industriels | PROFINET, EtherNet/IP, IEC 61850, LonWorks | Liaison + Réseau | Usines, postes électriques |
| Interfaces simples | S0, TOR, impulsions, IR | Physique seul | Rétrofit, comptage impulsions |

---

## Scoring pertinence pour cible PROMEOS (parc multisite B2B)

Notation 0-10 sur 8 critères. Extrait du scoring doc → synthèse table ci-dessous.

| Protocole | Sous-compteur | Parc multisite | Rénovation | Neuf | GTB existante | Pilotage | Cloud | Cybersécu |
|---|---|---|---|---|---|---|---|---|
| **Modbus RTU/TCP** | **9** | 7 | 8 | 7 | 8 | 4 | 5 | 3 (7 avec Security) |
| **M-Bus / W-MBus / OMS** | 8 | 7 | 6 | 8 | 6 | 2 | 6 | 7 |
| **DLMS/COSEM** | 6 | 7 | 4 | 7 | 4 | 6 | 5 | **8** |
| **BACnet (MS/TP → IP → SC)** | 6 | **9** | 8 | **10** | **10** | 9 | 6 | 4 → **9** (SC) |
| **KNX Secure** | 3 | 5 | 6 | 8 | 7 | 9 | 4 | 8 |
| **DALI/DALI-2/D4i** | 2 | 3 | 5 | 6 | 7 | 9 (éclairage) | 3 | 2 |
| **OPC UA** | 3 | 7 | 5 | 8 | 6 | 5 | **9** | **9** |
| **MQTT** | 3 | 8 | 6 | 9 | 7 | 6 | **9** | 8 |
| **SNMP v3** | 1 | 4 | 3 | 4 | 6 | 2 | 5 | 8 |
| **LoRaWAN / Wi-SUN** | 7 (sites isolés) | 8 | 7 | 6 | 3 | 2 | 7 | 8 |
| **S0 / TOR / IR** | 7 (secours) | 5 | 8 | 5 | 2 | 1 | 1 | 3 |
| LonWorks | 2 | 4 | 6 (brownfield) | 2 | 5 | 6 | 2 | 3 |
| Zigbee Smart Energy | 5 | 4 | 4 | 5 | 4 | 5 | 4 | 6 |
| PROFINET / EtherNet/IP | 2 | 3 | 2 | 3 | 5 | 6 | 2 | 4 |
| IEC 61850 | 1 | 3 | 1 | 2 | 3 | 7 (postes HT) | 2 | 7 |

---

## Hiérarchie retenue pour PROMEOS (parc multisite type banque/ETI)

### Cœur (support natif requis)

1. **Modbus RTU/TCP + Modbus Security** — majorité des sous-compteurs BT
2. **BACnet (MS/TP + IP + BACnet/SC TLS 1.3)** — CVC, alarmes, éclairage ; migration SC obligatoire pour cybersécu
3. **M-Bus / Wireless M-Bus / OMS (EN 13757, AES-128)** — relevé eau/chaleur/gaz, sites sans câble
4. **KNX Secure (ISO/IEC 14543-3, AES-128 CCM)** — éclairage/CVC en agences neuves
5. **OPC UA (OPC Foundation) + MQTT (OASIS)** — cloud, normalisation data, EMS
6. **SNMP v3** — supervision IT des passerelles/routeurs

### Passerelles (support indirect via gateway)

- **DLMS/COSEM / IEC 62056-21** — compteurs réglementés (Linky, smart grid), via concentrateurs
- **DALI / DALI-2 / D4i (IEC 62386)** — éclairage, via passerelle DALI→BACnet/KNX
- **LoRaWAN / Wi-SUN (IEEE 802.15.4g)** — sites isolés, via gateway LPWAN→MQTT
- **LonWorks / Zigbee** — brownfield uniquement, via convertisseurs
- **PROFINET / EtherNet/IP / IEC 61850** — campus industriel avec poste source, via OPC UA

### À éviter

- **BACnet MS/TP sans SC** (brownfield acceptable, migrer vers SC)
- **Modbus RTU sans Security** (segmenter, isoler)
- **LonWorks** en greenfield (coût + maintenance)
- **S0/TOR/IR** sauf dernier recours, convertir vers Modbus/MQTT

---

## 4 architectures de référence

| # | Type | Schéma logique | Cas d'usage |
|---|---|---|---|
| 1 | **Brownfield minimaliste** | Modbus RTU/M-Bus → converter → gateway local → VPN cloud | Rénovation light agence existante |
| 2 | **Brownfield + GTB** | GTB BACnet MS/TP+IP maintenue, passerelles Modbus→BACnet, BACnet/SC backbone, OPC UA/MQTT vers cloud | Sites avec GTB CVC en place |
| 3 | **Greenfield tertiaire** | Sous-compteurs Modbus/TCP + M-Bus, automates BACnet/SC, KNX Secure éclairage, passerelle OPC UA/MQTT | Agences neuves / rénovations profondes |
| 4 | **Cybersécu renforcée** | Isolation bus + VLAN + BACnet/SC + KNX Secure + TLS Modbus + OPC UA auth X.509 + SNMP v3 + DMZ | Sites bancaires critiques, data centers |
| 5 | **Multisite scalable** | Gateway edge par agence + brokers MQTT/OPC UA + SaaS central + LoRaWAN sites isolés | Réseau national d'agences |
| 6 | **Pilotage avancé** | Sous-comptage complet + BACnet/SC + LoRaWAN + OPC UA/MQTT + analytics cloud + MQTT QoS 2 temps réel | Sièges, demand-response, IA optimisation |

---

## Sécurité — état de l'art par protocole

- **BACnet/SC** : TLS 1.3 + WebSockets + X.509 mutuel, hub-and-spoke (Beckhoff)
- **KNX Secure** : AES-128 CCM sur bus (Data Secure) + IP (IP Secure), certifié VDE
- **Modbus Security** : TLS + authentification X.509 (modbus.org spec)
- **M-Bus / OMS** : AES-128 CCM natif (confidentialité + intégrité)
- **OPC UA** : X.509, chiffrement, signatures, contrôle d'accès, audit natif
- **MQTT** : TLS + OAuth/tokens (sécurité déléguée au transport)
- **SNMP v3** : authentification MD5/SHA + chiffrement DES/AES
- **DLMS/COSEM** : AES/GCM selon profil, gestion clés
- **Zigbee / LoRaWAN** : AES-128 end-to-end
- **DALI, LonWorks, BACnet MS/TP, Modbus RTU** : aucune sécu native → isolation physique

---

## Angles PROMEOS (applications produit)

### Module Flex Ready (baromètre flex 2026)
La norme NF EN IEC 62746-4 (Flex Ready®) suppose une interop GTB sécurisée. Ce document confirme que **BACnet/SC + OPC UA + KNX Secure** sont les briques minimales pour un site flex-ready en 2026. Site avec seul Modbus RTU non sécurisé + BACnet MS/TP = bloquant pour certification Flex Ready.

### Module Capacité Nov 2026
Le scoring `compute_asset_eligibility` en `backend/services/capacity/eligibility.py` mentionne `has_teleometrie` + `has_flex_ready_gtb` comme blockers. Ces blockers peuvent être enrichis avec une vérification **protocoles en place** : site avec BACnet/SC → green ; site avec seul Modbus non secure → amber (reste à passerelle) ; site full S0/impulsions → red.

### Site360 / Patrimoine
Ajouter un champ `protocols_available: list[str]` sur le modèle `Site` pour tracer quels protocoles sont présents. Permet scoring "protocol readiness" pour :
- Eligibilité flex
- Compatibilité sous-comptage automatique
- Priorisation investissement GTB par site

### Cockpit (segment ETI / bancaire multisite)
Les 6 architectures de référence sont des patterns d'investissement. Ajouter un indicateur "architecture maturity" par portefeuille (1 brownfield → 6 pilotage avancé).

---

## Normes citées

- **Modbus** : spec Modicon (1979), Modbus/TCP (MBAP), modbussecurityprotocol.pdf
- **M-Bus** : EN 13757-2 (filaire), EN 13757-3 (application), EN 13757-4 (radio)
- **DLMS/COSEM** : IEC 62056 (suite), OBIS codes, DLMS UA certification
- **BACnet** : ASHRAE 135, ISO 16484-5, BTL certification
- **KNX** : ISO/IEC 14543-3
- **DALI** : IEC 62386 (DALI-2 DALI Alliance, D4i)
- **OPC UA** : OPC Foundation spec, indépendant plateforme
- **LonWorks** : ISO/IEC 14908
- **PROFINET** : PI org, canaux RT/IRT
- **EtherNet/IP** : ODVA + CIP
- **IEC 61850** : Logical Nodes, MMS/GOOSE/SV, cybersécu IEC 62351
- **S0** : DIN 43864 / EN 62053-31
- **IEEE 802.15.4** : Zigbee, Wi-SUN base

## Sources URLs (non garanties, à vérifier si citation officielle requise)

- beckhoff.com — BACnet/SC
- opcfoundation.org — OPC UA
- mqtt.org — MQTT
- fortinet.com — SNMP
- digi.com — LoRaWAN, Wi-SUN
- knx.org — KNX Secure
- modbus.org — Modbus Security PDF
- stackforce.com — M-Bus
- networkthermostat.com — BACnet MS/TP
- wattsense.com — BACnet overview
- profinet.com — PROFINET
- kalkitech.com — IEC 61850
- teldat.com — Zigbee Smart Energy
- holosys.eu — M-Bus wired vs wireless
- lansensystems.com — OMS
- en.wikipedia.org/wiki/IEC_62056 — DLMS
- dlms.com — Core specs
- ampvortex.com — KNX standard
- dali-alliance.org — D4i
- lumoscontrols.com — DALI-2 vs D4i
- odva.org — CIP/EtherNet-IP
- wago.com — LonWorks
- csimn.com — LonWorks tutorial
