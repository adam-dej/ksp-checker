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
# Test hlási chyby a iné veci loggeru ktorý mu je daný. Vráti jedno z TestResult.{OK, SKIP, WARNING,
# ERROR}
#
# Na pridanie nového testu teda stačí napísať príslušnú fciu s dekorátorom a docstringom, o ostatné
# sa starať netreba :)
#
# Workflow scriptu
# ----------------
#
# Najskôr beží `main`. Jej úlohou je sparsovať argumenty ktore boli scriptu dané. Na základe týchto
# argumentov spúšťa ostatné časti scriptu. Obvykle upraví zoznam testov ktoré majú bežať a spustí
# funkciu `execute`. Táto funkcia zoberie cesty k zadaniam, vstupom a vzorákom a spustí na nich
# funkcie `parse_{tasks,inputs,solutions}`. Tieto funkcie sa preiterujú súbormi so správnym menom, a
# na každom súbore spustia `parse_{task,input,solution}`. Tieto funkcie sparsujú už konkrétny súbor.
# Sú umiestnené v časti skriptu "PARSER" a určené na pravidelné menenie maintainerom testov pri
# zmene formátu súborov. Funkcie `parse_{task,input,solution}` vrátia objekty sparsovaných vecí
# funkciám `parse_{tasks,inputs,solutions}`. Tieto vrátia listy sparsovaných objektov funkcii
# `execute`. Táto funkcia z týchto dát postaví `test_data` dict, ktorý sa neskôr bude dávať
# jednotlivým testom. `execute` následne spustí funkciu `execute_tests` so zoznamom testov, dictom
# `test_data` a classou loggera ktorú maju testy používať. `execute_tests` následne spúšťa
# jednotlivé testy (pre každý vytvorí instanciu loggera s appropriate identifikátorom testu). Zoznam
# so štatistikami ohľadom behu testov vráti `execute`, ktorý vypíše finálne hlášky a vygeneruje
# vhodný return code.
#
# Čo týmto skriptom básnik myslel...
# ----------------------------------
#
# Alebo náhodné poznámky pre náhodných maintainerov.
#
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


class TestRegistrar():
    def __init__(self):
        self.all = {}

    def __call__(self, func):
        self.all[func.__name__] = {"doc": func.__doc__, "run": func}
        return func

test = TestRegistrar()


class TestResult(Enum):
    OK = 0
    SKIP = 1
    WARNING = 2
    ERROR = 3


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


@test
def taskComplete(logger, test_data):
    """Kontrola či úloha má meno a autora"""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    success = True
    for task in test_data["tasks"]:
        if not task.task_name:
            logger.logIssue(logging.ERROR, Issue("Úloha nemá meno!", task.task_filename))
            success = False
        if not task.task_author:
            logger.logIssue(logging.ERROR, Issue("Úloha nemá autora!", task.task_filename))
            success = False
    return TestResult.OK if success else TestResult.ERROR


@test
def taskProofreaded(logger, test_data):
    """Kontrola či je úloha sproofreadovaná"""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    success = True
    for task in test_data["tasks"]:
        if not task.task_proofreader:
            logger.logIssue(logging.WARNING, Issue("Úloha nie je sproofreadovaná!",
                            task.task_filename))
            success = False
    return TestResult.OK if success else TestResult.WARNING


@test
def taskFirstLetter(logger, test_data):
    """Kontrola prvého písmenka úlohy.

    Tento test zlyhá, ak úlohy v kategórií Z a O nezačínajú na správne písmenko."""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    config = []
    config += ['Z']*4  # Prvé 4 úlohy majú začínať Z-tkom
    config += ['O']*4  # Ďalšie 4 úlohy majú začínať O-čkom

    success = True
    for task in test_data["tasks"]:
        if not task.task_name.startswith(config[task.task_number-1]):
            logger.logIssue(logging.ERROR,
                            Issue(("Úloha \"{0}\" nezačína správnym písmenom ({1})!"
                                  .format(task.task_name, config[task.task_number-1])),
                                  task.task_filename))
            success = False
    return TestResult.OK if success else TestResult.ERROR


@test
def taskCorrectPoints(logger, test_data):
    """Kontrola správneho súčtu bodov.

    Tento test zlyhá ak úlohy nemajú správne súčty bodov. Správne súčty bodov sú 10 za príklady
    1-3, 15 za 4-5 a 20 za 6-8."""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    config = []
    config += [10]*3  # Úlohy 1-3 10b
    config += [15]*2  # Úlohy 4-5 15b
    config += [20]*3  # Úlohy 6-8 20b

    success = True
    for task in test_data["tasks"]:
        task_points = (task.task_points["bodypopis"] + task.task_points["bodyprogram"])
        if task_points != config[task.task_number-1]:
            logger.logIssue(logging.ERROR,
                            Issue(("Úloha \"{0}\" nemá spávny počet bodov! Má {1}, má mať {2}."
                                   .format(task.task_name, task_points,
                                           config[task.task_number-1])),
                                  task.task_filename))
            success = False
    return TestResult.OK if success else TestResult.ERROR


@test
def allTasksPresent(logger, test_data):
    """Kontrola či existuje všetkých 8 úloh."""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    tasks_exist = [False]*8

    for task in test_data["tasks"]:
        tasks_exist[task.task_number-1] = True

    for task_number, task_exists in enumerate(tasks_exist):
        if not task_exists:
            logger.logIssue(logging.ERROR,
                            Issue("Úloha číslo {0} neexistuje!".format(task_number+1), ""))

    return TestResult.OK if all(tasks_exist) else TestResult.ERROR


@test
def taskSamplesEndWithUnixNewline(logger, test_data):
    """Kontrola či všetky príklady vstupu / výstupu končia s UNIX newline."""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    success = True
    for task in test_data["tasks"]:
        lines = task.task_plaintext.splitlines(True)
        checking = False
        for index, line in enumerate(lines):
            if line.startswith('```vstup') or line.startswith('```vystup'):
                checking = True
                continue
            if line.startswith('```'):
                checking = False
                continue
            if checking and line.endswith('\r\n'):
                logger.logIssue(logging.ERROR, Issue("Riadok má Windowsácky endline!",
                                                     task.task_filename, index+1))
                success = False
    return TestResult.OK if success else TestResult.ERROR


@test
def taskSamplesWhitespace(logger, test_data):
    """Kontrola či príklady vstupu / výstupu nekončia medzerou."""
    if not test_data["tasks"]:
        logger.logMessage(logging.DEBUG, 'Nemám path k úloham, skippujem sa...')
        return TestResult.SKIP

    success = True
    for task in test_data["tasks"]:
        lines = task.task_plaintext.splitlines(True)
        checking = False
        for index, line in enumerate(lines):
            if line.startswith('```vstup') or line.startswith('```vystup'):
                checking = True
                continue
            if line.startswith('```'):
                checking = False
                continue
            if checking and re.match("[^ \t\r\f\v]*[ \t\r\f\v]+$", line):
                logger.logIssue(logging.ERROR, Issue("Riadok končí whitespace-om!",
                                                     task.task_filename, index+1))
                success = False
    return TestResult.OK if success else TestResult.ERROR


# -----------------------------------------------------------------------------

# --------------------------------- PARSER ------------------------------------


class Task():
    def __init__(self, task_filename=None, task_text=None):
        self.task_plaintext = task_text
        self.task_filename = task_filename

        self.task_name = None
        self.task_number = None
        self.task_points = {}
        self.task_author = None
        self.task_proofreader = None


def parse_task(logger, task_filename):
    # Binary read mode lebo zachovajme newlines
    task_file = open(task_filename, 'rb')
    task = Task(task_filename, task_file.read().decode("utf-8"))

    lines = task.task_plaintext.splitlines()

    # Vyparsujeme číslo príkladu
    fname = os.path.basename(task.task_filename)
    try:
        found_task_number = re.search('prikl([0-9]*)', fname).group(1)
        task.task_number = int(found_task_number)
    except (AttributeError, IndexError, ValueError):
        logger.logIssue(logging.ERROR, Issue("Súbor nemá platné číslo príkladu!", fname))
        return None

    # Vyparsujme meno príkladu
    try:
        # Regex ktoý chce matchnúť meno príkladu (po # a pred {} s bodmi)
        found_task_name = re.search('\.?#([^{}]*)', lines[0]).group(1)
        task.task_name = found_task_name.strip()
    except (AttributeError, IndexError):
        logger.logIssue(logging.WARNING, Issue("Nepodarilo sa zistiť meno príkladu!", fname))

    # Vyparsujeme body za príklad
    try:
        # Regex ktorý chce matchnúť čísleka s bodmi
        found_points = re.search('{bodypopis=([0-9]*) bodyprogram=([0-9]*)}', lines[0])
        task.task_points["bodypopis"] = int(found_points.group(1))
        task.task_points["bodyprogram"] = int(found_points.group(2))
    except (AttributeError, IndexError, ValueError):
        logger.logIssue(logging.WARNING, Issue("Nepodarilo sa zistiť body za príklad!", fname))

    for idx, line in enumerate(lines):
        # Vyparsujeme autora
        found_author = re.search('%by (.*)', line)
        if found_author:
            if task.task_author is not None:
                logger.warning('Úloha %s má údajne viac autorov!', task.task_filename)
            task.task_author = found_author.group(1)

        # Vyparsujeme proofreadera
        found_proofreader = re.search('%proofread (.*)', line)
        if found_proofreader:
            if task.task_proofreader is not None:
                logger.logIssue(logging.WARNING, Issue('Úloha má údajne viac proofreaderov!',
                                                       fname, idx+1))
            task.task_proofreader = found_proofreader.group(1)

    return task


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


def parse_tasks(IssueLogger, path_to_tasks):
    VALID_TASK_FILE_NAME = 'prikl*.md'
    tasks = []
    if not os.path.isdir(path_to_tasks):
        logger.critical("folder '%s' nenájdený alebo nie je folder!", path_to_tasks)
    for task_filename in glob.iglob(os.path.join(path_to_tasks, VALID_TASK_FILE_NAME)):
        if os.path.isfile(task_filename):
            logger.debug("Čítam zadanie %s", task_filename)
            task = parse_task(IssueLogger("checker.parser.task"), task_filename)
            if task is not None:
                tasks.append(task)
    return tasks


def parse_inputs(IssueLogger, path_to_inputs):
    pass


def parse_solutions(IssueLogger, path_to_solutions):
    pass


def execute_tests(tests, test_data, logger_class):
    results = {TestResult.SKIP: 0,
               TestResult.OK: 0,
               TestResult.WARNING: 0,
               TestResult.ERROR: 0}

    for test_name, test in tests.items():
        logger.debug("Spúšťam test %s", test_name)

        # deepcopy lebo nechceme aby prišiel niekto, v teste zmenil test_data a tak rozbil všetky
        # ostatné testy
        status = test["run"](logger_class('checker.' + test_name), copy.deepcopy(test_data))
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

    if args.path_to_tasks:
        logger.debug("Spúšťam testy na zadaniach z '%s'", args.path_to_tasks[0])
        tasks = parse_tasks(ConsoleIssueLogger, args.path_to_tasks[0])

    if args.path_to_inputs:
        logger.debug("Spúšťam testy na vstupoch z '%s'", args.path_to_inputs[0])
        inputs = parse_inputs(ConsoleIssueLogger, args.path_to_inputs[0])

    if args.path_to_solutions:
        logger.debug("Spúšťam testy na vzorákoch z '%s'", args.path_to_solutions[0])
        solutions = parse_solutions(ConsoleIssueLogger, args.path_to_solutions[0])

    test_data = {"path_to_tasks": args.path_to_tasks[0] if args.path_to_tasks is not None else None,
                 "path_to_solutions": (args.path_to_solutions[0]
                                       if args.path_to_solutions is not None else None),
                 "path_to_inputs": (args.path_to_inputs[0]
                                    if args.path_to_inputs is not None else None),
                 "tasks": tasks,
                 "solutions": solutions,
                 "inputs": inputs}

    results = execute_tests(tests, test_data, ConsoleIssueLogger)

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
