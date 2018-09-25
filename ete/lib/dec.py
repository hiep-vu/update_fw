'''dec.py

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python
      2.7 or later.
'''
import decorator
import logging
import os
import sys
import time


log = logging.getLogger(__name__)


def whoami():
    '''Return the current def name.'''
    return sys._getframe(1).f_code.co_name


@decorator.decorator
def time_elapsed(f, *args, **kwargs):
    '''Timer decorator for time elapsed counter.

    Preserving signatures of decorated functions
    Reference: http://stackoverflow.com/questions/147816/preserving-signatures-of-decorated-functions
    
    :param - stdout (print to stdout)
    '''
    print('>>> {}'.format(f.__name__))
    log.debug('>>> {}'.format(f.__name__))
    args = [x for x in args]
    kwargs = dict((k, v) for k, v in kwargs.items())
    start_time = time.time()
    status = f(*args, **kwargs)
    timer = time.time() - start_time

    log.debug('<<< {} finished in {:.2f} seconds'.format(f.__name__, timer))
    print('<<< {} finished in {:.2f} seconds'.format(f.__name__, timer))
    return status


@decorator.decorator
def state_machine(f, *args, **kwargs):
    args = [x for x in args]
    kwargs = dict((k, v) for k, v in kwargs.items())
    status = f(*args, **kwargs)
    return status

