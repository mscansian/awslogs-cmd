""" cmd.py

    Run a command and stream its output to awslogs
"""
import argparse
import tempfile
import os
import subprocess
import uuid

from logstream import CloudWatchLogsStream


def main(args):
    stream = CloudWatchLogsStream(group_name=args.group, stream_name=args.stream)
    print ("group {}".format(args.group))
    print ("stream {}".format(args.stream))

    stdout_fd, stdout_filename = tempfile.mkstemp()
    with os.fdopen(stdout_fd, "w") as stdout:
        process = subprocess.Popen(args=[args.command]+args.args,
                                   stderr=stdout, stdout=stdout)
    try:
        process_is_running = True
        with open(stdout_filename, "r") as stdout:
            while process_is_running:
                process_is_running = process.poll() is None
                for line in stdout:
                    stream.write(line)
        retcode = "return code {}".format(process.poll())
        stream.write(retcode)
        print (retcode)
    except:
        raise
    finally:
        stream.push()
        os.remove(stdout_filename)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='awslogs-cmd', description='Redirect output to awslogs')
    parser.add_argument("command")
    parser.add_argument("args", nargs='*')
    parser.add_argument("-G", "--group", help="awslogs group name", required=True)
    parser.add_argument("-S", "--stream", help="awslogs stream name", default=str(uuid.uuid4()))
    parser.set_defaults(func=main)
    args = parser.parse_args()
    args.func(args)
