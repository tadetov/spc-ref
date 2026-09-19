# Report ETL – 2026-09-18T19:10:16

Platnost DLP: {'PLATNOST_OD': '01.09.2026', 'PLATNOST_DO': '30.09.2026'}  
Zip: DLP20260827.zip / SPC20260827.zip

## Výběr

- přípravků v DLP celkem: 69759
- filtry: ['REG == R', 'bez PZLÚ (-0)', "kódy: ['0003925', '0096414', '0096416', '0115401', '0178634', '0216533', '0254306']"]
- přípravků po filtru: 7
- z toho s lokálním SPC souborem: 7 dokumentů
- z toho **s odkazem na EMA (centralizovaná registrace, SPC NENÍ v SÚKL zipu)**: 0 přípravků / 0 odkazů
- bez jakéhokoli SPC: 0 přípravků
- zpracováno dokumentů: 7

## Rozložení v celém DLP (před filtrem)

**rozlozeni_reg**
- R – registrovaný léčivý přípravek: 61129
- B – přípravek po provedené změně může být uváděn na trh po dobu 6 měsíců a používán do uplynutí doby použitelnosti, nejdéle po dobu platnosti registrace: 6973
- P – potravina pro zvláštní lékařské účely: 1434
- F – specifický léčebný program povolený MZČR na základě doporučení SÚKL: 178
- M – pozastavení registrace nebo používání léčivého přípravku  a jeho uvádění do oběhu: 27
- I – léčivý přípravek povolený na základě mimořádného opatření MZ: 13
- C – zrušená registrace, přípravek bude stažen z oběhu do doby uvedené v rozhodnutí o zrušení registrace: 4
- K – pozastavení rozhodnutí o centralizované registraci: 1

**rozlozeni_typ_lp**
- CH – Chemické léčivé přípravky: 61394
- BT – Biotechnologické léčivé přípravky: 2763
-  – : 1992
- HO – Homeopatické léčivé přípravky: 833
- BI – Biologické léčivé přípravky - ostatní: 575
- RA – Radiofarmaka: 562
- IM – Imunologické léčivé přípravky: 477
- HE – Rostlinné léčivé přípravky: 275
- IM/BT – Imunologické léčivé přípravky/Biotechnologické léčivé přípravky: 261
- TR – Tradiční rostlinné léčivé přípravky: 203
- KR/B – Krevní derivát-immunoglobulin (iv/im/sc): 191
- KR/F – Krevní derivát-koagulační faktor: 45
- AD/GM – ATMP - Genová terapie obsahující GMO: 44
- KR/A – Krevní derivát-albumin: 34
- KR/L – Krevní derivát-fibrinové lepidlo: 24
- KR/O – Krevní derivát-ostatní: 21
- KR/I – Krevní derivát-koagulační inhibitor: 18
- IM/CH – Imunologické léčivé přípravky/Chemické léčivé přípravky: 18
- AD/GCM – ATMP - Genová terapie (s buňkami/tkáněmi) obsahující GMO: 12
- IM/M/BT – Imunologické léčivé přípravky obsahující GMO/Biotechnologické léčivé přípravky: 11
- AD/T – ATMP - Tkáňové inženýrství: 3
- AD/S – ATMP - Somato-buněčná terapie: 2
- IM/M – Imunologické léčivé přípravky obsahující GMO: 1

**rozlozeni_odkaz_spc**
- soubor: 47179
- url_ema: 13331
- chybi: 9249

Příznaky složení v číselníku: {'A': 'AD ... DOPLNĚNO DO:', 'C': 'Pomocná látka, která odpovídá jiné pomocné látce', 'D': 'Adjuvant', 'L': 'Léčivá látka', 'O': 'Účinná látka, která odpovídá jiné účinné látce', 'R': 'Rozpouštědlo', 'S': 'SUBTOTAL', 'T': 'TOTAL', 'X': '1) pomocná látka, \n2) oddělovací řádek, pokud není uveden název látky', 'Z': 'pomocný údaj; \n1) pro léčivou látku znamená, že následuje léčivá látka odpovídající látce uvedené na řádku před corresponding to:, \n2) pro pomocnou látku znamená, že následuje pomocná látka (viz označení C) odpovídající pomocné látce uvedené na řádku před corresponding to:,\n3) OR v názvu látky znamená, že v léčivém přípravku je buď látka uvedená nad nebo pod řádkem s označením OR'}  
Jako *léčivá látka* použity příznaky: ['L', 'O']

## Parsování

- formáty: {'pdf': 6, 'doc': 1}
- stav dokumentů: {'ok': 7}
- sken / bez textu: 0
- sekce vytaženy: {'2': 7, '4.1': 7, '4.2': 7, '4.3': 7, '4.4': 7, '4.5': 7, '4.6': 7}
- sekce chybí: {}
- selhání: {}
- EMA/EC: odkazů 0, PDF nalezeno 0, chybí 0, SPC bloků 0, stav {}, sekce chybí {}
- dokumentů s výrazem dávky /kg nebo /m²: 6
- dokumentů s podnadpisy v 4.2: {'pediatrie': 6, 'ledviny': 6, 'seniori': 4, 'jatra': 5}
- skupin ATC (primární jednotka): 7
- průměr znaků vybraných sekcí / dokument: 13988
- unikátní texty sekcí (unikátní/celkem): {'2': '7/7', '4.1': '7/7', '4.2': '7/7', '4.3': '7/7', '4.4': '7/7', '4.5': '7/7', '4.6': '7/7'}
- výstupní JSON: 0.15 MB (gzip 0.04 MB), čas 1 s

## Dokumenty s chybějícími sekcemi


## Náhled vytažených sekcí (prvních 300 znaků)

### SPC205707.pdf [pdf] – CLEXANE

1. NÁZEV PŘÍPRAVKU: CLEXANE 2 000 IU (20 mg)/0,2 ml injekční roztok v předplněné injekční stříkačce | CLEXANE 4 000 IU (40 mg)/0,4 ml injekční roztok v předplněné injekční stříkačce | CLEXANE 6 000 IU (60 mg)/0,6 ml injekční roztok v předplněné injekční stříkačce | CLEXANE 8 000 IU (80 mg)/0,8 ml injekční roztok v před  
sp. zn.: sukls258650/2023

**2 Kvalitativní a kvantitativní složení** (1001 zn.)  
> 2 000 IU (20 mg) /0,2 ml Jedna předplněná injekční stříkačka obsahuje enoxaparinum natricum 2 000 IU anti-Xa aktivity (odpovídá 20 mg) v 0,2 ml vody na injekci. 4 000 IU (40 mg) /0,4 ml Jedna předplněná injekční stříkačka obsahuje enoxaparinum natricum 4 000 IU anti-Xa aktivity (to odpovídá 40 mg) v

**4.1 Terapeutické indikace** (1266 zn.)  
> Přípravek CLEXANE (a související názvy) je indikován u dospělých: • Profylaxe venózní tromboembolické nemoci v chirurgii u pacientů se středním nebo vysokým rizikem, zejména v ortopedické nebo všeobecné chirurgii, včetně chirurgie nádorových onemocnění. • Profylaxe venózní tromboembolické nemoci u i

**4.2 Dávkování a způsob podání** (16952 zn.)  
> Dávkování  Profylaxe venózní tromboembolické choroby v chirurgii u pacientů se středním a vysokým rizikem Individuální riziko tromboembolie pro pacienty je možné odhadnout pomocí validovaného modelu stratifikace rizika. • U pacientů se středním rizikem tromboembolismu je doporučená dávka 2 000 IU (2

**4.3 Kontraindikace** (1014 zn.)  
> Sodná sůl enoxaparinu je kontraindikována u pacientů s: • hypersenzitivitou na sodnou sůl enoxaparinu nebo jeho deriváty včetně ostatních nízkomolekulárních heparinů (LMWH) nebo na kteroukoli pomocnou látku uvedenou v bodě 6.1; • anamnézou heparinem indukované trombocytopenie (HIT) zprostředkované i

**4.4 Zvláštní upozornění a opatření pro použití** (11849 zn.)  
> • Obecně: Nízkomolekulární hepariny (LMWH) nelze volně zaměňovat (jednotku za jednotku) se sodnou solí enoxaparinu. Tyto léky se liší svým výrobním postupem, molekulární hmotností, specifickou anti-Xa aktivitou a anti-IIa aktivitou, jednotkami, dávkováním a klinickou účinností a bezpečností. Následk

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (1286 zn.)  
> Nedoporučované lékové kombinace • Léky ovlivňující hemostázu (viz bod 4.4) Před začátkem terapie sodnou solí enoxaparinu se doporučuje přerušit léčbu některými léky ovlivňujícími hemostázu, pokud nejsou striktně indikované. Pokud je kombinované použití indikované, je nezbytné při používání sodné sol

**4.6 Fertilita, těhotenství a kojení** (1512 zn.)  
> Těhotenství U lidí nejsou důkazy o průchodu sodné soli enoxaparinu placentární barierou v druhém a třetím trimestru těhotenství. O prvním trimestru nejsou k dispozici žádné informace. Studie na zvířatech neprokázaly známky fetotoxicity a teratogenity (viz bod 5.3). Zároveň také ukázaly, že přechod s

podnadpisy 4.2: ['pediatrie', 'ledviny', 'jatra', 'seniori']  
- dávka `150 IU/kg` ← „Léčba hluboké žilní trombózy (DVT) a plicní embolie (PE) Sodná sůl enoxaparinu se může podávat s.c. injekcí buď jednou denně 150 IU/kg (1,5 mg/kg) nebo dvakrát “
- dávka `1,5 mg/kg` ← „Léčba hluboké žilní trombózy (DVT) a plicní embolie (PE) Sodná sůl enoxaparinu se může podávat s.c. injekcí buď jednou denně 150 IU/kg (1,5 mg/kg) nebo dvakrát “
- dávka `100 IU/kg` ← „Léčba hluboké žilní trombózy (DVT) a plicní embolie (PE) Sodná sůl enoxaparinu se může podávat s.c. injekcí buď jednou denně 150 IU/kg (1,5 mg/kg) nebo dvakrát “
- dávka `1mg/kg` ← „Léčba hluboké žilní trombózy (DVT) a plicní embolie (PE) Sodná sůl enoxaparinu se může podávat s.c. injekcí buď jednou denně 150 IU/kg (1,5 mg/kg) nebo dvakrát “
- dávka `150 IU/kg` ← „Dávkovací režim 150 IU/kg (1,5 mg/kg) jednou denně se má použít u nekomplikovaných pacientů s nízkým rizikem rekurence VTE“
- dávka `1,5 mg/kg` ← „Dávkovací režim 150 IU/kg (1,5 mg/kg) jednou denně se má použít u nekomplikovaných pacientů s nízkým rizikem rekurence VTE“
- dávka `100 IU/kg` ← „U všech ostatních pacientů, jako jsou pacienti s obezitou, symptomatickou PE, onkologickým onemocněním, rekurentní VTE nebo proximální trombózou (vena iliaca) s“
- dávka `1 mg/kg` ← „U všech ostatních pacientů, jako jsou pacienti s obezitou, symptomatickou PE, onkologickým onemocněním, rekurentní VTE nebo proximální trombózou (vena iliaca) s“

### SPC209840.pdf [pdf] – GENTAMICIN LEK

1. NÁZEV PŘÍPRAVKU: Gentamicin Lek 80 mg/2 ml injekční/infuzní roztok  
sp. zn.: sukls69414/2024

**2 Kvalitativní a kvantitativní složení** (311 zn.)  
> Jedna ampulka se 2 ml injekčního roztoku obsahuje 80 mg gentamicinu (ve formě gentamicin- sulfátu).  Pomocné látky se známým účinkem: Tento přípravek obsahuje 16 mg propylenglykolu, 1,6 mg methylparabenu, 0,2 mg propylparabenu, 1,6 mg disiřičitanu sodného v 1 ampulce.  Úplný seznam pomocných látek v

**4.1 Terapeutické indikace** (1237 zn.)  
> Gentamicin Lek je indikován k léčbě vážných systémových infekcí vyvolaných aerobními gramnegativními mikroorganismy, citlivými na gentamicin, jako jsou např. tyto infekce: • sepse • závažné opakované infekce močových cest • infekce dolních dýchacích cest • infekce centrálního nervového systému (včet

**4.2 Dávkování a způsob podání** (3861 zn.)  
> Dávkování  Gentamicin Lek se může podávat intramuskulárně, intravenózně nebo intratekálně. Dávkování, cesta podání a interval mezi jednotlivými dávkami závisí na typu a závažnosti infekce, na citlivosti mikroorganismu a na stavu pacienta (na věku, na funkci ledvin). Podání v jediné denní dávce má si

**4.3 Kontraindikace** (128 zn.)  
> - Hypersenzitivita na léčivou látku nebo na kteroukoli pomocnou látku uvedenou v bodě 6.1. - Hypersenzitivita na aminoglykosidy.

**4.4 Zvláštní upozornění a opatření pro použití** (3553 zn.)  
> U pacientů s pokročilou poruchou funkce ledvin nebo s preexistující hluchotou nitroušního původu má být gentamicin použit pouze ve vitální indikaci.  Jelikož má gentamicin vlastnosti neuromuskulárního blokátoru, zvláštní pozornost má být věnována pacientům s existujícími neuromuskulárními poruchami 

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (1574 zn.)  
> Antibiotika Kombinovaná léčba vhodnými antibiotiky (např. beta-laktamová antibiotika) může vést k synergickému účinku.  Synergické účinky byly popsány s acylaminopeniciliny na Pseudomonas aeruginosa, s ampicilinem na Enterococci a s cefalosporiny na Klebsiella pneumoniae.  Potenciálně nefrotoxické a

**4.6 Fertilita, těhotenství a kojení** (734 zn.)  
> Těhotenství Údaje o podávání gentamicinu těhotným ženám nejsou k dispozici. Studie na zvířatech prokázaly reprodukční toxicitu gentamicinu (viz bod 5.3). Gentamicin prostupuje placentou a existuje potenciální riziko poškození vnitřního ucha a ledvin plodu. Proto má být gentamicin používán během těho

podnadpisy 4.2: ['pediatrie', 'ledviny', 'seniori']  
- dávka `3-6 mg/kg tělesné hmotnosti` ← „Dospělí, děti (2 – 11 let) a dospívající (12 – 16 let) Doporučená denní dávka u dětí, dospívajících a dospělých s normální funkcí ledvin je 3-6 mg/kg tělesné hm“
- dávka `4,5-7,5 mg/kg tělesné hmotnosti` ← „Kojenci a batolata (28 dní a 23 měsíců) Doporučená denní dávka u dětí od 1 měsíce života je 4,5-7,5 mg/kg tělesné hmotnosti denně, podaná v jedné (upřednostňová“
- dávka `4-7 mg/kg tělesné hmotnosti` ← „Novorozenci (0 – 27 dní) Doporučená denní dávka u novorozenců je 4-7 mg/kg tělesné hmotnosti denně“
- dávka `7,5 mg/kg` ← „Maximální denní dávka gentamicinu je 7,5 mg/kg, podaná rozděleně ve třech jednotlivých dávkách“

### SPC222524.pdf [pdf] – PARACETAMOL B. BRAUN

1. NÁZEV PŘÍPRAVKU: Paracetamol B. Braun 10 mg/ml infuzní roztok  
sp. zn.: sukls28717/2025

**2 Kvalitativní a kvantitativní složení** (279 zn.)  
> Jeden ml infuzního roztoku obsahuje 10 mg paracetamolu. Jedna ampulka o objemu 10 ml obsahuje 100 mg paracetamolu. Jedna lahvička o objemu 50 ml obsahuje 500 mg paracetamolu. Jedna lahvička o objemu 100 ml obsahuje 1000 mg paracetamolu.  Úplný seznam pomocných látek viz bod 6.1.

**4.1 Terapeutické indikace** (282 zn.)  
> Paracetamol B. Braun je indikován:  ● ke krátkodobé léčbě středně silné bolesti, zejména po operaci, ● ke krátkodobé léčbě horečky, pokud je podání intravenózní cestou klinicky odůvodněné urgentní potřebou léčby bolesti nebo hypertermie a/nebo když jiné způsoby podání nejsou možné.

**4.2 Dávkování a způsob podání** (5161 zn.)  
> Lahvička o objemu 100 ml je určena výhradně dospělým, dospívajícím a dětem o tělesné hmotnosti vyšší než 33 kg.  Lahvička o objemu 50 ml je určena výhradně batolatům a dětem o tělesné hmotnosti vyšší než 10 kg a nižší než 33 kg.  Ampulka o objemu 10 ml je určena výhradně donošeným novorozencům, koje

**4.3 Kontraindikace** (188 zn.)  
> ● Hypersenzitivita na paracetamol, propacetamol-hydrochlorid (prekurzor paracetamolu) nebo na kteroukoli pomocnou látku uvedenou v bodě 6.1. ● Případy závažné hepatocelulární insuficience.

**4.4 Zvláštní upozornění a opatření pro použití** (2222 zn.)  
> RIZIKO CHYB V MEDIKACI Dbejte na to, aby se zabránilo chybám při výpočtech požadované dávky v důsledku záměny miligramů (mg) a mililitrů (ml), což by mohlo vést k náhodnému předávkování a k úmrtí (viz bod 4.2).  Dlouhodobé nebo časté používání se nedoporučuje. Doporučuje se použít vhodnou perorální 

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (934 zn.)  
> ● Probenecid způsobuje téměř dvojnásobné snížení clearance paracetamolu inhibicí jeho konjugace s kyselinou glukuronovou. Pokud se má paracetamol užívat současně s probenecidem, je třeba zvážit snížení dávky paracetamolu. ● Salicylamid může prodloužit poločas eliminace paracetamolu.  ● Opatrnosti je

**4.6 Fertilita, těhotenství a kojení** (640 zn.)  
> Těhotenství: Velké množství dat u těhotných žen neukazuje na malformační, ani na feto/neonatální toxicitu. Výsledky epidemiologických studií neurologického vývoje u dětí, které byly in utero vystaveny paracetamolu, nejsou průkazné.  Pokud je to z klinického hlediska zapotřebí, může být paracetamol v

podnadpisy 4.2: ['pediatrie', 'ledviny', 'jatra']  
- dávka `7,5 mg/kg` ← „Braun (10 mg/ml) podle horní hranice tělesné hmotnosti*** Maximální denní dávka ** ≤ 10 kg * 7,5 mg/kg 0,75 ml/kg 7,5 ml 30 mg/kg“
- dávka `0,75 ml/kg` ← „Braun (10 mg/ml) podle horní hranice tělesné hmotnosti*** Maximální denní dávka ** ≤ 10 kg * 7,5 mg/kg 0,75 ml/kg 7,5 ml 30 mg/kg“
- dávka `30 mg/kg` ← „Braun (10 mg/ml) podle horní hranice tělesné hmotnosti*** Maximální denní dávka ** ≤ 10 kg * 7,5 mg/kg 0,75 ml/kg 7,5 ml 30 mg/kg“
- dávka `15 mg/kg` ← „> 10 kg až ≤ 33 kg 15 mg/kg 1,5 ml/kg 49,5 ml 60 mg/kg nepřekročit 2 g“
- dávka `1,5 ml/kg` ← „> 10 kg až ≤ 33 kg 15 mg/kg 1,5 ml/kg 49,5 ml 60 mg/kg nepřekročit 2 g“
- dávka `60 mg/kg` ← „> 10 kg až ≤ 33 kg 15 mg/kg 1,5 ml/kg 49,5 ml 60 mg/kg nepřekročit 2 g“
- dávka `15 mg/kg` ← „> 33 kg až ≤ 50 kg 15 mg/kg 1,5 ml/kg 75 ml 60 mg/kg nepřekročit 3 g“
- dávka `1,5 ml/kg` ← „> 33 kg až ≤ 50 kg 15 mg/kg 1,5 ml/kg 75 ml 60 mg/kg nepřekročit 3 g“

### SPC226792.pdf [pdf] – IBALGIN BABY

1. NÁZEV PŘÍPRAVKU: Ibalgin Baby 20 mg/ml perorální suspenze  
sp. zn.: sukls6922/2025

**2 Kvalitativní a kvantitativní složení** (218 zn.)  
> Jeden ml suspenze obsahuje ibuprofenum 20 mg. Pomocné látky se známým účinkem: Jeden ml perorální suspenze obsahuje 2,5 mg natrium-benzoátu (E 211) a 300 mg sorbitolu (E 420).  Úplný seznam pomocných látek viz bod 6.1.

**4.1 Terapeutické indikace** (651 zn.)  
> Přípravek Ibalgin Baby je určen k léčbě: • horečky, zejména při akutních bakteriálních a virových infekcích, včetně postvakcinační horečky; • mírné až středně silné bolesti, jako je např. bolest zubů, hlavy (včetně migrény vaskulární etiologie), zad, bolest svalů nebo kloubů nezánětlivé etiologie, b

**4.2 Dávkování a způsob podání** (2559 zn.)  
> Výskyt nežádoucích účinků lze minimalizovat podáváním nejnižší účinné dávky po nejkratší dobu nutnou k potlačení příznaků onemocnění (viz bod 4.4).  Při léčbě horečky a bolesti nerevmatického původu se používá jednotlivá dávka 5-10 mg ibuprofenu/kg tělesné hmotnosti, denní dávka by neměla překročit 

**4.3 Kontraindikace** (581 zn.)  
> • Hypersenzitivita na léčivou látku nebo na kteroukoli pomocnou látku uvedenou v bodě 6.1. • Hypersenzitivita na kyselinu acetylsalicylovou a jiná nesteroidní antirevmatika projevující se jako astma, urtikárie a jiné alergické reakce. • Anamnesticky gastrointestinální krvácení nebo perforace ve vzta

**4.4 Zvláštní upozornění a opatření pro použití** (7550 zn.)  
> Ibalgin Baby by neměl být podáván společně s jinými nesteroidními antirevmatiky včetně selektivních inhibitorů cyklooxygenázy 2. Výskyt nežádoucích účinků může být snížen podáváním nejnižší účinné dávky po nejkratší dobu nutnou ke zlepšení příznaků.  Starší pacienti U starších pacientů je zvýšený vý

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (1536 zn.)  
> Při současném podávání ibuprofenu (zvláště ve vysokých dávkách) s antikoagulancii, např. s warfarinem, dochází k prodloužení protrombinového času a zvýšenému riziku krvácení.  Kyselina acetylsalicylová Současné podávání ibuprofenu a kyseliny acetylsalicylové se obecně nedoporučuje vzhledem k možnost

**4.6 Fertilita, těhotenství a kojení** (2945 zn.)  
> Přípravek je určen dětem. Informace níže jsou uvedeny pro případ, že by přípravek užívaly těhotné nebo kojící ženy.  Těhotenství Inhibice syntézy prostaglandinů může nepříznivě ovlivňovat těhotenství a/nebo vývoj embrya či plodu. Údaje z epidemiologických studií poukazují na zvýšené riziko potratu, 

podnadpisy 4.2: ['ledviny', 'jatra']  
- dávka `5-10 mg ibuprofenu/kg tělesné hmotnosti` ← „Při léčbě horečky a bolesti nerevmatického původu se používá jednotlivá dávka 5-10 mg ibuprofenu/kg tělesné hmotnosti, denní dávka by neměla překročit 40 mg ibu“
- dávka `40 mg ibuprofenu/kg tělesné hmotnosti` ← „Při léčbě horečky a bolesti nerevmatického původu se používá jednotlivá dávka 5-10 mg ibuprofenu/kg tělesné hmotnosti, denní dávka by neměla překročit 40 mg ibu“
- dávka `30-40 mg/kg tělesné hmotnosti /den` ← „Při léčbě juvenilní idiopatické artritidy je obvyklá dávka 30-40 mg/kg tělesné hmotnosti /den, podaná ve 3-4 dílčích dávkách“
- dávka `50 mg/kg tělesné hmotnosti` ← „Maximální dávka 50 mg/kg tělesné hmotnosti se nesmí překročit“
- dávka `20-35 mg/kg tělesné hmotnosti` ← „U ostatních indikací je denní dávka u dětí do 12 let věku 20-35 mg/kg tělesné hmotnosti podaná rozděleně ve 3-4 dílčích dávkách“
- dávka `20 mg/kg/den` ← „Orientační příklad dávkování podle hmotnosti dítěte (v tabulce jsou vypočítány denní dávky s použitím spodní hranice doporučeného množství ibuprofenu 20 mg/kg/d“

### SPC227574.pdf [pdf] – AMOKSIKLAV

1. NÁZEV PŘÍPRAVKU: Amoksiklav 312,5 mg/5 ml prášek pro perorální suspenzi  
sp. zn.: sukls214820/2025

**2 Kvalitativní a kvantitativní složení** (591 zn.)  
> Jeden ml perorální suspenze po rekonstituci obsahuje 50 mg amoxicilinu ve formě trihydrátu amoxicilinu a 12,5 mg kyseliny klavulanové ve formě kalium-klavulanátu.  Pět ml perorální suspenze (1 odměrka) obsahuje 250 mg amoxicilinu (ve formě trihydrátu amoxicilinu) a 62,5 mg kyseliny klavulanové (ve f

**4.1 Terapeutické indikace** (613 zn.)  
> Přípravek Amoksiklav je indikován k léčbě následujících infekcí u dospělých, dospívajících a dětí (viz body 4.2, 4.4 a 5.1):  - akutní bakteriální sinusitida (odpovídajícím způsobem diagnostikovaná) - akutní otitis media - akutní exacerbace chronické bronchitidy (odpovídajícím způsobem diagnostikova

**4.2 Dávkování a způsob podání** (3513 zn.)  
> Dávkování Dávky jsou v textu vyjádřeny jako obsah amoxicilinu/kyseliny klavulanové, pokud nejsou vyjádřeny pro jednotlivé složky.  Při stanovování dávky přípravku Amoksiklav, která se volí k léčbě individuální infekce, je nutno vzít v potaz: ● předpokládané patogeny a jejich pravděpodobnou citlivost

**4.3 Kontraindikace** (395 zn.)  
> - Hypersenzitivita na léčivé látky nebo na kteroukoli pomocnou látku uvedenou v bodě 6.1, nebo kterýkoli z penicilinů.  - Těžká bezprostřední hypersenzitivní reakce (např. anafylaxe) na jiná beta-laktamová antibiotika (např. cefalosporin, karbapenem nebo monobaktam) v anamnéze.  - Žloutenka/zhoršení

**4.4 Zvláštní upozornění a opatření pro použití** (6731 zn.)  
> Před zahájením léčby kombinací amoxicilin/kyselina klavulanová je nutno se pečlivě dotázat na předchozí hypersenzitivní reakce na peniciliny, cefalosporiny nebo další beta-laktamová antibiotika (viz body 4.3 a 4.8).  U pacientů léčených peniciliny byly hlášeny závažné a ojediněle fatální hypersenzit

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (1504 zn.)  
> Perorální antikoagulancia  Perorální antikoagulancia a penicilinová antibiotika se v praxi široce používají bez hlášených interakcí. V literatuře se však vyskytují případy zvýšeného mezinárodního normalizovaného poměru (INR) u pacientů léčených acenokumarolem nebo warfarinem, kterým je předepsána kú

**4.6 Fertilita, těhotenství a kojení** (999 zn.)  
> Těhotenství Studie na zvířatech neukazují na přímé či nepřímé škodlivé účinky, pokud jde o březost, embryonální/fetální vývoj, porod nebo postnatální vývoj (viz bod 5.3). Omezené údaje o používání kombinace amoxicilin/kyselina klavulanová během těhotenství u lidí na zvýšené riziko vrozených malforma

podnadpisy 4.2: ['pediatrie', 'ledviny', 'jatra', 'seniori']  
- dávka `20 mg/5 mg až 60 mg/15 mg na kg` ← „Děti < 40 kg Dávka 20 mg/5 mg až 60 mg/15 mg na kg denně podávaná ve třech dílčích dávkách“
- dávka `40 mg/10 mg/kg/den` ← „U pacientů do 2 let věku neexistují žádné klinické údaje pro podávání formulací přípravku Amoksiklav v poměru 4:1 v dávkách vyšších než 40 mg/10 mg/kg/den“
- dávka `15 mg/3,75 mg/kg` ← „Děti < 40 kg CrCl: 10-30 ml/min: 15 mg/3,75 mg/kg dvakrát denně (maximum 500 mg/125 mg dvakrát denně)“
- dávka `15 mg/3,75 mg/kg` ← „CrCl < 10 ml/min: 15 mg/3,75 mg/kg jako jediná denní dávka (maximum 500 mg/125 mg)“
- dávka `15 mg/3,75 mg/kg/den` ← „Hemodialýza: 15 mg/3,75 mg/kg/den jednou denně“
- dávka `15 mg/3,75 mg/kg` ← „Před hemodialýzou 15 mg/3,75 mg/kg“
- dávka `15 mg/3,75 mg/kg` ← „Za účelem obnovení hladin léčivých látek v oběhu by mělo být po ukončení hemodialýzy podáno 15 mg/3,75 mg/kg“

### SPC307108.doc [doc] – ZENARO

1. NÁZEV PŘÍPRAVKU: Zenaro 5 mg potahované tablety  
sp. zn.: sukls67180/2022

**2 Kvalitativní a kvantitativní složení** (227 zn.)  
> Jedna potahovaná tableta obsahuje levocetirizini dihydrochloridum 5 mg.  Pomocné látky se známým účinkem: jedna tableta obsahuje 67,5 mg monohydrátu laktosy a maximálně 0,04 mg sodíku.  Úplný seznam pomocných látek viz bod 6.1.

**4.1 Terapeutické indikace** (151 zn.)  
> Symptomatická léčba alergické rinitidy (včetně perzistující alergické rinitidy) a urtikarie u dospělých, dospívajících a dětí od 6 let věku a starších.

**4.2 Dávkování a způsob podání** (2689 zn.)  
> Dávkování Dospělí a dospívající od 12 let věku Doporučená denní dávka je 5 mg (1 potahovaná tableta).  Starší pacienti U starších pacientů se středně závažnou až závažnou poruchou funkce ledvin se doporučuje úprava dávky (viz níže Porucha funkce ledvin).  Porucha funkce ledvin Intervaly podávání se 

**4.3 Kontraindikace** (235 zn.)  
> • Hypersenzitivita na léčivou látku, na cetirizin, hydroxyzin a jiné piperazinové deriváty nebo na kteroukoli pomocnou látku uvedenou v bodě 6.1. • Pacienti se závažnou poruchou funkce ledvin s clearance kreatininu nižší než 10 ml/min.

**4.4 Zvláštní upozornění a opatření pro použití** (1404 zn.)  
> Při současném požívání alkoholu je doporučena opatrnost (viz bod 4.5).  Pozornost je třeba věnovat pacientům s predispozičními faktory retence moči (např. míšní léze, hyperplazie prostaty), protože levocetirizin může zvyšovat riziko retence moči.  U pacientů s epilepsií nebo s rizikem výskytu křečí 

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (992 zn.)  
> Interakční studie (včetně studie s induktory CYP 3A4) s levocetirizinem nebyly provedeny. Studie s racemátem (cetirizinem) prokázaly, že se nevyskytují žádné klinicky významné nežádoucí interakce (s antipyrinem, azitromycinem, cimetidinem, diazepamem, erythromycinem, glypizidem, ketokonazolem a pseu

**4.6 Fertilita, těhotenství a kojení** (1073 zn.)  
> Těhotenství Nejsou k dispozici žádné klinické údaje nebo je jen omezené množství údajů (výsledky u méně než 300 těhotenství) o podávání levocetirizinu těhotným ženám. Avšak u cetirizinu, racemátu levocetirizinu, velké množství dat (více než 1 000 těhotenství) získaných u těhotných žen nenaznačuje vý

podnadpisy 4.2: ['pediatrie', 'ledviny', 'jatra', 'seniori']  

### SPC74427.pdf [pdf] – AMINOVEN 5%

sp. zn.: sukls78532/2011

**2 Kvalitativní a kvantitativní složení** (534 zn.)  
> 1000 ml infuzního roztoku obsahuje: Isoleucinum 2,50 g Leucinum 3,70 g Lysini acetas 4,655 g =Lysinum 3,30 g Methioninum 2,15 g Phenylalaninum 2,55 g Threoninum 2,20 g Tryptophanum 1,00 g Valinum 3,10 g Argininum 6,00 g Histidinum 1,50 g Alaninum 7,00 g Glycinum 5,50 g Prolinum 5,60 g Serinum 3,25 g

**4.1 Terapeutické indikace** (169 zn.)  
> Doplnění aminokyselin jako součást celkové parenterální výživy.  Roztoky aminokyselin by se měly obecně podávat v kombinaci s adekvátním množstvím energetických doplňků.

**4.2 Dávkování a způsob podání** (1929 zn.)  
> Dávkování Denní požadavky na aminokyseliny závisí na tělesné hmotnosti a na metabolickém stavu pacienta. Maximální denní dávka se liší v závislosti na klinickém stavu pacienta a může se dokonce změnit ze dne na den. Doporučuje se podávat infuzi formou kontinuální infuze po dobu alespoň 14 hodin až m

**4.3 Kontraindikace** (395 zn.)  
> Podání přípravku Aminoven 5% je kontraindikováno u dětí mladších dvou let. Stejně jako jiné roztoky aminokyselin je i přípravek Aminoven 5% kontraindikován v následujících případech: Porucha metabolizmu aminokyselin, metabolická acidóza, renální insuficience bez léčby hemodialýzou nebo hemofiltrací,

**4.4 Zvláštní upozornění a opatření pro použití** (1287 zn.)  
> Měla by být sledována hladina elektrolytů v séru, bilance tekutin a funkce ledvin.  V případě hypokalémie a/nebo hyponatrémie by se mělo současně doplnit odpovídající množství kalia a/nebo natria.  Roztoky aminokyselin mohou urychlit akutní deficit folátů. Z toho důvodu se má denně podávat kyselina 

**4.5 Interakce s jinými léčivými přípravky a jiné formy interakce** (80 zn.)  
> Doposud nejsou známy žádné interakce. Informace o inkompatibilitách viz bod 6.2.

**4.6 Fertilita, těhotenství a kojení** (385 zn.)  
> Nebyly provedeny žádné specifické studie hodnotící bezpečnost přípravku Aminoven 5% na fertilitu, těhotenství a kojení. Klinické zkušenosti s podobnými parenterálními roztoky aminokyselin však neukázaly žádné riziko při jejich použití během těhotenství nebo kojení. Před podáním přípravku Aminoven 5%

podnadpisy 4.2: ['pediatrie']  
- dávka `16,0 – 20,0 ml přípravku Aminoven 5%/kg těl. hm./den` ← „Dávkování: 16,0 – 20,0 ml přípravku Aminoven 5%/kg těl. hm./den (ekv. 0,8 - 1,0 g aminokyselin/kg těl. hm./den), to např. odpovídá 1120 - 1400 ml přípravku Amin“
- dávka `0,8 - 1,0 g aminokyselin/kg těl. hm./den` ← „Dávkování: 16,0 – 20,0 ml přípravku Aminoven 5%/kg těl. hm./den (ekv. 0,8 - 1,0 g aminokyselin/kg těl. hm./den), to např. odpovídá 1120 - 1400 ml přípravku Amin“
- dávka `2,0 ml přípravku Aminoven 5%/kg těl. hm./hod.` ← „Maximální infuzní rychlost: 2,0 ml přípravku Aminoven 5%/kg těl. hm./hod. (ekv. 0,1 g aminokyselin/kg těl. hm./hod.)“
- dávka `0,1 g aminokyselin/kg těl. hm./hod.` ← „Maximální infuzní rychlost: 2,0 ml přípravku Aminoven 5%/kg těl. hm./hod. (ekv. 0,1 g aminokyselin/kg těl. hm./hod.)“
- dávka `20 ml přípravku Aminoven 5%/kg těl. hm./den` ← „Maximální denní dávka: 20 ml přípravku Aminoven 5%/kg těl. hm./den (ekv. 1,0 g aminokyselin/kg těl. hm./den), to odpovídá 70 g aminokyselin na 70 kg těl. hm. pa“
- dávka `1,0 g aminokyselin/kg těl. hm./den` ← „Maximální denní dávka: 20 ml přípravku Aminoven 5%/kg těl. hm./den (ekv. 1,0 g aminokyselin/kg těl. hm./den), to odpovídá 70 g aminokyselin na 70 kg těl. hm. pa“
- dávka `40 ml přípravku Aminoven 5% na kg tělesné hmotnosti/den` ← „40 ml přípravku Aminoven 5% na kg tělesné hmotnosti/den (ekv. 2,0 g aminokyselin na kg tělesné hmotnosti/den), je však nutné vzít v potaz celkový denní příjem t“
- dávka `2,0 g aminokyselin na kg tělesné hmotnosti/den` ← „40 ml přípravku Aminoven 5% na kg tělesné hmotnosti/den (ekv. 2,0 g aminokyselin na kg tělesné hmotnosti/den), je však nutné vzít v potaz celkový denní příjem t“
