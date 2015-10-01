#!/usr/bin/env python3

# Pre dokumentáciu viď readme

import logging
import argparse
import sys
import os
import re
import copy
import glob
import functools
import subprocess
import tempfile
import py_compile

from test_utils import test, for_each_item_in, TestResult
from issue_utils import Issue, IssueLogger
import tests
from models import *

logger = logging.getLogger('checker')
logger.setLevel(logging.WARNING)
formatter = logging.Formatter('Kontrola zadaní - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler(sys.stderr)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


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
                thing = Task.parse(IssueLogger("checker.parser.task"), filename)
            elif what == "solutions":
                thing = Solution.parse(IssueLogger("checker.parser.solution"), filename)

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
