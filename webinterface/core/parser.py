import string

class Parser:
    @staticmethod
    def _is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    @staticmethod
    def parse_single(s):
        if s is "":
            return None
        if Parser._is_number(s):
            return float(s)
        else:
            return s

    @staticmethod
    def parse(s):
        s = s.lstrip()
        while s.replace("  ", " ") is not s:
            s = s.replace("  ", " ")
        s = s.replace(", ", ",").replace(" ,", ",").replace("[ ","[").replace(" ]", "]")
        parts = s.split(" ")
        l = []
        for element in parts:
            l.append(Parser._parseRecursive(element))
        return l

    @staticmethod
    def _parseRecursive(s):
        if s is "":
            return None
        if Parser._is_number(s):
            return float(s)
        elif s[0] is "[":
            return Parser._parseList(s)
        else:
            return s

    @staticmethod
    def _parseList(s):
        parts = Parser._splitList(s)
        parsed = []
        for element in parts:
            parsed.append(Parser._parseRecursive(element))
        return parsed

    @staticmethod
    def _splitList(s):
        parts = []
        count = 0
        lastindex = 1
        for i, c in enumerate(s):
            if c is "[":
                count += 1
            elif c is "]":
                count -= 1
            if c is ",":
                if count is 1:
                    parts.append(s[lastindex:i])
                    lastindex = i+1
            if count is 0:
                parts.append(s[lastindex:i]) #add last element
                return parts
        return parts
