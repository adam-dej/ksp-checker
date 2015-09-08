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
    def logMessage(self, severity, message):
        pass

    def logIssue(self, severity, Issue):
        pass

# ---------------------------------- TESTY ------------------------------------


@test
def taskComplete(logger, test_data):
    """Kontrola či úloha má meno a autora"""
    if not test_data["tasks"]:
        logger.logMessage(logging.INFO, 'Nemám path k úloham, skippujem sa...')
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
        logger.logMessage(logging.INFO, 'Nemám path k úloham, skippujem sa...')
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
        logger.logMessage(logging.INFO, 'Nemám path k úloham, skippujem sa...')
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
        logger.logMessage(logging.INFO, 'Nemám path k úloham, skippujem sa...')
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

# -----------------------------------------------------------------------------

# --------------------------------- PARSER ------------------------------------


class Task():
    def parse(self):
        logger = logging.getLogger('checker.parser')
        lines = self.task_plaintext.split('\n')

        # Vyparsujeme číslo príkladu
        fname = os.path.basename(self.task_filename)
        try:
            found_task_number = re.search('prikl([0-9]*)', fname).group(1)
            self.task_number = int(found_task_number)
        except (AttributeError, IndexError, ValueError):
            logger.error('Súbor %s nie je valídne meno príkladu!', self.task_filename)

        # Vyparsujme meno príkladu
        try:
            # Regex ktoý chce matchnúť meno príkladu (po # a pred {} s bodmi)
            found_task_name = re.search('\.?#([^{}]*)', lines[0]).group(1)
            self.task_name = found_task_name.strip()
            logger.debug('Vyparsované meno príkladu (%s) z %s', self.task_name, self.task_filename)
        except (AttributeError, IndexError):
            logger.warning('Nepodarilo sa vyparsovať meno príkladu z %s', self.task_filename)

        # Vyparsujeme body za príklad
        try:
            # Regex ktorý chce matchnúť čísleka s bodmi
            found_points = re.search('{bodypopis=([0-9]*) bodyprogram=([0-9]*)}', lines[0])
            self.task_points["bodypopis"] = int(found_points.group(1))
            self.task_points["bodyprogram"] = int(found_points.group(2))
            logger.debug('Vyparsované body (%s) z príkladu %s', self.task_points,
                         self.task_filename)
        except (AttributeError, IndexError, ValueError):
            logger.warning('Nepodarilo sa vyprasovať body z príkladu %s', self.task_filename)

        for line in lines:
            # Vyparsujeme autora
            found_author = re.search('%by (.*)', line)
            if found_author:
                if self.task_author is not None:
                    logger.warning('Úloha %s má údajne viac autorov!', self.task_filename)
                self.task_author = found_author.group(1)
                logger.debug('Nájdený autor (%s) úlohy %s', self.task_author, self.task_filename)

            # Vyparsujeme proofreadera
            found_proofreader = re.search('%proofread (.*)', line)
            if found_proofreader:
                if self.task_proofreader is not None:
                    logger.warning('Úloha %s má údajne viac proofreaderov!', self.task_filename)
                self.task_proofreader = found_proofreader.group(1)
                logger.debug('Nájdený proofreader (%s) úlohy %s', self.task_proofreader,
                             self.task_filename)

    def __init__(self, task_filename=None, task_text=None):
        self.task_plaintext = task_text
        self.task_filename = task_filename

        self.task_name = None
        self.task_number = None
        self.task_points = {}
        self.task_author = None
        self.task_proofreader = None

        if self.task_plaintext is not None:
            self.parse()

        pass


# -----------------------------------------------------------------------------


def print_tests():
    for tst_name, tst in test.all.items():
        print(tst_name, " - ", tst['doc'])
        print()


def execute(args, tests):
    logger.debug("Spustím tieto testy: %s", tests.keys())
    tasks = []

    if args.path_to_tasks:
        # Bola nám daná cesta k zadaniam, dajme ju testom. Ale najskôr tieto
        # zadania loadnime a sparsujme
        logger.debug("Spúšťam testy na zadaniach z '%s'", args.path_to_tasks[0])
        if not os.path.isdir(args.path_to_tasks[0]):
            logger.critical("folder '%s' nenájdený alebo nie je folder!", args.path_to_tasks[0])
        for task_filename in os.listdir(args.path_to_tasks[0]):
            task_filename = os.path.join(args.path_to_tasks[0], task_filename)
            if os.path.isfile(task_filename):
                logger.debug("Čítam zadanie %s", task_filename)
                task_file = open(task_filename, 'r')
                tasks.append(Task(task_filename, task_file.read()))

    # TODO okrem iného chceme loadnuť a sparsovať vstupy a vzoráky ešte

    results = {TestResult.SKIP: 0,
               TestResult.OK: 0,
               TestResult.WARNING: 0,
               TestResult.ERROR: 0}

    # Spustime testy
    for test_name, test in tests.items():
        logger.debug("Spúšťam test %s", test_name)
        # TODO add test data for solutions and inputs
        test_data = {"path_to_tasks": args.path_to_tasks,
                     "tasks": tasks}

        # Implementácia IssueLoggera
        class ConsoleIssueLogger(IssueLogger):
            def __init__(self, logger_name):
                self.logger = logging.getLogger(logger_name)

            def logMessage(self, severity, message):
                self.logger.log(severity, message)

            def logIssue(self, severity, issue):
                if issue.line:
                    self.logger.log(severity, "File %s, line %i: %s",
                                    issue.file, issue.line, issue.message)
                else:
                    self.logger.log(severity, "File %s: %s",
                                    issue.file, issue.message)

        # deepcopy lebo nechceme aby prišiel niekto, v teste zmenil test_data
        # a tak rozbil všetky ostatné
        status = test["run"](ConsoleIssueLogger('checker.' + test_name), copy.deepcopy(test_data))
        results[status] += 1

        if status == TestResult.ERROR:
            logger.error("Test %s ZLYHAL!", test_name)
        elif status == TestResult.WARNING:
            logger.warning("Test %s skončil s varovaním!", test_name)
        elif status == TestResult.OK:
            logger.info("Test %s je ok.", test_name)
        elif status == TestResult.SKIP:
            logger.debug("Test %s skippol sám seba", test_name)

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
