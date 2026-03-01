# RAG Süsteemi Testlogide Kokkuvõte

**Kuupäev:** 2026-03-01  
**Testitud päringuid:** 10  
**Mudel:** google/gemma-3-27b-it  

---

## Tulemuste ülevaade

| Tulemus | Arv | Osakaal |
|---------|:---:|:-------:|
| 👍 Hea | 4 | 40% |
| 👎 Halb | 6 | 60% |

---

## Vigade jaotus vahesammude kaupa

| Vahesamm | Vigade arv | % kõikidest vigadest |
|----------|:----------:|:--------------------:|
| Samm 1 – metaandmete filtreerimine (filtrid liiga karmid/valed) | 2 | 33% |
| Samm 2 – RAG vektorotsing (leiti valed ained) | 3 | 50% |
| Samm 3 – LLM vastuse genereerimine (hallutsinatsioon / vale vastus) | 1 | 17% |
| **Kokku** | **6** | **100%** |

---

## Kõik testjuhtumid detailidega

| # | Aeg | Kasutaja päring | Filtrid | Filtreeritud kursusi | Leitud ained (Top-5) | Tulemus | Vea vahesamm |
|---|-----|----------------|---------|:--------------------:|----------------------|:-------:|--------------|
| 1 | 17:46 | Leia mulle arvutiteaduse kursuseid | linn=Narva, aste=doktori, eeldusaineteta=True | 1 | Suhtluspõhine keeleõpe: keelesõbrakursus | 👎 | Samm 1 |
| 2 | 17:49 | Leia mulle keemia praktikume | semester=kevad, EAP=3.0, linn=Viljandi, aste=doktori | 0 | – | 👎 | Samm 1 |
| 3 | 17:51 | Ained mis aitavad ettevõtet asutada | – | 3156 | Ettevõtlusega alustamine, Ettevõtluse alused, Sissejuhatus tarkvaraettevõtlusse | 👍 | – |
| 4 | 17:53 | Leia mulle midagi loomingulist ja käelist | – | 3156 | Hundid mets ja inimesed: kunsti õpikoda, Selgroogsete zooloogia välipraktikum, Praktiline arheobotaanika | 👎 | Samm 2 |
| 5 | 17:56 | Kursused mis sobivad vahetusõpilasele | semester=kevad | 1570 | Rahvusvaheline õpikogemus, Suhtluspõhine keeleõpe, Keeleõppe tandemkursus | 👎 | Samm 2 |
| 6 | 17:58 | Leia ained kus pole eksamit | hindamisviis=Eristamata | 1343 | Anorgaanilise keemia praktikum I, Koolikeemia praktikum II, Orgaanilise keemia praktikum | 👎 | Samm 2 |
| 7 | 17:59 | Leia kvantarvutus ja kvantmehaanika kursuseid | – | 3156 | Kvantmehaanika, Kvantarvutuse alused, Kvantkrüptograafia | 👍 | – |
| 8 | 18:00 | Machine learning kursused | – | 3156 | Masinõpe ja närvivõrgud, Masinõpe, Projektipõhine sissejuhatus masinõppesse | 👍 | – |
| 9 | 18:02 | Millised neist sobivad algajatele? | – | 3156 | Ukraina keel algajatele, Ettevõtlusega alustamine, Eesti keele intensiivkursus | 👎 | Samm 2 |
| 10 | 18:03 | Mis on nende kursuste maht EAPdes? | – | 3156 | Kosmoseteaduse doktorikursus, Juhtimine, Laborimeditsiin, Magistriseminar | 👎 | Samm 3 |

---

## Halvad juhtumid – detailne analüüs

### Samm 1 vead – metaandmete filtreerimine

#### Päring 1 – "Leia mulle arvutiteaduse kursuseid"
- **Filtrid:** linn=Narva, aste=doktori, eeldusaineteta=True
- **Filtreeritud kursusi:** 1
- **Probleem:** Kolme filtri kombinatsioon jättis alles ainult 1 kursuse ("Suhtluspõhine keeleõpe"), mis ei ole arvutiteadusega kuidagi seotud. LLM käitus õigesti – ta ütles ausalt, et sobivat kursust ei leitud.
- **Lahendus:** Hoiatada kasutajat, kui filtreeritud kursuste arv langeb alla 20. Pakkuda automaatselt filtrite leevendamist.

#### Päring 2 – "Leia mulle keemia praktikume"
- **Filtrid:** semester=kevad, EAP=3.0, linn=Viljandi, aste=doktori
- **Filtreeritud kursusi:** 0
- **Probleem:** Filtrite kombinatsioon andis tühja andmestiku – Viljandis pole doktoriõppe kursuseid, mis vastaksid kevadsemestri ja EAP=3 tingimustele. LLM vastas korrektselt, et tulemused puuduvad.
- **Lahendus:** Sama mis eelmisel – varajane hoiatus tühja andmestiku korral, enne LLM-i päringu saatmist.

---

### Samm 2 vead – RAG vektorotsing

#### Päring 4 – "Leia mulle midagi loomingulist ja käelist"
- **Filtreeritud kursusi:** 3156
- **Leitud ained:** Hundid, mets ja inimesed: kunsti õpikoda; Selgroogsete zooloogia välipraktikum; Praktiline arheobotaanika
- **Probleem:** Sõna "käeline" tõmbas semantiliselt ligi praktikumikursuseid (zooloogia, arheobotaanika), mis on küll "käelised" labori mõttes, aga mitte selles tähenduses mida kasutaja silmas pidas. Abstraktne päring pettis embeddingu mudeli.
- **Lahendus:** Hübriidotsing (semantiline + märksõnapõhine). Võib kaaluda ka LLM-i kasutamist päringu ümberformuleerimiseks enne otsingut (query rewriting).

#### Päring 5 – "Kursused mis sobivad vahetusõpilasele"
- **Filtrid:** semester=kevad
- **Filtreeritud kursusi:** 1570
- **Leitud ained:** Rahvusvaheline õpikogemus, Suhtluspõhine keeleõpe (Narva), Keeleõppe tandemkursus, Inglise keel bioloogia üliõpilastele
- **Probleem:** "Vahetusõpilane" on abstraktne kriteerium, mida metaandmetes ei eksisteeri. RAG seostas selle rahvusvahelisuse ja keeleõppega, aga vahetusüliõpilane vajab tegelikult laiu üldaineid – mitte spetsiifilisi keelekursuseid.
- **Lahendus:** Lisada süsteemiviibasse instruktsioon, mis selgitab LLM-ile vahetusüliõpilase profiili, või paluda kasutajal täpsustada oma erialast tausta.

#### Päring 6 – "Leia ained kus pole eksamit"
- **Filtrid:** hindamisviis=Eristamata
- **Filtreeritud kursusi:** 1343
- **Leitud ained:** Anorgaanilise keemia praktikum I, Koolikeemia praktikum II, Orgaanilise keemia praktikum
- **Probleem:** Filter töötas õigesti (eristamata hindamine = arvestus), aga RAG tõi keemia praktikumid, sest need on andmestikus arvuliselt üliesindatud eristamata hindamisega ainete hulgas. Lisaks hallutsineeris LLM vastuses kursuseid (nt Hundid mets ja inimesed), mida Top-5 seas polnud – seega on see tegelikult **kahe vahesammu viga korraga** (Samm 2 + Samm 3).
- **Lahendus:** Mitmekesistada Top-N tulemusi valdkonniti. LLM-i prompti tugevdada: "Maini ainult kursuseid, mis on täpselt ülaltoodud nimekirjas."

#### Päring 9 – "Millised neist sobivad algajatele?"
- **Eelmine päring:** "Machine learning kursused" (👍 Hea)
- **Filtreeritud kursusi:** 3156
- **Leitud ained:** Ukraina keel algajatele, Ettevõtlusega alustamine, Eesti keele intensiivkursus
- **Probleem:** Kasutaja viitas eelmise päringu tulemustele sõnaga "neist", aga RAG tegi uue otsingu sõna "algajatele" põhjal ilma vestluskontekstita ja leidis täiesti ebaolulised kursused. LLM ignoreeris RAG tulemusi ja hallutsineeris statistika kursused – seega ka siin on **kaks vahesammu vigased korraga**.
- **Lahendus:** Arhitektuuriline muudatus – esimese päringu Top-N tulemused tuleks salvestada sessiooniolekusse ja jätkupäringute korral kasutada sama konteksti uue otsingu asemel.

---

### Samm 3 vead – LLM vastuse genereerimine

#### Päring 10 – "Mis on nende kursuste maht EAPdes?"
- **Eelmine päring:** "Soovita ökoloogia kursuseid" (päring 9 jätk vestluses)
- **Filtreeritud kursusi:** 3156
- **Leitud ained:** Kosmoseteaduse doktorikursus, Juhtimine, Laborimeditsiin, Magistriseminar
- **Probleem:** RAG ei suutnud "nende" viidet lahendada (sama probleem mis päringul 9), tõi täiesti valed kursused. LLM ignoreeris konteksti täielikult ja vastas ökoloogia kursuste EAP mahtudega (Ökoloogia alused õpetajatele – 3.0 EAP jne), mida ei eksisteerinud ei RAG kontekstis ega eelmises vestlusvoorus. Puhas hallutsinatsioon.
- **Lahendus:** Sama arhitektuuriline lahendus mis päringul 9 (sessioonipõhine kontekst). Lisaks range LLM instruktsioon: "Kui kontekstis pole vastust, ütle seda ausalt – ära mõtle andmeid välja."

---

## Peamised järeldused

### 1. Vestluse järjepidevus on suurim probleem
Päringud 9 ja 10 näitasid, et kui kasutaja viitab eelmisele vastusele ("neist", "nende"), kukub kogu pipeline läbi. RAG otsib iga kord nullist ja toob ebaolulised kursused, misjärel LLM hallutsineerib. See on **arhitektuuriline probleem**, mitte üksiku sammu viga.

### 2. RAG on nõrk abstraktsete päringute korral
"Loominguline ja käeline", "vahetusõpilasele sobiv" – need on inimlikult mõistetavad, aga vektorruum ei suuda neid kontekstuaalselt õigesti hinnata. Embedding mudel leiab semantiliselt sarnased sõnad, mitte kasutaja tegeliku vajaduse.

### 3. Filtrid vajavad kasutajalikku kaitset
Mõlemad Samm 1 vead olid välditavad, kui süsteem oleks hoiatanud enne päringu saatmist: "Sinu filtritega leiti ainult N kursust – kas oled kindel?"

---



*Logifail: `tagasiside_log.csv` | Rakendus: `app.py`*