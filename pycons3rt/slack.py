#!/usr/bin/python

"""Module: slack

This module provides an interface for posting to Slack!

Sample usage:

python slack.py \
    --text="This is the text of my message" \
    --url="https://hooks.slack.com/services/my-webhook-url" \
    --attachment="Attachment text" \
    --channel="@joe.yennaco" \
    --color=good \
    --pretext="This is pretext" \
    --icon="https://s3.amazonaws.com/jackpine-images/homer-flexing.jpg"
"""
import logging
import urllib
import json
import argparse

# Set up logger name for this module
try:
    from logify import Logify
except ImportError:
    Logify = None
    mod_logger = 'slack'
else:
    mod_logger = Logify.get_name() + '.slack'

__author__ = 'Joe Yennaco'


class SlackMessage(object):
    """Object to encapsulate a Slack message

    This class encapsulates a Slack message and its parameters, and
    provides a send() method for sending Slack messages
    """
    def __init__(self, webhook_url, text, **kwargs):
        """Creates a SlackMessage object

        :param webhook_url: (str) Webhook URL provided by Slack
        :param text: (str) Text to send in the Slack message
        :param kwargs:
        :return: None
        :raises ValueError
        """
        self.cls_logger = mod_logger + '.SlackMessage'
        log = logging.getLogger(self.cls_logger + '.__init__')
        self.payload = {}
        if not isinstance(webhook_url, basestring):
            raise ValueError('webhook_url arg must be a string')
        if not isinstance(text, basestring):
            raise ValueError('text arg must be a string')
        self.payload['text'] = text
        self.webhook_url = webhook_url
        self.options = ['user', 'channel', 'icon_url', 'icon_emoji']
        self.attachments = []
        for option in self.options:
            if (option in kwargs) and (isinstance(option, basestring)):
                self.payload[option] = kwargs[option]
        log.info('SlackMessage configured using webhook URL: {u}'.format(
            u=self.webhook_url))

    def __str__(self):
        return self.payload.__str__()

    def set_text(self, text):
        """Sets the text attribute of the payload

        :param text: (str) Text of the message
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_text')
        if not isinstance(text, basestring):
            msg = 'text arg must be a string'
            log.error(msg)
            raise ValueError(msg)
        self.payload['text'] = text
        log.info('Set message text to: {t}'.format(t=text))

    def set_icon(self, icon_url):
        """Sets the icon_url for the message

        :param icon_url: (str) Icon URL
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.set_icon')
        if not isinstance(icon_url, basestring):
            msg = 'icon_url arg must be a string'
            log.error(msg)
            raise ValueError(msg)
        self.payload['icon_url'] = icon_url
        log.info('Set Icon URL to: {u}'.format(u=icon_url))

    def add_attachment(self, attachment):
        """Adds an attachment to the SlackMessage payload

        This public method adds a slack message to the attachment
        list.

        :param attachment: SlackAttachment object
        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.add_attachment')
        if not isinstance(attachment, SlackAttachment):
            msg = 'attachment must be of type: SlackAttachment'
            log.error(msg)
            raise ValueError(msg)
        self.attachments.append(attachment.attachment)
        log.info('Added attachment: {a}'.format(a=attachment))

    def send(self):
        """Sends the Slack message

        This public method sends the Slack message along with any
        attachments, then clears the attachments array.

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.send')

        if self.attachments:
            self.payload['attachments'] = self.attachments

        # Encode payload in JSON
        log.debug('Using payload: %s', self.payload)
        try:
            json_payload = json.JSONEncoder().encode(self.payload)
        except(TypeError, ValueError, OverflowError) as e:
            log.error('There was a problem encoding the JSON payload\n%s', e)
            raise
        else:
            log.debug('JSON payload: %s', json_payload)

        # Post to Slack!
        log.info('Posting message to Slack...')
        try:
            result = urllib.urlopen(self.webhook_url, json_payload)
        except(TypeError, ValueError, IOError) as e:
            log.error('There was a problem querying URL: %s\n%s',
                      self.webhook_url, e)
            raise

        # Check return code
        if result.getcode() != 200:
            log.error('Slack post to url {u} failed with code: {c}:\n{o}'.format(
                c=result.getcode(), u=result.geturl(), o=result.info()))
        else:
            log.info('Posted message to Slack successfully.')

        # Clear out attachments after sending
        self.attachments = []
        self.payload.pop('attachments', None)


class SlackAttachment(object):
    """Contains data for a Slack Attachment

    This class is used to create an attachment for a Slack
    post.
    """
    def __init__(self, fallback, **kwargs):
        self.cls_logger = mod_logger + '.SlackAttachment'
        if not isinstance(fallback, basestring):
            raise ValueError('fallback arg must be a string')
        self.fallback = fallback
        self.attachment = {}
        self.options = ['color', 'pretext', 'author_name', 'author_link',
                        'author_icon', 'title', 'title_link', 'text',
                        'image_url', 'thumb_url']
        for option in self.options:
            if (option in kwargs) and (isinstance(option, basestring)):
                self.attachment[option] = kwargs[option]
        if 'fields' in kwargs:
            if isinstance(kwargs['fields'], list):
                for field in kwargs['fields']:
                    if not isinstance(field, dict):
                        raise ValueError('field entries must be of type: dict')
                    for key, value in field.iteritems():
                        if not isinstance(value, basestring):
                            raise ValueError('field values must be strings')
                self.attachment['fields'] = kwargs['fields']

    def __str__(self):
        return self.fallback


def main():
    """Handles external calling for this module

    Execute this python module and provide the args shown below to
    external call this module to send Slack messages with attachments!

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    parser = argparse.ArgumentParser(description='This Python module allows '
                                                 'sending Slack messages.')
    parser.add_argument('-u', '--url', help='Slack webhook URL', required=True)
    parser.add_argument('-t', '--text', help='Text of the message', required=True)
    parser.add_argument('-n', '--channel', help='Slack channel', required=True)
    parser.add_argument('-i', '--icon', help='URL for the Slack icon', required=False)
    parser.add_argument('-c', '--color', help='Color of the Slack post', required=False)
    parser.add_argument('-a', '--attachment', help='Text for the Slack Attachment', required=False)
    parser.add_argument('-p', '--pretext', help='Pretext for the Slack attachment', required=False)
    args = parser.parse_args()

    # Create the SlackMessage object
    try:
        slack_msg = SlackMessage(args.url, channel=args.channel, icon_url=args.icon, text=args.text)
    except ValueError as e:
        msg = 'Unable to create slack message\n{ex}'.format(ex=e)
        log.error(msg)
        print msg
        return

    # If provided, create the SlackAttachment object
    if args.attachment:
        try:
            slack_att = SlackAttachment(fallback=args.attachment, color=args.color,
                                        pretext=args.pretext, text=args.attachment)
        except ValueError as e:
            msg = 'Unable to create slack attachment\n{ex}'.format(ex=e)
            log.error(msg)
            print msg
            return
        slack_msg.add_attachment(slack_att)

    # Send Slack message
    try:
        slack_msg.send()
    except(TypeError, ValueError, IOError) as e:
        msg = 'Unable to send Slack message\n{ex}'.format(ex=e)
        log.error(msg)
        print msg
        return
    else:
        msg = 'Your message has been Slacked!'
        log.info(msg)
        print msg


if __name__ == '__main__':
    main()
