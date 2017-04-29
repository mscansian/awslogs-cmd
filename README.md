# awslogs-cmd #
Run a command and push the output to AWS Cloud Watch Logs

## Installation ##
Dependencies are installed in a virtualenv. To install run the following
command from the project root.

    $ ./install-venv.sh

## Usage example ##
The following example will run *apt-cache search linux* and push the output
to a stream inside *test* group in AWS Cloud Watch Logs. The stream name is
printed on the terminal.

    $ ./awslogs-cmd -v --group test apt-cache search linux

For further help:

    $ ./awslogs-cmd --help

## Running commands with optional arguments ##
When running commands with optional arguments, they may get mixed up with
awslogs-cmd's own arguments. To fix this behaviour enclose ambiguous arguments
with quotes and prepend a space. Example:

    $ ./awslogs-cmd --group test netstat -l  # Wrong. Results in error
    $ ./awslogs-cmd --group test netstat " -l"  # Correct

To disable this behaviour see option *--literal*.

## AWS Credentials ##
AWS Credentials are handled by boto3.
See https://boto3.readthedocs.io/en/latest/guide/configuration.html.
