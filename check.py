#!/usr/bin/env python3

# Skript ktorý sa spúšťa pri kompilácií zadaní a robí im sanity checking.
#
# Čo týmto skriptom básnik myslel...
# ----------------------------------
#
# Alebo náhodné poznámky pre náhodných maintainerov.
#
#  - Dodržujte PEP-8
#  - Snažte sa o konzistentný coding style
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

if __name__ == "__main__":
    sys.exit(main())
