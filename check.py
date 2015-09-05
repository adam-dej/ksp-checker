#!/usr/bin/env python3

# Skript ktorý sa spúšťa pri kompilácií zadaní a robí im sanity checking.
#
# Tento skript by default spustí všetky testy ktoré pozná (overridnuteľné
# flagmi).
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

logger = logging.getLogger('check')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - ' +
                              ' %(message)s')


def makeTestRegistrar():
    tests = {}

    def testRegistrar(func):
        tests[func.__name__] = {"doc": func.__doc__, "run": func}
        return func
    testRegistrar.all = tests
    return testRegistrar

test = makeTestRegistrar()


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
    for tst in test.all:
        print(tst, " - ", test.all[tst]['doc'])
        print()


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
    argumentParser.add_argument('-e', '--enforce', nargs='*', dest="enforce",
                                metavar="test", help="Nezávisle od configu " +
                                "spusti tieto testy. Overridne --skip.")
    argumentParser.add_argument('-r', '--run-only', nargs='*', dest="runonly",
                                metavar="test", help="Nezávisle od configu " +
                                "spusti IBA tieto testy. Overridne --skip aj" +
                                " --enforce")
    argumentParser.add_argument('-v', action="count", dest="verbosity",
                                help="Viac sa vykecávaj (-vv kecá ešte viac)")
    args = argumentParser.parse_args()

    if args.print_only:
        print_tests()
        return 0

    return 0

if __name__ == "__main__":
    sys.exit(main())
