'''This module loads all the test custom packages.'''
import os
import sys

# Include the project package into the system path to allow import
package_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, package_path)

from lib import util

util.add_python_packages('{0}'.format(package_path))
util.add_python_packages('{0}/packages'.format(package_path))

import argparse
from pexpect.exceptions import TIMEOUT
