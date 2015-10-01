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
