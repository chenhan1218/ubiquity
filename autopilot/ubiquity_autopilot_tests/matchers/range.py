class InRange(object):

    def __init__(self, start, end):
        self.range_start = start
        self.range_end = end

    def __str__(self):
        return 'InRange(%r, %r)' % (
            self.range_start, self.range_end)

    def match(self, actual):
        if actual in range(self.range_start, self.range_end):
            return None
        else:
            return InRangeMismatch(
                actual, self.range_start, self.range_end)


class InRangeMismatch(object):

    def __init__(self, actual, start, end):
        self.actual = actual
        self.range_start = start
        self.range_end = end

    def describe(self):
        return "%r is not in range %r - %r" % (
            self.actual, self.range_start, self.range_end)

    def get_details(self):
        return {}
