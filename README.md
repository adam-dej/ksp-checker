# ksp-checker
*Tasks cross-checker for Correspondence Seminar in Programming*

Skript ktorý sa spúšťa pri kompilácií zadaní a robí im sanity checking.


Po spustení tento skript najskôr zoberie veci na check a sparsuje ich. To sa
robí mimo testov lebo ak by sa zmenil formát súborov nech netreba všetky testy
prepísať. Potom sa spustia jednotlivé testy, ktoré dostanú path k zadaniam (ak
chcú checkovať súborovú štruktúru, filenames...), plaintexty zadaní (ak chcú
checkovať newlines, trailing whitespace...) a sparsované zadania (ak chcú
checkovať počty bodov, správnosť názvov úloh...)

## Súbory

  - `check.py` je hlavný executable súbor. Tento spúšťajte. test_utils.py` a
  - `issue_utils.py` a `test_utils.py` sú pomocné drobnosti ktoré potrebujú
    testy, parsery a hlavný script.
  - `tests.py` - v tomto súbore sú definované rôzne testy ktoré sa majú spúštať
  - `models.py` - v tomto súbore sú definované entity reprezentujúce zadania a
    vzoráky a návody ako ich vyparsovať.

Súborov `check.py`, `issue_utils.py` a `test_utils.py` by sa bežný testopísač
nemal musieť chytať.

Bežný testopísač by mal písať testy do `tests.py`. Ak by sa zmenil formát zadaní
a / alebo vzorákov, bude nutné príslušne upraviť aj `models.py`.

## Test

Test je obyčajná funkcia v sekcii skriptu "TESTY", ktorá je dekorovaná @test
dekorátorom. Meno tejto funkcie je názov testu (bude sa používať v argumentoch,
ako chybová hláška keď test zlyhá a tak.) Test musí obsahovať neprázdny
docstring ktorý v prvom riadku pár slovami popíše čo test robí a v ostatných
riadkoch (indentovaných 4mi medzerami) optionally test popíše detailnejšie. Test
hlási chyby a iné veci loggeru ktorý mu je daný. Vráti boolean (`True` je
success), alebo jedno z `TestResult.{OK, SKIP, WARNING, ERROR}` Na pridanie
nového testu teda stačí napísať príslušnú fciu s dekorátorom a docstringom, o
ostatné sa starať netreba :)

### Implementované testy

Use the source, Luke. Každý test by mal mať napísané na čo je. A stále existuje
flag `-p` :)

## Dekorátory

Dekorátory *je treba* používať v poradí v akom sú tu popísané. Všetky dekorátory
iné ako `@test` sú len pre pohodlnosť pri písaní testov a nemusia byť použité.

### `@test`

Týmto dekorátorom sa registruje test. Každá funkcia obsahujúca tento dekorátor
je považovaná sa test. Dekorátor berie jeden parameter, a to je závažnosť testu.
Ak test nevráti nejakú vec z `TestResult` v prípade vrátenia falsy objektu bude
vrátená táto hodnota. Nepovinný parameter je `require`. Je to list kľúčov ktoré
musia byť v dicte `test_data` aby malo zmysel tento test spúštať. Ak niektorá z
veci chýba, test vráti `TestResult.SKIP`

### `@for_each_item_in`

Tento iterátor bere ako parameter kľúč do `test_data`. Spôsobí to, že sa
preiteruje cez `test_data[parameter]` a test spustí pre každý item miesto iba
raz pre celé test_data. Použitie tohto dekorátora mení hlavičku testu, a druhý
parameter už nie je `test_data`, ale item z `test_data[parameter]`. Príklad v
praxi: Chceme spustiť tento test pre každé zadanie v `test_data["tasks"]`.
Optional parameter tohto dekorátora je `bypassable`. Ak je true a item obsahuje
list `bypass` a tento list obsahuje meno testu dekorovaného týmto, tak test sa
pre tento súbor preskočí. V praxi sa tento list buduje z komentárov štýlu
`%skiptest testName` zo zadaní a vzorákov a slúži na preskočenie
neaplikovateľných testov na ten vzorák / zadanie (napríklad úlohou je vypísať 10
medzier na čo sa test sťažuje že výstup ma trailing whitespaces, tak tento test
preskočíme)

Workflow scriptu
----------------

Najskôr beží `main`. Jej úlohou je sparsovať argumenty ktore boli scriptu dané.
Na základe týchto argumentov spúšťa ostatné časti scriptu. Obvykle upraví zoznam
testov ktoré majú bežať a spustí funkciu `execute`. Táto funkcia zoberie cesty k
zadaniam, vstupom a vzorákom a spustí na nich funkcie `parse_{markdown,inputs}`
(parsovanie úloh a vzorákov je tak podobné že to rieši jedna fcia
`parse_markdown`). Tieto funkcie sa preiterujú súbormi so správnym menom, a na
každom súbore spustia `{Task,Solution}.parse`. Tieto funkcie sparsujú už
konkrétny súbor. Sú umiestnené v časti skriptu "PARSER" a určené na pravidelné
menenie maintainerom testov pri zmene formátu súborov. Funkcie
`{Task,Solution}.parse` vrátia objekty sparsovaných vecí funkciám
`parse_{markdown,inputs}`. Tieto vrátia listy sparsovaných objektov funkcii
`execute`. Táto funkcia z týchto dát postaví `test_data` dict, ktorý sa neskôr
bude dávať jednotlivým testom. `execute` následne spustí funkciu `execute_tests`
so zoznamom testov, dictom `test_data` a classou loggera ktorú maju testy
používať. `execute_tests` následne spúšťa jednotlivé testy (pre každý vytvorí
instanciu loggera s appropriate identifikátorom testu). Zoznam so štatistikami
ohľadom behu testov je vrátení fcii `execute`, ktorá vypíše finálne hlášky a
vygeneruje vhodný return code.

Čo týmto skriptom básnik myslel...
----------------------------------

Alebo náhodné poznámky pre náhodných maintainerov.

 - Cieľ tohto skriptu nie je mať len implementované testy, ale aj zjednodušiť
   písanie nových
 - Dodržujte PEP-8 (okrem max dĺžky riadku, to nech je 100)
 - Snažte sa o konzistentný coding style
 - Nakoľko sa meno fcie testu používa v chybovej hláške o zlyhaní a tak, mená
   majú dávať zmysel (prosím, žiadne `T_PAAMAYIM_NEKUDOTAYIM` ;) )
 - Unix-like: "No news are good news". Nevypisujte hlúposti ak nie ste verbose.
 - Logging je urobený tak ako je aby sa jednoducho dal zmeniť formát výstupu ak
   by niekto chcel script použiť ako linter v editore.
 - Tento script je zatiaľ iba v zadaniach kde sa môže správať ako chce.
   Eventuálne ale bude jeden build step keď sa budú automaticky v CI buildiť
   zadania, preto je napísaný tak ako je.
