""" cmd.py

    Run a command and stream its output to awslogs
"""
import argparse
import tempfile
import os
import subprocess
import uuid
import signal
import sys

from logstream import CloudWatchLogsStream


def main(args):
    logs = CloudWatchLogsStream(group_name=args.group, stream_name=args.stream)

    if args.verbose:
        print ("group {}".format(args.group))
        print ("stream {}".format(args.stream))

    if not args.literal:
        # HACK: Use a space before args to pass then to the function
        args.args = list(map(str.lstrip, args.args))

    try:
        cmd_args = [args.command]+args.args
        if args.unbuffer:
            cmd_args.insert(0, "unbuffer")
        process, stdout_filename, stderr_filename = start_process(cmd_args)

        if args.sigusr1:
            # Forward SIGUSR1 to child process
            signal.signal(signal.SIGUSR1, forward_signal(process))

        if args.sigterm:
            # Forward SIGTERM to child process
            signal.signal(signal.SIGTERM, forward_signal(process))

        try:
            run_process(process, logs, stdout_filename, stderr_filename,
                        through=args.stream_through)

            if args.return_code:
                write_stream(logs, through=args.stream_through,
                             stderr="return code {}".format(process.poll()))
        except:
            raise
        finally:
            os.remove(stdout_filename)
            os.remove(stderr_filename)
    except Exception as e:
        if not args.silent_exceptions:
            write_stream(logs, stderr=str(e), through=True)
        raise
    finally:
        logs.push()
    sys.exit(process.returncode)

# Start a process and return filenames for stdout and stderr
def start_process(args):
    stdout_fd, stdout_filename = tempfile.mkstemp()
    stderr_fd, stderr_filename = tempfile.mkstemp()
    with os.fdopen(stdout_fd, "w") as stdout:
        with os.fdopen(stderr_fd, "w") as stderr:
            process = subprocess.Popen(args=args, stderr=stderr, stdout=stdout)
    return process, stdout_filename, stderr_filename

# Read stderr and stdout files and stream to awslogs until process exits
def run_process(process, logs, stdout_filename, stderr_filename, through):
    with open(stdout_filename, "r") as stdout:
        with open(stderr_filename, "r") as stderr:
            process_is_running = True
            while process_is_running:
                process_is_running = process.poll() is None
                for line in stdout:
                    write_stream(logs, stdout=line, through=through)
                for line in stderr:
                    write_stream(logs, stderr=line, through=through)

# Write stdout or stderr
def write_stream(logs, stdout=None, stderr=None, through=False):
    if stdout:
        logs.write(stdout)
        if through:
            print (stdout)

    if stderr:
        logs.write(stderr)
        if through:
            print (stderr, file=sys.stderr)

# Send signal to
def forward_signal(process):
    def signal(signum, frame):
        process.send_signal(signum)
    return signal

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='awslogs-cmd', description='Redirect output to awslogs')
    parser.add_argument("command")
    parser.add_argument("args", nargs='*')
    parser.add_argument("-G", "-g", "--group", help="awslogs group name", required=True)
    parser.add_argument("-S", "-s", "--stream", help="awslogs stream name", default=str(uuid.uuid4()))
    parser.add_argument("-v", "--verbose", help="print group name and stream name", action="store_true")
    parser.add_argument("-t", "--stream-through", help="output stdout and stderr", action="store_true")
    parser.add_argument("--unbuffer", help="use unbuffer", action="store_true")
    parser.add_argument("--return-code", help="print return code", action="store_true")
    parser.add_argument("--literal", help="never lstrip args", action="store_true")
    parser.add_argument("--silent-exceptions", help="dont push exceptions to awslogs", action="store_true")
    parser.add_argument("--sigusr1", help="forward SIGUSR1 to child process", action="store_true")
    parser.add_argument("--sigterm", help="forward SIGTERM to child process", action="store_true")
    parser.set_defaults(func=main)
    args = parser.parse_args()
    args.func(args)
