""" logstream.py

    Small utility lib to stream to AWS Cloud Watch Logs.
"""
import os
import logging
import pytz
from datetime import datetime

import boto3
import botocore


CLOUDWATCH_LOGS_REGION = os.environ.get("CLOUDWATCH_LOGS_REGION", "us-east-1")


logger = logging.getLogger(__name__)


class BaseLogStream:
    def log(self, message, timestamp=None):
        raise NotImplementedError()

    def push(self):
        raise NotImplementedError()

    def __init__(self, group_name, stream_name):
        self.group_name = group_name
        self.stream_name = stream_name

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.push()


class CloudWatchLogsStream(BaseLogStream):
    LOG_EVENT_HEADER_SIZE = 26    # 26 bytes
    MAX_BATCH_SIZE = 1048576      # 1 MB
    MAX_BATCH_COUNT = 1000        # 1000 events
    PUSH_SIZE_THRESHOLD = 0.8     # 80%
    PUSH_COUNT_THRESHOLD = 0.99   # 99%
    PUSH_TIME_THRESHOLD = 30000   # 30 seconds

    """ Alias for log() """
    def write(self, data):
        self.log(data)

    """ Log message """
    def log(self, message, timestamp=None):
        if self._crossed_any_thresholds():
            self.push()

        if not message:
            return  # No message to log

        if timestamp is None:
            timestamp = self._current_time()
        self._create_log_event(message, timestamp)

    def _create_log_event(self, message, timestamp):
        self._log_events.append({"timestamp": timestamp, "message": message})
        self._log_events_size += len(message) + self.LOG_EVENT_HEADER_SIZE

    def _crossed_any_thresholds(self):
        if self._crossed_time_threshold() or self._crossed_size_thresholds():
            return True
        return False

    def _crossed_size_thresholds(self):
        max_size = self.MAX_BATCH_SIZE * self.PUSH_SIZE_THRESHOLD
        if self._log_events_size >= max_size:
            logger.info("Forcing a PUSH. Reached max batch size.")
            return True
        max_count = self.MAX_BATCH_COUNT * self.PUSH_COUNT_THRESHOLD
        if len(self._log_events) >= max_count:
            logger.info("Forcing a PUSH. Reached max batch count.")
            return True
        return False

    def _crossed_time_threshold(self):
        try:
            oldest_log_event = self._log_events[0]
            expiration_time = self._current_time() - self.PUSH_TIME_THRESHOLD
            if oldest_log_event["timestamp"] <= expiration_time:
                logger.info("Forcing a PUSH. Reached time threshold.")
                return True
        except IndexError:
            return False
        return False

    """ Push logged messages to AWS Cloud Watch """
    def push(self):
        logger.info("Pushing logs to CloudWatch.")
        if not len(self._log_events):
            logger.warning("No data to push.")
            return
        self._awslogs_push(self.group_name, self.stream_name, self._log_events)
        self._clear_log_events()
        logger.info("Push completed.")

    def _awslogs_push(self, group_name, stream_name, log_events):
        response = self._client.put_log_events(
            logGroupName=group_name,
            logStreamName=stream_name,
            logEvents=log_events,
            sequenceToken=self._sequence_token
        )
        self._sequence_token = response["nextSequenceToken"]

    def _get_sequence_token(self):
        response = self._client.describe_log_streams(
            logGroupName=self.group_name,
            logStreamNamePrefix=self.stream_name,
            limit=1
        )
        return response["logStreams"][0].get("uploadSequenceToken", "0")

    def _clear_log_events(self):
        self._log_events_size = 0
        self._log_events = []

    def __init__(self, group_name, stream_name):
        super(CloudWatchLogsStream, self).__init__(group_name, stream_name)
        self._client = boto3.client('logs', region_name=CLOUDWATCH_LOGS_REGION)
        self._clear_log_events()
        self._create_stream()

    def _create_stream(self):
        try:
            logger.info("Creating CloudWatch stream.")
            self._client.create_log_stream(
                logGroupName=self.group_name,
                logStreamName=self.stream_name
            )
            self._sequence_token = "0"
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                logger.warning("CloudWatch Stream already exists.")
                self._sequence_token = self._get_sequence_token()
            else:
                raise

    def _current_time(self):
        utc_time = datetime.now(pytz.timezone('UTC'))
        return int(utc_time.timestamp() * 1000)
