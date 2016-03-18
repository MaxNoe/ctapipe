'''
This module provides a streaming implementation of
data containers

The following classes are provided:

- Pipeline a class describing the data flow
- Source to read or create data
- Operator receives data, calculates something and returns the modified data
'''

import sys
import logging
import time


class NextEvent(Exception):
    pass


class Pipeline():

    def __init__(self, source, operators):

        self.source = source
        self.operators = operators

        for operator in operators:
            logging.debug('Using operator {}'.format(operator))

    def run(self):
        for event in self.source:

            try:
                for operator in self.operators:

                    try:
                        event = operator(event)
                    except (KeyboardInterrupt, SystemExit):
                        sys.exit(0)
                    except NextEvent:
                        raise
                    except Exception:
                        logging.exception('Error using Operator ' + str(operator))
                        continue

            except NextEvent:
                continue


class Source():
    def __iter__(self):
        raise NotImplemented


class Operator():

    def __call__(self, event):
        raise NotImplemented()

    def __repr__(self):
        return self.__class__.__name__ + '()'


class Delay(Operator):

    def __init__(self, delay=1):
        self.delay = delay

    def __call__(self, event):
        time.sleep(self.delay)
        return event

    def __repr__(self):
        return self.__class__.__name__ + '(delay={})'.format(self.delay)


class Print(Operator):

    def __init__(self, key=None):
        self.key = key

    def __call__(self, event):
        if self.key is None:
            print(event)
        else:
            print(event[self.key])
        return event


class Filter(Operator):

    def __init__(self, filter):
        self.filter = filter

    def __call__(self, event):

        if not self.filter(event):
            raise NextEvent('Filter')

        return event

    def __repr__(self):
        return self.__class__.__name__ + '(filter={})'.format(self.filter)


class DummySource():
    def __iter__(self):
        for i in range(10):
            yield i
