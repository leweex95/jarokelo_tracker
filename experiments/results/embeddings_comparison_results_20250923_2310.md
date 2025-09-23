## 2025-09-23 23:24 - Embedding comparison on 1000 entries

**Sample size:** 1000, **Top-N:** 5

### Corpus info

**Full corpus size:** 10905
**Eval corpus size:** 1000
**Date range:** 2025-03-19 → 2025-09-22

### Embedding comparison results

---

### SZTAKI-HLT/hubert-base-cc (Hungarian-only)

**Average Top-1 Cosine Similarity:** 0.9451
**Average Top-5 Cosine Similarity:** 0.9408
**Average Overall Cosine Similarity:** 0.8943

| Query | TopN Results | TopN Cosine Scores |
|-------|--------------|-------------------|
| kátyú az úton | kátyúk a ház előtti belső parkolóban<br>lekopott zebra<br>törött, elhagyott autó a kavics utca 1 előtt<br>kidőlő villanyrendőr<br>láthatóan magára hagyott autó | 0.9665, 0.9621, 0.9591, 0.9569, 0.9552 |
| pothole in the road | nap vitorla szetesett<br>hiányos fedlap nádor 5-7 az étterem elött<br>elektromos roller a patakban<br>rege hinta leszakadt<br>ez a doboz letört | 0.9287, 0.9284, 0.9280, 0.9275, 0.9273 |
| hibás közvilágítás | hiányos fedlapok<br>beszakadt fedlap<br>láthatóan magára hagyott autó<br>lerakott hűtőszekrény<br>hiányos közutas fedlap | 0.9546, 0.9535, 0.9494, 0.9493, 0.9486 |
| broken streetlight | graffiti<br>nap vitorla szetesett<br>a gőzmozdony 1 es szám alatti ház mögött a one fedlap körül tönkrement a betongallér<br>ez a doboz letört<br>leesett tábla | 0.9439, 0.9377, 0.9374, 0.9353, 0.9343 |
| csőtörés a főutcán | újpalotán a fő téri buszmegálló automatáját összefújták.<br>törött, elhagyott autó a kavics utca 1 előtt<br>felgyújtották a szemetest a buszmegállóban.<br>a templom kertjében kidöntöttek egy kukát.<br>ismeretlen eredetű fedlap beszakadt a járdán. balesetveszélyes. | 0.9618, 0.9613, 0.9607, 0.9594, 0.9586 |
| water pipe burst on the main street | a gőzmozdony 1 es szám alatti ház mögött a one fedlap körül tönkrement a betongallér<br>hiányos fedlap nádor 5-7 az étterem elött<br>tizedes utca és a keleti károly utca a nèbih-től felfelé tele van szeméttel, emberi ürülékkel, és a hozzá használt zsebkendőkkel.<br>frissítés: 2025.07.24. járókelő visszajelzése: „semmivel egyenlő amit csináltak eddig.” ----- viacolort a fák gyökerei felnyomják. gyerekek elesnek görkorcsolyával , rollerrel.<br>a radnóti u 17 előtt a fedlap széle letört. | 0.9149, 0.9074, 0.9062, 0.9050, 0.9042 |

### NYTK/PULI-BERT-Large (Hungarian-only)

**Average Top-1 Cosine Similarity:** 0.7585
**Average Top-5 Cosine Similarity:** 0.7429
**Average Overall Cosine Similarity:** 0.6185

| Query | TopN Results | TopN Cosine Scores |
|-------|--------------|-------------------|
| kátyú az úton | csőtörés közterületen<br>a közvágóhídnál a bp park előtti zebránál van egy kátyú.<br>az erdőalja út végén egy kapu alól ömlik a víz, végig le a kocsis sándor úton<br>tönkrement járda az illatos center gépjármű bejárójában .<br>a dózsa györgy út és szondi utca kereszteződésében lévő zebra előtt van egy kátyú. | 0.8556, 0.8470, 0.8467, 0.8422, 0.8391 |
| pothole in the road | süllyedő csatornafedlap<br>kidőlt poller a gerlóczy utcában a dm-nél.<br>graffiti<br>frissítés: 2025.09.14. a bejelentő válasza: „nem történt semmi, szerintem mehetne egy ki dely reminder” ----- ki van torve a kanyarban par poller igy fel lehet hajtani a jardara. a motorosok rendszeresen itt mennek le.<br>frissítés: 2025.07.24. járókelő visszajelzése: „semmivel egyenlő amit csináltak eddig.” ----- viacolort a fák gyökerei felnyomják. gyerekek elesnek görkorcsolyával , rollerrel. | 0.6164, 0.6099, 0.6068, 0.6038, 0.6002 |
| hibás közvilágítás | csőtörés közterületen<br>kidőlő villanyrendőr<br>szemét a zöld területen.<br>rongálás, gyűlöletkeltő szövegek<br>hiányos közutas fedlap | 0.8547, 0.8414, 0.8215, 0.8211, 0.8209 |
| broken streetlight | graffiti<br>döglött galamb<br>kidőlt poller a gerlóczy utcában a dm-nél.<br>szétdobált szemét<br>rendszeresen van itt ilyen hulladék | 0.7111, 0.6892, 0.6628, 0.6600, 0.6511 |
| csőtörés a főutcán | tönkrement járda az illatos center gépjármű bejárójában .<br>csőtörés közterületen<br>elhagyott rendszamnelkuli taxi az erdo szelen<br>törött, elhagyott autó a kavics utca 1 előtt<br>otthagyott auto | 0.8594, 0.8578, 0.8490, 0.8448, 0.8409 |
| water pipe burst on the main street | kidőlt poller a gerlóczy utcában a dm-nél.<br>tönkrement járda az illatos center gépjármű bejárójában .<br>frissítés: 2025.07.24. járókelő visszajelzése: „semmivel egyenlő amit csináltak eddig.” ----- viacolort a fák gyökerei felnyomják. gyerekek elesnek görkorcsolyával , rollerrel.<br>frissítés: 2025.09.14. a bejelentő válasza: „nem történt semmi, szerintem mehetne egy ki dely reminder” ----- ki van torve a kanyarban par poller igy fel lehet hajtani a jardara. a motorosok rendszeresen itt mennek le.<br>frissítés: 2025.04.08. trafficom válasza: „a jelzett műtárgy nem a trafficom kft. tulajdona, ill. nem tartozik cégünk üzemeltetése alá.” ----- tönkrement fedlap a millenniumtelepi hév megállóban a haraszti út 157 szemben. | 0.6540, 0.6538, 0.6491, 0.6445, 0.6336 |
