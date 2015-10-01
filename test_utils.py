import functools
import logging
from enum import Enum

logger = logging.getLogger('checker')


class TestResult(Enum):
    OK = 0
    SKIP = 1
    WARNING = 2
    ERROR = 3


class TestRegistrar():
    def __init__(self):
        self.all = {}

    def __call__(self, severity, require=[], ignore=False):
        def registrar_decorator(func):
            def wrapper(logger, test_data):
                # Otestujeme či test má všetko potrebné pre svoj beh
                for requirement in require:
                    if requirement not in test_data.keys() or not test_data[requirement]:
                        logger.logMessage(logging.DEBUG, 'Nemám potrebné veci, skippupjem sa...')
                        return TestResult.SKIP

                # Spustíme test
                status = func(logger, test_data)

                # Ak funkcia vráti boolean miesto TestResult, vráťme hodnotu parametra severity pri
                # zlyhaní.
                if not isinstance(status, TestResult):
                    return severity if not status else TestResult.OK
                else:
                    return status

            if not ignore:
                self.all[func.__name__] = {"doc": func.__doc__, "run": wrapper}
            return wrapper
        return registrar_decorator

test = TestRegistrar()


def for_each_item_in(items, bypassable=False):
    def foreach_decorator(function):
        @functools.wraps(function)
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
        return wrapper
    return foreach_decorator
