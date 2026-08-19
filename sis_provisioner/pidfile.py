# Copyright 2026 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


import errno
import os
from inspect import getmodule, stack
from logging import getLogger


# modified from:
# http://stackoverflow.com/questions/1444790/python-module-for-creating-pid-
# based-lockfile
class Pidfile:
    def __init__(self, path=None, directory='/tmp', filename=None, logger=None):
        caller = getmodule(stack()[1][0]).__name__
        if path:
            self.pidfile = path
        else:
            if not filename:
                filename = caller.split('.')[-1]

            self.pidfile = f'{directory}/{filename}.pid'

        self.logger = logger if logger else getLogger(caller)

    def __enter__(self):
        try:
            self._create()
        except OSError as e:
            if e.errno == errno.EEXIST:
                pid = self._check()
                if pid:
                    self.pidfd = None
                    msg = f'process already running pid = {pid} ({self.pidfile})'
                    self.logger.info(msg)
                    raise ProcessRunningException(msg)
                else:
                    os.remove(self.pidfile)
                    self.logger.info(f'removed stale lockfile {self.pidfile}')
                    self._create()
            else:
                raise

        os.write(self.pidfd, str(os.getpid()).encode('utf-8'))
        os.close(self.pidfd)
        return self

    def __exit__(self, t, e, tb):
        # return false to raise, true to pass
        if t is None:
            # normal condition, no exception
            self._remove()
            return True
        elif t is ProcessRunningException:
            # do not remove the other process lockfile
            return False
        else:
            # other exception
            if self.pidfd:
                # this was our lockfile, removing
                self._remove()
            return False

    def _create(self):
        self.pidfd = os.open(self.pidfile,
                             os.O_CREAT | os.O_WRONLY | os.O_EXCL)

    def _remove(self):
        os.remove(self.pidfile)

    def _check(self):
        """
        check if a process is still running
        the process id is expected to be in pidfile, which should exist.
        if it is still running, returns the pid, if not, return False.
        """
        with open(self.pidfile, 'r') as f:
            try:
                pid = int(f.read())
                os.kill(pid, 0)
                return pid
            except ValueError:
                self.logger.error(f'bad pid: {pid}')
            except OSError:
                self.logger.error(f'cannot deliver signal to {pid}')

            return False


class ProcessRunningException(Exception):
    pass
