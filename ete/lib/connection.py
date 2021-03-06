'''This class inherits from pexpect with enhancements for our specific use.

Please refer to the following link for source code,

https://github.com/pexpect/pexpect

Please refer to the following link for documentation,

https://pexpect.readthedocs.io/en/stable/

'''
import datetime
import os
import re
import sys

from pexpect import pxssh, run
from pexpect.exceptions import ExceptionPexpect, TIMEOUT
from pexpect.pxssh import ExceptionPxssh

PY3 = (sys.version_info[0] >= 3)
text_type = str if PY3 else unicode


class Connection(pxssh.pxssh):
    def __init__(
        self, timeout=30, maxread=2000, searchwindowsize=None,
        logfile=None, cwd=None, env=None, ignore_sighup=True, echo=True,
        options={}, encoding=None, codec_errors='strict', static_logpath=None,
        verbose=None,
    ):
        '''
        '''
        super(Connection, self).__init__(
            timeout=timeout, maxread=maxread,
            searchwindowsize=searchwindowsize, logfile=logfile, cwd=cwd,
            env=env, ignore_sighup=ignore_sighup, echo=echo, options=options,
            encoding=encoding, codec_errors=codec_errors,
        )
        # Create a static logfile path with set location for logs to be stored
        self._static_logfile = None
        if static_logpath:
            # Expand the home directory path if ~ is used
            if '~' in static_logpath:
                static_logpath = os.path.expanduser(static_logpath)
            if not os.path.exists(static_logpath):
                os.makedirs(static_logpath)
            self._static_logfile = self.get_file_name_path(static_logpath)

        self.verbose = verbose
        self.full_buffer = None
        self.output = None
        self.logfile_read = logfile
        self.logfile = None

    def _log(self, s, direction):
        '''Write read output from the connection to a static file.

        Write read output from the connection to a static file if static
        logpath is define.  The file name is generated by get_file_name_path()
        function.  The purpose for _static_logfile is to keep a timestamped log
        independent from the logfile user specified.
        '''
        super(Connection, self)._log(s, direction)
        if self._static_logfile and direction == 'read':
            with open(self._static_logfile, 'ab') as static_logfile:
                static_logfile.write(s)
                static_logfile.flush()

    def _get_prompt(self, partial_prompt):
        '''Get the prompt of the connected system.'''
        self.send('\r', partial_prompt, timeout=3, attempt=3, regex=True)
        return self.full_buffer.strip()

    def get_file_name_path(self, logpath, timestamp='', header='connection', extension='log'):
        '''Helper function to create a file name path with timestamp.

        Helper function to create a file name path with timestamp to save
        debug info like screen shots.  No file is created only the path is
        assembled here.
        '''
        if not timestamp:
            timestamp = datetime.datetime.now().isoformat().replace(':', '').replace('-', '').replace('.', '')
        file_name = '{timestamp}_{header}.{extension}'.format(header=header, timestamp=timestamp, extension=extension)
        full_path = os.path.join(logpath, file_name)
        return full_path
        
    def login(
        self, server, username, password='', terminal_type='ansi',
        original_prompt=r'[#$]', login_timeout=10, port=None,
        auto_prompt_reset=True, ssh_key=None, quiet=True,
        sync_multiplier=1, check_local_ip=True, 
        password_regex=r'(?i)(?:password:)|(?:passphrase for key)',
        ssh_tunnels={}, spawn_local_ssh=True,
        sync_original_prompt=True, ssh_config=None,
        remove_known_hosts=False, ping_before_connect=True, attempt=3,
    ):
        '''Overrides login from parent class, add to find the prompt after the
        ssh connection is established if auto_prompt_reset is set to False.
        Otherwise, login() function set the ssh prompt to '[PEXPECT]$' by
        default.
        '''
        is_logged_in = False
        
        # Retry specified attempts before raising exception
        for i in xrange(attempt):
            output = ''
            pattern = ''
            if ping_before_connect:
                # Set ping command and expected pattern
                cmd = 'ping -c4 {}'.format(server)
                pattern = '4 received'
                if self.verbose:
                    if i == 0:
                        print('{}/{} attempt :\t"{}"\tpattern="{}"'.format(i + 1, attempt, cmd.strip(), pattern))
                    else:
                        print('{}/{} attempts:\t"{}"\tpattern="{}"'.format(i + 1, attempt, cmd.strip(), pattern))
                output = run(cmd, timeout=10)

            # Ping to make sure host is reachable before establish ssh connection
            if pattern in output:
                if remove_known_hosts:
                    run('rm {}'.format(os.path.expanduser('~/.ssh/known_hosts')), timeout=5)
                try:
                    is_logged_in = super(Connection, self).login(
                        server, username, password=password, terminal_type=terminal_type,
                        original_prompt=original_prompt, login_timeout=login_timeout, port=port,
                        auto_prompt_reset=auto_prompt_reset, ssh_key=ssh_key, quiet=quiet,
                        sync_multiplier=sync_multiplier, check_local_ip=check_local_ip,
                        password_regex=password_regex,
                        ssh_tunnels=ssh_tunnels, spawn_local_ssh=spawn_local_ssh,
                        sync_original_prompt=sync_original_prompt,
                    )
                    # Get prompt upon login and set it as default prompt
                    self.PROMPT = self._get_prompt(original_prompt)
                except:
                    if i + 1 >= attempt:
                        if self.verbose:
                            print('Unable to reach host {}, make sure host is reachable!'.format(server))
                        raise pxssh.ExceptionPxssh('Unable to reach host {}, make sure host is reachable!'.format(server))
                    continue
                break
            else:
                if i + 1 >= attempt:
                    if self.verbose:
                        print('Unable to reach host {}, make sure host is reachable!'.format(server))
                    raise pxssh.ExceptionPxssh('Unable to reach host {}, make sure host is reachable!'.format(server))
        return is_logged_in
        
    def send(self, s, pattern=[], timeout=-1, attempt=1, regex=False, verbose=False):
        '''Overrides send from parent class, added ability to include expected
        patterns, expected timeout, retry attempts, and matching with/without
        regular expressions.

        In addition to the class variables pexpect sets,

            self.before
            self.after
            self.match
            self.match_index
            self.buffer

        this function returns additional variables,

            self.full_buffer - full buffer of the command including the command
                               and the prompt
            self.output - output from the command excluding the command and the
                          prompt

        :param - s
        :param - pattern (default [])
        :param - timeout (default -1, when set to -1, it uses class default of
                 30s)
        :param - attempt (default 1)
        :param - regex (default True)
        :return - match index from pattern list (returns None if no match)
        '''
        self.before = None
        self.after = None
        self.match = None
        self.match_index = None
        self.buffer = bytes() if self.encoding is None else text_type()
        self.full_buffer = None
        self.output = None

        if attempt < 1:
            attempt = 1

        # Retry specified attempts before raising exception
        for i in xrange(attempt):
            if self.verbose:
                if i == 0:
                    print('{}/{} attempt :\t"{}"\tpattern="{}"'.format(i + 1, attempt, s.strip(), pattern))
                else:
                    print('{}/{} attempts:\t"{}"\tpattern="{}"'.format(i + 1, attempt, s.strip(), pattern))
            super(Connection, self).send(s)
            if pattern:
                try:
                    if regex:
                        super(Connection, self).expect(pattern, timeout=timeout)
                    else:
                        super(Connection, self).expect_exact(pattern, timeout=timeout)
                    self.full_buffer = self.before + self.after + self.buffer

                    # Get output from the command sent, stripping the command and the prompt.
                    self.output = self.full_buffer.replace(self.PROMPT, '').strip()
                    if verbose:
                        print('s "{}"'.format(s))
                        print('1 match "{}"'.format(self.match if isinstance(self.match, str) else self.match.group(0)))
                        print('2 before "{}"'.format(self.before))
                        print('3 after "{}"'.format(self.after))
                        print('4 buffer "{}"'.format(self.buffer))
                        print('5 output "{}"'.format(self.output))
                        print('6 full_buffer "{}"'.format(self.full_buffer))
                        print('7 prompt "{}"'.format(self.PROMPT))
                    break
                except TIMEOUT:
                    self.full_buffer = self.buffer

                    # Get output from the command sent, stripping the command and the prompt.
                    self.output = self.full_buffer.replace(self.PROMPT, '').strip()
                    if verbose:
                        print('s "{}"'.format(s))
                        print('1 buffer "{}"'.format(self.buffer))
                        print('2 output "{}"'.format(self.output))
                        print('3 full_buffer "{}"'.format(self.full_buffer))
                        print('4 prompt "{}"'.format(self.PROMPT))
                    if i + 1 >= attempt:
                        if self.verbose:
                            print('Raise TIMEOUT exception')
                        raise TIMEOUT(ExceptionPexpect)
        return self.match_index

    def sendline(self, s='', pattern=[], timeout=-1, attempt=1, regex=False, verbose=False):
        '''Send command and append line feed at the end.'''
        s = self._coerce_send_string(s)
        return self.send(s=s+self.linesep, pattern=pattern, timeout=timeout, attempt=attempt, regex=regex, verbose=verbose)
