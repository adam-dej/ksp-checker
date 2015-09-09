#!/usr/bin/env python3

# Skript ktorý sa spúšťa pri kompilácií zadaní a robí im sanity checking.
#
# Po spustení tento skript najskôr zoberie veci na check a sparsuje ich. To sa robí mimo testov lebo
# ak by sa zmenil formát súborov nech netreba všetky testy prepísať. Potom sa spustia jednotlivé
# testy, ktoré dostanú path k zadaniam (ak chcú checkovať súborovú štruktúru, filenames...),
# plaintexty zadaní (ak chcú checkovať newlines, trailing whitespace...) a sparsované zadania (ak
# chcú checkovať počty bodov, správnosť názvov úloh...)
#
# Test
# ----
#
# Test je obyčajná funkcia v sekcii skriptu "TESTY", ktorá je dekorovaná @test dekorátorom. Meno
# tejto funkcie je názov testu (bude sa používať v argumentoch, ako chybová hláška keď test zlyhá a
# tak.) Test musí obsahovať neprázdny docstring ktorý v prvom riadku pár slovami popíše čo test robí
# a v ostatných riadkoch (indentovaných 4mi medzerami) optionally test popíše detailnejšie.
#
# Test hlási chyby a iné veci loggeru ktorý mu je daný. Vráti boolean (True je success), alebo jedno
# z TestResult.{OK, SKIP, WARNING, ERROR}
#
# Na pridanie nového testu teda stačí napísať príslušnú fciu s dekorátorom a docstringom, o ostatné
# sa starať netreba :)
#
# Dekorátory
# ----------
#
# Dekorátory je treba používať v poradí v akom sú tu popísané. Všetky dekorátory iné ako @test
# sú len pre pohodlnosť pri písaní testov a nemusia byť použité.
#
# @test: Týmto dekorátorom sa registruje test. Každá funkcia obsahujúca tento dekorátor je
#        považovaná sa test. Dekorátor berie jeden parameter, a to je závažnosť testu. Ak test
#        nevráti nejakú vec z TestResult v prípade vrátenia falsy objektu bude vrátená táto hodnota.
# @require: Tento dekorátor spôsobí vrátenie TestResult.SKIP ak v test_data nie je potrebný údaj pre
#           beh daného testu. Ako parameter berie list potrebných keys z test_data
# @for_each_item: Tento iterátor bere ako parameter kľúč do test_data. Spôsobí to, že sa preiteruje
#                 cez test_data[parameter] a test spustí pre každý item miesto iba raz pre celé
#                 test_data. Použitie tohto dekorátora mení hlavičku testu, a druhý parameter už nie
#                 je test_data, ale item z test_data[parameter]. Príklad v praxi: Chceme spustiť
#                 tento test pre každé zadanie v test_data["tasks"].
#                 Optional parameter tohto dekorátora je bypassable. Ak je true a item obsahuje
#                 list `bypass` a tento list obsahuje meno testu dekorovaného týmto, tak test sa
#                 pre tento súbor preskočí. V praxi sa tento list buduje z komentárov štýlu
#                 '%skiptest testName' zo zadaní a vzorákov a slúži na preskočenie neaplikovateľných
#                 testov na ten vzorák / zadanie (napríklad úlohou je vypísať 10 medzier na čo sa
#                 test sťažuje že výstup ma trailing whitespaces, tak tento test preskočíme)
#
# Workflow scriptu
# ----------------
#
# Najskôr beží `main`. Jej úlohou je sparsovať argumenty ktore boli scriptu dané. Na základe týchto
# argumentov spúšťa ostatné časti scriptu. Obvykle upraví zoznam testov ktoré majú bežať a spustí
# funkciu `execute`. Táto funkcia zoberie cesty k zadaniam, vstupom a vzorákom a spustí na nich
# funkcie `parse_{files,inputs}` (parsovanie úloh a vzorákov je tak podobné že to rieši jedna fcia
# `parse_files`). Tieto funkcie sa preiterujú súbormi so správnym menom, a na každom súbore spustia
# `parse_{task,solution}`. Tieto funkcie sparsujú už konkrétny súbor. Sú umiestnené v časti skriptu
# "PARSER" a určené na pravidelné menenie maintainerom testov pri zmene formátu súborov. Funkcie
# `parse_{task,input,solution}` vrátia objekty sparsovaných vecí funkciám
# `parse_{tasks,inputs,solutions}`. Tieto vrátia listy sparsovaných objektov funkcii `execute`. Táto
# funkcia z týchto dát postaví `test_data` dict, ktorý sa neskôr bude dávať jednotlivým testom.
# `execute` následne spustí funkciu `execute_tests` so zoznamom testov, dictom `test_data` a classou
# loggera ktorú maju testy používať. `execute_tests` následne spúšťa jednotlivé testy (pre každý
# vytvorí instanciu loggera s appropriate identifikátorom testu). Zoznam so štatistikami ohľadom
# behu testov je vrátení fcii `execute`, ktorá vypíše finálne hlášky a vygeneruje vhodný return
# code.
#
# Čo týmto skriptom básnik myslel...
# ----------------------------------
#
# Alebo náhodné poznámky pre náhodných maintainerov.
#
#  - Cieľ tohto skriptu nie je mať len implementované testy, ale aj zjednodušiť písanie nových
#  - Dodržujte PEP-8 (okrem max dĺžky riadku, to nech je 100)
#  - Snažte sa o konzistentný coding style
#  - Nakoľko sa meno fcie testu používa v chybovej hláške o zlyhaní a tak, mená majú dávať zmysel
#    (prosím, žiadne T_PAAMAYIM_NEKUDOTAYIM ;) )
#  - Unix-like: "No news are good news". Nevypisujte hlúposti ak nie ste verbose.
#  - Tento script je zatiaľ iba v zadaniach kde sa môže správať ako chce. Eventuálne ale bude jeden
#    build step keď sa budú automaticky v CI buildiť zadania, preto je napísaný tak ako je.

import logging
import argparse
import sys
import os
import re
import copy
import glob
from enum import Enum

logger = logging.getLogger('checker')
logger.setLevel(logging.WARNING)
formatter = logging.Formatter('Kontrola zadaní - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class TestResult(Enum):
    OK = 0
    SKIP = 1
    WARNING = 2
    ERROR = 3


class TestRegistrar():
    def __init__(self):
        self.all = {}

    def __call__(self, severity):
        def registrar_decorator(func):
            def wrapper(logger, test_data):
                status = func(logger, test_data)
                # Ak funkcia vráti boolean miesto TestResult, vráťme hodnotu parametra severity pri
                # zlyhaní.
                if not isinstance(status, TestResult):
                    return severity if not status else TestResult.OK
                else:
                    return status

            self.all[func.__name__] = {"doc": func.__doc__, "run": wrapper}
            return wrapper
        return registrar_decorator

test = TestRegistrar()


def require(listOfRequirements):
    def require_decorator(function):
        def require_wrapper(logger, test_data):
            for requirement in listOfRequirements:
                if requirement not in test_data.keys() or not test_data[requirement]:
                    logger.logMessage(logging.DEBUG, 'Nemám potrebné veci, skippupjem sa...')
                    return TestResult.SKIP
            return function(logger, test_data)
        require_wrapper.__name__ = function.__name__
        require_wrapper.__doc__ = function.__doc__
        return require_wrapper
    return require_decorator


def for_each_item(items, bypassable=False):
    def foreach_decorator(function):
        def wrapper(logger, test_data):
            success = True
            for item in test_data[items]:
                if bypassable and item.bypass and function.__name__ in item.bypass:
                    logger.logMessage(logging.DEBUG, (("Nájdená inštrukcia na preskočenie testu v" +
                                                       " \"{0}\", preskakujem test {1}")
                                                      .format(item.filename, function.__name__)))
                    continue
                if not function(logger, item):
                    success = False
            return success
        wrapper.__name__ = function.__name__
        wrapper.__doc__ = function.__doc__
        return wrapper
    return foreach_decorator


class Issue():
    def __init__(self, message, file, line=None):
        self.message = message
        self.file = file
        self.line = line


# Nejaký takýto objekt dostane test do parametra logger. Defaultná implementácia iba vypíše chyby do
# konzoly. V budúcnosti je možné takto prispôsobiť výstup tohto skriptu pre editory kde môže
# fungovať ako linter. Parameter severity je z modulu logging (napr logging.WARNING)
class IssueLogger():
    def __init__(self, logger_name):
        pass

    def logMessage(self, severity, message):
        pass

    def logIssue(self, severity, Issue):
        pass


# ---------------------------------- TESTY ------------------------------------

@test(TestResult.ERROR)
@require(["tasks"])
def allTasksPresent(logger, test_data):
    """Kontrola či existuje všetkých 8 úloh."""

    tasks_exist = [False]*8

    for task in test_data["tasks"]:
        tasks_exist[task.number-1] = True

    for task_number, task_exists in enumerate(tasks_exist):
        if not task_exists:
            logger.logIssue(logging.ERROR,
                            Issue("Úloha číslo {0} neexistuje!".format(task_number+1), ""))

    return all(tasks_exist)


@test(TestResult.ERROR)
@require(["tasks"])
@for_each_item("tasks")
def taskComplete(logger, task):
    """Kontrola či úloha má meno a autora"""

    success = True
    if not task.name:
        logger.logIssue(logging.ERROR, Issue("Úloha nemá meno!", task.filename))
        success = False
    if not task.author:
        logger.logIssue(logging.ERROR, Issue("Úloha nemá autora!", task.filename))
        success = False
    return success


@test(TestResult.WARNING)
@require(["tasks"])
@for_each_item("tasks", bypassable=True)
def taskProofreaded(logger, task):
    """Kontrola či je úloha sproofreadovaná"""

    if not task.proofreader:
        logger.logIssue(logging.WARNING, Issue("Úloha nie je sproofreadovaná!", task.filename))
        return False
    return True


@test(TestResult.ERROR)
@require(["tasks"])
@for_each_item("tasks", bypassable=True)
def taskFirstLetter(logger, task):
    """Kontrola prvého písmenka úlohy.

    Tento test zlyhá, ak úlohy v kategórií Z a O nezačínajú na správne písmenko."""

    config = []
    config += ['Z']*4  # Prvé 4 úlohy majú začínať Z-tkom
    config += ['O']*4  # Ďalšie 4 úlohy majú začínať O-čkom

    if not task.name.startswith(config[task.number-1]):
        logger.logIssue(logging.ERROR,
                        Issue(("Úloha \"{0}\" nezačína správnym písmenom ({1})!"
                              .format(task.name, config[task.number-1])), task.filename))
        return False
    return True


@test(TestResult.ERROR)
@require(["tasks"])
@for_each_item("tasks", bypassable=True)
def taskCorrectPoints(logger, task):
    """Kontrola správneho súčtu bodov.

    Tento test zlyhá ak úlohy nemajú správne súčty bodov. Správne súčty bodov sú 10 za príklady
    1-3, 15 za 4-5 a 20 za 6-8."""

    config = []
    config += [10]*3  # Úlohy 1-3 10b
    config += [15]*2  # Úlohy 4-5 15b
    config += [20]*3  # Úlohy 6-8 20b

    task_points = (task.points["bodypopis"] + task.points["bodyprogram"])
    if task_points != config[task.number-1]:
        logger.logIssue(logging.ERROR,
                        Issue(("Úloha \"{0}\" nemá spávny počet bodov! Má {1}, má mať {2}."
                               .format(task.name, task_points, config[task.number-1])),
                              task.filename))
        return False
    return True


@test(TestResult.ERROR)
@require(["tasks"])
@for_each_item("tasks", bypassable=True)
def taskSamplesEndWithUnixNewline(logger, task):
    """Kontrola či všetky príklady vstupu / výstupu končia s UNIX newline."""

    lines = task.plaintext.splitlines(True)
    checking = False
    success = True
    for index, line in enumerate(lines):
        if line.startswith('```vstup') or line.startswith('```vystup'):
            checking = True
            continue
        if line.startswith('```'):
            checking = False
            continue
        if checking and line.endswith('\r\n'):
            logger.logIssue(logging.ERROR, Issue("Riadok má Windowsácky endline!",
                                                 task.filename, index+1))
            success = False
    return success


@test(TestResult.ERROR)
@require(["tasks"])
@for_each_item("tasks", bypassable=True)
def taskSamplesWhitespace(logger, task):
    """Kontrola či príklady vstupu / výstupu nekončia medzerou."""

    success = True
    lines = task.plaintext.splitlines(True)
    checking = False
    for index, line in enumerate(lines):
        if line.startswith('```vstup') or line.startswith('```vystup'):
            checking = True
            continue
        if line.startswith('```'):
            checking = False
            continue
        if checking and re.match("[^ \t\r\f\v]*[ \t\r\f\v]+$", line):
            logger.logIssue(logging.ERROR, Issue("Riadok končí whitespace-om!", task.filename,
                                                 index+1))
            success = False
    return success


@test(TestResult.WARNING)
@require(["solutions"])
def allSolutionsPresent(logger, test_data):
    """Kontrola či existujú všetky vzoráky."""

    solutions_exist = [False]*8

    for solution in test_data["solutions"]:
        solutions_exist[solution.number-1] = True

    for solution_number, solution_exists in enumerate(solutions_exist):
        if not solution_exists:
            logger.logIssue(logging.WARNING,
                            Issue("Vzorák číslo {0} neexistuje!".format(solution_number+1), ""))

    return all(solutions_exist)


@test(TestResult.ERROR)
@require(["solutions"])
@for_each_item("solutions")
def solutionComplete(logger, solution):
    """Kontrola či vzorák má meno a autora."""

    success = True
    if not solution.name:
        logger.logIssue(logging.ERROR, Issue("Vzorák nemá meno!", solution.filename))
        success = False
    if not solution.author:
        logger.logIssue(logging.ERROR, Issue("Vzorák nemá autora!", solution.filename))
        success = False
    return success


@test(TestResult.ERROR)
@require(["tasks", "solutions"])
def solutionMatchesTask(logger, test_data):
    """Kontrola či úloha a prislúchajúci vzorák majú rovnaké meno a rovnaké body."""

    tasks = [None]*8
    solutions = [None]*8

    for task in test_data["tasks"]:
        tasks[task.number-1] = task

    for solution in test_data["solutions"]:
        solutions[solution.number-1] = solution

    success = True
    for index in range(8):
        if tasks[index] and solutions[index]:
            if tasks[index].name != solutions[index].name:
                logger.logIssue(logging.ERROR,
                                Issue(("Názov vzoráku \"{0}\" sa nezhoduje s názvom" +
                                       " úlohy \"{1}\"").format(solutions[index].name,
                                                                tasks[index].name),
                                      solutions[index].filename))
                success = False
            if tasks[index].points != solutions[index].points:
                logger.logIssue(logging.ERROR,
                                Issue(("Body za úlohu \"{1}\" sa nezhodujú s bodmi vo vzoráku " +
                                       "\"{0}\"").format(solutions[index].points,
                                                         tasks[index].points),
                                      solutions[index].filename))
                success = False
    return success


@test(TestResult.ERROR)
@require(["solutions"])
@for_each_item("solutions")
def solutionAllListingsExist(logger, solution):
    """Kontrola či existujú všetky súbory listingov použité vo vzoráku."""

    success = True
    for idx, line in enumerate(solution.plaintext.splitlines()):
        # Matchne '\listing{...}'
        match = re.match('\\\\listing{([^}]*)}', line)
        if match and not os.path.isfile(os.path.join(os.path.dirname(solution.filename),
                                                     match.group(1))):
            logger.logIssue(logging.ERROR,
                            Issue("Listing {0} neexistuje!".format(match.group(1)),
                                  solution.filename, idx+1))
            success = False
    return success


@test(TestResult.WARNING)
@require(["tasks", "inputs"])
def taskHasInputs(logger, test_data):
    """Kontrola či každá úloha má vstupy."""

    success = True
    for task in test_data["tasks"]:
        if not test_data["inputs"][task.number-1]:
            logger.logIssue(logging.WARNING, Issue("Úloha nemá vstupy!", task.filename))
            success = False
    return success


@test(TestResult.ERROR)
@require(["inputs"])
@for_each_item("inputs")
def inputsHaveUnixNewlines(logger, tests):
    """Kontrola či majú vstupy UNIXácke newlines."""

    for inp, inp_filename in tests.items():
        inp_file = open(inp_filename, 'rb')
        line_number = 1
        for line in inp_file:
            if '\r\n' in line.decode('utf-8'):
                logger.logIssue(logging.ERROR, Issue("Vstup má Windowsácky newline!",
                                                     inp_filename, line_number))
                inp_file.close()
                return False
            line_number += 1
        inp_file.close()
    return True


@test(TestResult.WARNING)
@require(["inputs"])
@for_each_item("inputs")
def inputsNoTrailingWhitespace(logger, tests):
    """Kontrola či vstupy a výstupy nemajú medzery na konci riadkov."""

    success = True
    for inp, inp_filename in tests.items():
        inp_file = open(inp_filename, 'r')
        line_number = 1
        for line in inp_file:
            if re.match("[^ \t\r\f\v]*[ \t\r\f\v]+$", line):
                logger.logIssue(logging.WARNING,
                                Issue("Vstup má na konci riadku whitespaces!", inp_filename,
                                      line_number))
                success = False
            line_number += 1
        inp_file.close()
    return success


@test(TestResult.ERROR)
@require(["inputs"])
@for_each_item("inputs")
def eachInputHasOutput(logger, tests):
    """Kontrola či každý .in súbor zo vstupov má prislúchajúci .out súbor"""

    for inp, inp_filename in tests.items():
        if inp.endswith('.in') and inp[:-3]+'.out' not in tests.keys():
            logger.logIssue(logging.ERROR, Issue("Vstup nemá výstup!", inp_filename))
            return False
    return True


@test(TestResult.ERROR)
@require(["inputs"])
@for_each_item("inputs")
def inputHasNewlineAtEof(logger, tests):
    """Kontrola či posledný riadok vo vstupoch a výstupoch končí znakom nového riadku."""

    for inp, inp_filename in tests.items():
        inp_file = open(inp_filename, 'r')
        line_number = 1
        for line in inp_file:
            line_number += 1
        inp_file.close()
        if not line.endswith('\n'):
            logger.logIssue(logging.ERROR,
                            Issue("Súbor nekončí znakom nového riadku!", inp_filename, line_number))
            return False
    return True


# -----------------------------------------------------------------------------

# --------------------------------- PARSER ------------------------------------


class Task():
    def __init__(self, task_filename=None, task_text=None):
        self.plaintext = task_text
        self.filename = task_filename

        self.name = None
        self.number = None
        self.points = {}
        self.author = None
        self.proofreader = None

        self.bypass = []


class Solution():
    def __init__(self, solution_filename=None, solution_text=None):
        self.plaintext = solution_text
        self.filename = solution_filename

        self.name = None
        self.number = None
        self.points = {}
        self.author = None

        self.bypass = []


def parse_task(logger, task_filename):
    # Binary read mode lebo zachovajme newlines
    task_file = open(task_filename, 'rb')
    task = Task(task_filename, task_file.read().decode("utf-8"))

    lines = task.plaintext.splitlines()

    # Vyparsujeme číslo príkladu
    fname = os.path.basename(task.filename)
    try:
        found_task_number = re.search('prikl([0-9]*)', fname).group(1)
        task.number = int(found_task_number)
    except (AttributeError, IndexError, ValueError):
        logger.logIssue(logging.ERROR, Issue("Súbor nemá platné číslo príkladu!", fname))
        return None

    # Vyparsujme meno príkladu
    try:
        # Regex ktoý chce matchnúť meno príkladu (po # a pred {} s bodmi)
        found_task_name = re.search('\.?#([^{}]*)', lines[0]).group(1)
        task.name = found_task_name.strip()
    except (AttributeError, IndexError):
        logger.logIssue(logging.WARNING, Issue("Nepodarilo sa zistiť meno príkladu!", fname))

    # Vyparsujeme body za príklad
    try:
        # Regex ktorý chce matchnúť čísleka s bodmi
        found_points = re.search('{bodypopis=([0-9]*) bodyprogram=([0-9]*)}', lines[0])
        task.points["bodypopis"] = int(found_points.group(1))
        task.points["bodyprogram"] = int(found_points.group(2))
    except (AttributeError, IndexError, ValueError):
        logger.logIssue(logging.WARNING, Issue("Nepodarilo sa zistiť body za príklad!", fname))

    for idx, line in enumerate(lines):
        # Vyparsujeme autora
        found_author = re.search('%by (.*)', line)
        if found_author:
            if task.author is not None:
                logger.warning('Úloha %s má údajne viac autorov!', task.filename)
            task.author = found_author.group(1)

        # Vyparsujeme ktoré testy máme preskočiť
        found_skiptest = re.search('%skiptest (.*)', line)
        if found_skiptest:
            task.bypass.append(found_skiptest.group(1))

        # Vyparsujeme proofreadera
        found_proofreader = re.search('%proofread (.*)', line)
        if found_proofreader:
            if task.proofreader is not None:
                logger.logIssue(logging.WARNING, Issue('Úloha má údajne viac proofreaderov!',
                                                       fname, idx+1))
            task.proofreader = found_proofreader.group(1)

    return task


def parse_solution(logger, solution_filename):
    # Binary read mode lebo zachovajme newlines
    solution_file = open(solution_filename, 'rb')
    solution = Solution(solution_filename, solution_file.read().decode("utf-8"))

    lines = solution.plaintext.splitlines()

    # Vyparsujeme číslo príkladu
    fname = os.path.basename(solution.filename)
    try:
        found_solution_number = re.search('prikl([0-9]*)', fname).group(1)
        solution.number = int(found_solution_number)
    except (AttributeError, IndexError, ValueError):
        logger.logIssue(logging.ERROR, Issue("Súbor nemá platné číslo príkladu!", fname))
        return None

    # Vyparsujme meno príkladu
    try:
        # Regex ktoý chce matchnúť meno príkladu (po # a pred {} s bodmi)
        found_solution_name = re.search('\.?#([^{}]*)', lines[0]).group(1)
        solution.name = found_solution_name.strip()
    except (AttributeError, IndexError):
        logger.logIssue(logging.WARNING, Issue("Nepodarilo sa zistiť meno príkladu!", fname))

    # Vyparsujeme autora a body za príklad
    try:
        # Regex ktorý chce matchnúť autora a čísleka s bodmi
        found = re.search('{vzorak="([^"]*)" bodypopis=([0-9]*) bodyprogram=([0-9]*)}', lines[0])
        solution.author = found.group(1)
        solution.points["bodypopis"] = int(found.group(2))
        solution.points["bodyprogram"] = int(found.group(3))
    except (AttributeError, IndexError, ValueError):
        logger.logIssue(logging.WARNING, Issue("Nepodarilo sa zistiť autora a body za príklad!",
                        fname))

    for idx, line in enumerate(lines):

        # Vyparsujeme ktoré testy máme preskočiť
        found_skiptest = re.search('%skiptest (.*)', line)
        if found_skiptest:
            solution.bypass.append(found_skiptest.group(1))

    return solution


# -----------------------------------------------------------------------------


# Implementácia IssueLoggera ktorý vypisuje veci priamo do konzoly
class ConsoleIssueLogger(IssueLogger):
    def __init__(self, logger_name):
        self.logger = logging.getLogger(logger_name)

    def logMessage(self, severity, message):
        self.logger.log(severity, message)

    def logIssue(self, severity, issue):
        if issue.line:
            self.logger.log(severity, "File %s, line %i: %s", issue.file, issue.line, issue.message)
        else:
            self.logger.log(severity, "File %s: %s", issue.file, issue.message)


def print_tests():
    for tst_name, tst in test.all.items():
        print(tst_name, " - ", tst['doc'])
        print()


def parse_markdown(IssueLogger, path_to_files, what):
    VALID_TASK_FILE_NAME = 'prikl*.md'
    things = []
    if not os.path.isdir(path_to_files):
        logger.critical("folder '%s' nenájdený alebo nie je folder!", path_to_files)
    for filename in glob.iglob(os.path.join(path_to_files, VALID_TASK_FILE_NAME)):
        if os.path.isfile(filename):
            logger.debug("Čítam súbor %s", filename)
            if what == "tasks":
                thing = parse_task(IssueLogger("checker.parser.task"), filename)
            elif what == "solutions":
                thing = parse_solution(IssueLogger("checker.parser.solution"), filename)

            if thing is not None:
                things.append(thing)
    return things


def parse_inputs(IssueLogger, path_to_inputs):
    inputs = []
    if not os.path.isdir(path_to_inputs):
        logger.critical("folder '%s' nenájdený alebo nie je folder!", path_to_files)
    for i in range(1, 9):
        folder = os.path.join(path_to_inputs, str(i))
        if os.path.isdir(folder):
            task_inputs = {}
            inputs_folder = os.path.join(folder, 'test')
            if os.path.isdir(inputs_folder):
                for inp in os.listdir(inputs_folder):
                    task_inputs[inp] = os.path.join(inputs_folder, inp)
            inputs.append(task_inputs)
        else:
            inputs.append(None)
    return inputs


def execute_tests(tests, test_data, logger_class, strict):
    results = {TestResult.SKIP: 0,
               TestResult.OK: 0,
               TestResult.WARNING: 0,
               TestResult.ERROR: 0}

    for test_name, test in tests.items():
        logger.debug("Spúšťam test %s", test_name)

        # deepcopy lebo nechceme aby prišiel niekto, v teste zmenil test_data a tak rozbil všetky
        # ostatné testy
        status = test["run"](logger_class('checker.' + test_name), copy.deepcopy(test_data))

        if status == TestResult.WARNING and strict:
            status = TestResult.ERROR

        results[status] += 1

        if status == TestResult.ERROR:
            logger.error("Test %s ZLYHAL!", test_name)
        elif status == TestResult.WARNING:
            logger.warning("Test %s skončil s varovaním!", test_name)
        elif status == TestResult.OK:
            logger.debug("Test %s je ok.", test_name)
        elif status == TestResult.SKIP:
            logger.debug("Test %s skippol sám seba", test_name)

    return results


def execute(args, tests):
    logger.debug("Spustím tieto testy: %s", tests.keys())
    tasks = None
    inputs = None
    solutions = None

    if not (args.path_to_tasks or args.path_to_inputs or args.path_to_solutions):
        logger.warning("Nedal si mi ani zadania, ani vstupy ani vzoráky. Čo mám teda testovať?")

    if args.path_to_tasks:
        logger.debug("Spúšťam testy na zadaniach z '%s'", args.path_to_tasks[0])
        tasks = parse_markdown(ConsoleIssueLogger, args.path_to_tasks[0], "tasks")

    if args.path_to_inputs:
        logger.debug("Spúšťam testy na vstupoch z '%s'", args.path_to_inputs[0])
        inputs = parse_inputs(ConsoleIssueLogger, args.path_to_inputs[0])

    if args.path_to_solutions:
        logger.debug("Spúšťam testy na vzorákoch z '%s'", args.path_to_solutions[0])
        solutions = parse_markdown(ConsoleIssueLogger, args.path_to_solutions[0], "solutions")

    test_data = {"path_to_tasks": args.path_to_tasks[0] if args.path_to_tasks is not None else None,
                 "path_to_solutions": (args.path_to_solutions[0]
                                       if args.path_to_solutions is not None else None),
                 "path_to_inputs": (args.path_to_inputs[0]
                                    if args.path_to_inputs is not None else None),
                 "tasks": tasks,
                 "solutions": solutions,
                 "inputs": inputs}

    results = execute_tests(tests, test_data, ConsoleIssueLogger, args.strict)

    logger.info("Done\n\n")

    logger.info("Výsledky: OK      - %i", results[TestResult.OK])
    logger.info("          SKIP    - %i", results[TestResult.SKIP])
    logger.info("          WARNING - %i", results[TestResult.WARNING])
    logger.info("          ERROR   - %i", results[TestResult.ERROR])

    if results[TestResult.ERROR] != 0:
        logger.critical("Celé zle. Zlyhalo %i testov!", results[TestResult.ERROR])
        return 1
    elif results[TestResult.WARNING] != 0:
        logger.warning("Testy zbehli ok, ale bolo %i warningov!", results[TestResult.WARNING])
        return 0
    else:
        logger.info("Testy zbehli ok. Dobrá práca.")
        return 0


def main():
    argumentParser = argparse.ArgumentParser(description="Checker KSP zadaní")
    argumentParser.add_argument('--tasks', nargs=1, dest='path_to_tasks',
                                help="Cesta k foldru so zadaniamu")
    argumentParser.add_argument('--inputs', nargs=1, dest="path_to_inputs",
                                help="Cesta k foldru so vstupmi")
    argumentParser.add_argument('--solutions', nargs=1, dest="path_to_solutions",
                                help="Cesta k foldru so vzorákmi")
    argumentParser.add_argument('-p', '--print-tests', action="store_true", dest="print_only",
                                help="Iba vypíš aké testy poznáš a skonči")
    argumentParser.add_argument('--strict', action="store_true", dest="strict",
                                help="Správaj sa k warningom ako k chybám")
    argumentParser.add_argument('-s', '--skip', nargs='*', dest="skip", metavar="test",
                                help="Preskoč tieto testy")
    argumentParser.add_argument('-r', '--run-only', nargs='*', dest="runonly", metavar="test",
                                help="spusti IBA tieto testy. Overridne --skip")
    argumentParser.add_argument('-v', action="count", dest="verbosity",
                                help="Viac sa vykecávaj (-vv kecá ešte viac)")
    args = argumentParser.parse_args()

    if args.print_only:
        print_tests()
        return 0

    if args.verbosity:
        if args.verbosity == 1:
            logger.setLevel(logging.INFO)
        if args.verbosity > 1:
            logger.setLevel(logging.DEBUG)

    if args.runonly:
        # Check či testy vôbec existujú
        tests_to_run = dict()
        for tst_name in args.runonly:
            if tst_name not in test.all:
                logger.critical("Bol requestnutý beh testu %s, ale ten neexistuje.", tst_name)
                return 1
            tests_to_run[tst_name] = test.all[tst_name]
        return execute(args, tests_to_run)

    if args.skip:
        # Ak nejaký test neexistuje a chceme ho skipnúť je to asi chyba / typo
        # a test čo nemá by bežal. Umrime radšej.
        tests_to_run = dict(test.all)
        for tst_name in args.skip:
            if tst_name not in test.all:
                logger.critical("Bolo requestnuté skipnutie testu %s, ale tento neexistuje.",
                                tst_name)
                return 1
            del tests_to_run[tst_name]
        return execute(args, tests_to_run)

    return execute(args, dict(test.all))

if __name__ == "__main__":
    sys.exit(main())
