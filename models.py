import os
import re
import logging

from issue_utils import Issue, IssueLogger


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

    @staticmethod
    def parse(logger, task_filename):
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


class Solution():
    def __init__(self, solution_filename=None, solution_text=None):
        self.plaintext = solution_text
        self.filename = solution_filename

        self.name = None
        self.number = None
        self.points = {}
        self.author = None

        self.bypass = []

    @staticmethod
    def parse(logger, solution_filename):
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
            found = re.search('{vzorak="([^"]*)" bodypopis=([0-9]*) bodyprogram=([0-9]*)}',
                              lines[0])
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
