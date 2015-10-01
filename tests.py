import tempfile
import subprocess
import py_compile

from test_utils import test, for_each_item_in, TestResult
from models import *


@test(TestResult.ERROR, require=["tasks"])
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


@test(TestResult.ERROR, require=["tasks"])
@for_each_item_in("tasks")
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


@test(TestResult.WARNING, require=["tasks"])
@for_each_item_in("tasks", bypassable=True)
def taskProofreaded(logger, task):
    """Kontrola či je úloha sproofreadovaná"""

    if not task.proofreader:
        logger.logIssue(logging.WARNING, Issue("Úloha nie je sproofreadovaná!", task.filename))
        return False
    return True


@test(TestResult.ERROR, require=["tasks"])
@for_each_item_in("tasks", bypassable=True)
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


@test(TestResult.ERROR, require=["tasks"])
@for_each_item_in("tasks", bypassable=True)
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


@test(TestResult.ERROR, require=["tasks"])
@for_each_item_in("tasks", bypassable=True)
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


@test(TestResult.ERROR, require=["tasks"])
@for_each_item_in("tasks", bypassable=True)
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


@test(TestResult.WARNING, require=["solutions"])
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


@test(TestResult.ERROR, require=["solutions"])
@for_each_item_in("solutions")
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


@test(TestResult.ERROR, require=["tasks", "solutions"])
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


@test(TestResult.ERROR, require=["solutions"])
@for_each_item_in("solutions")
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


@test(TestResult.WARNING, require=["solutions"])
@for_each_item_in("solutions", bypassable=True)
def solutionAllListingsCompileable(logger, solution):
    """Kontrola či sú všetky listingy skompilovateľné.

    Kontroluje všetky listingy s príponami .cc, .c++, .cpp, .py, .pas tak, že sa ich pokúsi
    skompilovať. Ak sa nenájde príslušný compiler skippne sa checkovanie daného listingu."""

    success = True
    for idx, line in enumerate(solution.plaintext.splitlines()):
        # Matchne '\listing{...}'
        match = re.match('\\\\listing{([^}]*)}', line)

        devnull = open(os.devnull, 'w')

        if match:
            temp_directory = tempfile.TemporaryDirectory()
            listing_filename = os.path.join(os.path.dirname(solution.filename), match.group(1))
            if os.path.isfile(listing_filename):

                if (listing_filename.endswith('.cpp') or listing_filename.endswith('.cc') or
                   listing_filename.endswith('.c++')):
                    try:
                        subprocess.check_call(['g++', '-v'], stdout=devnull, stderr=devnull)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        logger.logMessage(logging.INFO,
                                          ("g++ nenájdené, skippujem checkovanie listingu {0}"
                                           .format(listing_filename)))
                        temp_directory.cleanup()
                        continue

                    try:
                        subprocess.check_output(['g++', '-std=c++11', '-fdiagnostics-color=never',
                                                 listing_filename, '-o',
                                                 os.path.join(temp_directory.name, 'test.out')],
                                                stderr=subprocess.STDOUT)
                    except subprocess.CalledProcessError as e:
                        logger.logIssue(logging.WARNING,
                                        Issue(("Listing {0} nejde skompilovať!\n{1}"
                                               .format(listing_filename, e.output.decode('utf-8'))),
                                              solution.filename, idx+1))

                elif listing_filename.endswith('.pas'):
                    try:
                        subprocess.check_call(['fpc', '-h'], stdout=devnull, stderr=devnull)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        logger.logMessage(logging.INFO,
                                          ("fpc nenájdené, skippujem checkovanie listingu {0}"
                                           .format(listing_filename)))
                        temp_directory.cleanup()
                        continue

                    try:
                        subprocess.check_output(['fpc', '-FE' + temp_directory.name,
                                                 listing_filename], stderr=subprocess.STDOUT)
                    except subprocess.CalledProcessError as e:
                        logger.logIssue(logging.WARNING,
                                        Issue(("Listing {0} nejde skompilovať!\n{1}"
                                               .format(listing_filename, e.output.decode('utf-8'))),
                                              solution.filename, idx+1))

                elif listing_filename.endswith('.py'):
                    try:
                        py_compile.compile(listing_filename,
                                           cfile=os.path.join(temp_directory.name, "out.pyc"),
                                           doraise=True)
                    except py_compile.PyCompileError:
                        logger.logIssue(logging.WARNING,
                                        Issue(("Listing {0} nejde skompilovať!\n{1}"
                                               .format(listing_filename, e.output.decode('utf-8'))),
                                              solution.filename, idx+1))

            temp_directory.cleanup()
    return success


@test(TestResult.WARNING, require=["tasks", "inputs"])
def taskHasInputs(logger, test_data):
    """Kontrola či každá úloha má vstupy."""

    success = True
    for task in test_data["tasks"]:
        if not test_data["inputs"][task.number-1]:
            logger.logIssue(logging.WARNING, Issue("Úloha nemá vstupy!", task.filename))
            success = False
    return success


@test(TestResult.ERROR, require=["inputs"])
@for_each_item_in("inputs")
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


@test(TestResult.WARNING, require=["inputs"])
@for_each_item_in("inputs")
def inputsNoTrailingWhitespace(logger, tests):
    """Kontrola či vstupy a výstupy nemajú medzery na konci riadkov."""

    success = True
    for inp, inp_filename in tests.items():
        inp_file = open(inp_filename, 'r')
        line_number = 1
        for line in inp_file:
            if line.rstrip() + '\n' != line:
                logger.logIssue(logging.WARNING,
                                Issue("Vstup má na konci riadku whitespaces!", inp_filename,
                                      line_number))
                success = False
            line_number += 1
        inp_file.close()
    return success


@test(TestResult.ERROR, require=["inputs"])
@for_each_item_in("inputs")
def eachInputHasOutput(logger, tests):
    """Kontrola či každý .in súbor zo vstupov má prislúchajúci .out súbor"""

    for inp, inp_filename in tests.items():
        if inp.endswith('.in') and inp[:-3]+'.out' not in tests.keys():
            logger.logIssue(logging.ERROR, Issue("Vstup nemá výstup!", inp_filename))
            return False
    return True


@test(TestResult.ERROR, require=["inputs"])
@for_each_item_in("inputs")
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
