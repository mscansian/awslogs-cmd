# awslogs-cmd #
Simple tool to run a command and push the output to AWS Cloud Watch Logs

## Installation ##
You need to run a script to install the dependencies on a virtualenv

    $ ./install-venv.sh

## Usage example ##
The following example will run the command "apt-cache search linux" and push
its output to a stream in the /test/cmd group. The stream name will be printed
on the terminal.

    $ ./awslogs-cmd --group /test/cmd apt-cache search linux

For more options use the help:

    $ ./awslogs-cmd --help

## Credentials ##
Credentials are handled by boto3. You can use env vars or a credentials file.

### Environment Variables ###

* AWS_ACCESS_KEY_ID
* AWS_SECRET_ACCESS_KEY
