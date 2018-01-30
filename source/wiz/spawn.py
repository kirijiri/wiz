# :coding: utf-8

from __future__ import print_function

import os
import sys
import shlex
import select
import subprocess
import distutils.spawn
import termios
import tty
import pty


def shell(environment, shell_type="bash"):
    """Spawn a sub-shell with an *environment* mapping.

    *shell_type* can indicate a specific type of shell. Default is Bash.

    """
    executable = distutils.spawn.find_executable(shell_type)

    # save original tty setting then set it to raw mode
    old_tty = termios.tcgetattr(sys.stdin)
    tty.setraw(sys.stdin.fileno())

    # open pseudo-terminal to interact with subprocess
    master_fd, slave_fd = pty.openpty()

    # Run in a new process group to enable job control
    process = subprocess.Popen(
        executable,
        preexec_fn=os.setsid,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        universal_newlines=True,
        env=environment
    )

    while process.poll() is None:
        read_list, write_list, _ = select.select([sys.stdin, master_fd], [], [])

        if sys.stdin in read_list:
            message = os.read(sys.stdin.fileno(), 10240)
            os.write(master_fd, message)

        elif master_fd in read_list:
            message = os.read(master_fd, 10240)
            if message:
                os.write(sys.stdout.fileno(), message)

    # restore tty settings back
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)


def execute(command, environment):
    """Run an *executable* within a specific *environment*."""
    # Run in a new process group to enable job control
    process = subprocess.Popen(
        shlex.split(command),
        preexec_fn=os.setsid,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=environment
    )

    lines_iterator = iter(process.stdout.readline, b"")
    while process.poll() is None:
        for line in lines_iterator:
            _line = line.rstrip()
            print(_line.decode("latin"), end="\r\n")