#!/usr/bin/env python3

# Skript ktorý sa spúšťa pri kompilácií zadaní a robí im sanity checking.
#
# Po spustení tento skript najskôr zoberie veci na check a sparsuje ich. To sa
# robí mimo testov lebo ak by sa zmenil formát súborov nech netreba všetky
# testy prepísať. Potom sa spustia jednotlivé testy, ktoré dostanú path k
# zadaniam (ak chcú checkovať súborovú štruktúru, filenames...), plaintexty
# zadaní (ak chcú checkovať newlines, trailing whitespace...) a sparsované
# zadania (ak chcú checkovať počty bodov, správnosť názvov úloh...)
#
# Test
# ----
#
# Test je obyčajná funkcia v sekcii skriptu "TESTY", ktorá je dekorovaná
# @test dekorátorom. Meno tejto funkcie je názov testu (bude sa používať v
# argumentoch, ako chybová hláška keď test zlyhá a tak.) Test musí obsahovať
# neprázdny docstring ktorý v prvom riadku pár slovami popíše čo test robí a
# v ostatných riadkoch (indentovaných 4mi medzerami) optionally test popíše
# detailnejšie.
#
# Na pridanie nového testu teda stačí napísať príslušnú fciu s dekorátorom a
# docstringom, o ostatné sa starať netreba :)
#
# Čo týmto skriptom básnik myslel...
# ----------------------------------
#
# Alebo náhodné poznámky pre náhodných maintainerov.
#
#  - Dodržujte PEP-8
#  - Snažte sa o konzistentný coding style
#  - Nakoľko sa meno fcie testu používa v chybovej hláške o zlyhaní a tak,
#    mená majú dávať zmysel (prosím, žiadne T_PAAMAYIM_NEKUDOTAYIM ;) )
#  - Unix-like: "No news are good news"
#    Nevypisujte hlúposti ak nie ste verbose.
#  - Tento script je zatiaľ iba v zadaniach kde sa môže správať ako chce.
#    Eventuálne ale bude jeden build step keď sa budú automaticky v CI buildiť
#    zadania, preto je napísaný tak ako je.

import logging
import argparse
import sys
import os

logger = logging.getLogger('checker')
logger.setLevel(logging.WARNING)
formatter = logging.Formatter('Kontrola zadaní - %(name)s - %(levelname)s - ' +
                              ' %(message)s')
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

# --------------------------------- PARSER ------------------------------------


class Task():
    def parse(self):
        logger = logging.getLogger('checker.parser')
        logger.debug("Parsujem zadanie")

    def __init__(self, task_text=None):
        self.task_plaintext = task_text

        if self.task_plaintext is not None:
            self.parse()

        self.task_name = None
        self.task_points = {}
        self.task_author = None
        self.task_proofread = None
        pass


# -----------------------------------------------------------------------------

# ---------------------------------- TESTY ------------------------------------


@test
def dummyTest1():
    """Test testu 1.

    Tento test testuje schopnosť pridávania testov pomocou dekorátorov.
    A toto je dlhááá dokumentáci ak nemu."""
    pass


@test
def dummyTest2():
    """Hlúpy ničohoneschopný test na pokus 2"""
    pass


# -----------------------------------------------------------------------------


def print_tests():
    for tst_name, tst in test.all.items():
        print(tst_name, " - ", tst['doc'])
        print()


def execute(args, tests):
    logger.debug("Spustím tieto testy: %s", str(tests.keys()))
    if args.path_to_tasks:
        # Bola nám daná cesta k zadaniam, dajme ju testom. Ale najskôr tieto
        # zadania loadnime a sparsujme
        logger.debug("Spúšťam testy na zadaniach z '%s'",
                     args.path_to_tasks[0])
        tasks = []
        if not os.path.isdir(args.path_to_tasks[0]):
            logger.critical("folder '%s' nenájdený alebo nie je folder!",
                            args.path_to_tasks[0])
        for task_filename in os.listdir(args.path_to_tasks[0]):
            task_filename = os.path.join(args.path_to_tasks[0], task_filename)
            if not os.path.isdir(task_filename):
                logger.debug("Čítam zadanie %s", task_filename)
                task_file = open(task_filename, 'r')
                tasks.append(Task(task_file.read()))


def main():
    argumentParser = argparse.ArgumentParser(description="Checker KSP zadaní")
    argumentParser.add_argument('--tasks', nargs=1, dest='path_to_tasks',
                                help="Cesta k foldru so zadaniamu")
    argumentParser.add_argument('--inputs', nargs=1,
                                dest="path_to_inputs",
                                help="Cesta k foldru so vstupmi")
    argumentParser.add_argument('--solutions', nargs=1,
                                dest="path_to_solutions",
                                help="Cesta k foldru so vzorákmi")
    argumentParser.add_argument('-p', '--print-tests', action="store_true",
                                dest="print_only",
                                help="Iba vypíš aké testy poznáš a skonči")
    argumentParser.add_argument('--strict', action="store_true", dest="strict",
                                help="Správaj sa k warningom ako k chybám")
    argumentParser.add_argument('-s', '--skip', nargs='*', dest="skip",
                                metavar="test", help="Preskoč tieto testy")
    argumentParser.add_argument('-r', '--run-only', nargs='*', dest="runonly",
                                metavar="test", help="spusti IBA tieto " +
                                "testy. Overridne --skip")
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
                logger.critical("Bol requestnutý beh testu " + tst_name +
                                ", ale ten neexistuje.")
                return 1
            tests_to_run[tst_name] = test.all[tst_name]
        return execute(args, tests_to_run)

    if args.skip:
        # Ak nejaký test neexistuje a chceme ho skipnúť je to asi chyba / typo
        # a test čo nemá by bežal. Umrime radšej.
        tests_to_run = dict(test.all)
        for tst_name in args.skip:
            if tst_name not in test.all:
                logger.critical("Bolo requestnuté skipnutie testu " +
                                tst_name + ", ale tento neexistuje.")
                return 1
            del tests_to_run[tst_name]
        return execute(args, tests_to_run)

    return execute(args, dict(test.all))

if __name__ == "__main__":
    sys.exit(main())
