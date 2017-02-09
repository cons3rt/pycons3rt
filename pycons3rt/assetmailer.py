#!/usr/bin/env python

"""Module: assetmailer

This module provides an interface for emailing CONS3RT asset-related info!

"""
import logging
import argparse
import os
import sys
import smtplib
from email.mime.text import MIMEText

# Set up logger name for this module
from logify import Logify
from osutil import get_os
import deployment

__author__ = 'Joe Yennaco'


# Set up logger name for this module
mod_logger = Logify.get_name() + '.assetmailer'

# Default sender email address
default_sender_email = 'joe.yennaco@jackpinetech.com'

# Default recipient email address
default_recipient_email = 'joe.yennaco@jackpinetech.com'


class AssetMailerError(Exception):
    """Simple exception type for AssetMailer errors
    """
    pass


class AssetMailer(object):

    def __init__(self):
        """Creates an AssetMailer object

        :return: None
        """
        self.cls_logger = mod_logger + '.AssetMailer'
        if get_os() == 'Linux':
            self.cons3rt_agent_home = os.path.join(os.path.sep, 'opt', 'cons3rt-agent')
        elif get_os() == 'Windows':
            self.cons3rt_agent_home = os.path.join('C:', os.path.sep, 'cons3rt-agent')
        else:
            self.cons3rt_agent_home = None
        if self.cons3rt_agent_home:
            self.cons3rt_agent_log_dir = os.path.join(self.cons3rt_agent_home, 'log')
        else:
            self.cons3rt_agent_log_dir = None
        self.dep = deployment.Deployment()
        self.run_name = self.dep.get_value('cons3rt.deploymentRun.name')
        self.run_id = self.dep.get_value('cons3rt.deploymentRun.id')
        self.recipient_email = self.dep.get_value('cons3rt.user.email')
        if self.recipient_email is None:
            self.recipient_email = default_recipient_email
        self.subject = 'pyCONS3RT Asset Mailer: Run {n}[{i}]'.format(n=self.run_name, i=self.run_id)

    def __str__(self):
        return 'AssetMailer for Deployment Run ID: {i}'.format(i=self.run_id)

    def send_cons3rt_agent_logs(self):
        """Send the cons3rt agent log file

        :return:
        """
        log = logging.getLogger(self.cls_logger + '.send_cons3rt_agent_logs')

        if self.cons3rt_agent_log_dir is None:
            log.warn('There is not CONS3RT agent log directory on this system')
            return

        for item in os.listdir(self.cons3rt_agent_log_dir):
            if os.path.isfile(item):
                item_path = os.path.join(self.cons3rt_agent_log_dir, item)
                log.info('Sending email with cons3rt agent log file: {f}'.format(f=item_path))
                try:
                    self.send_text_file(text_file=item_path)
                except (TypeError, OSError, AssetMailerError):
                    _, ex, trace = sys.exc_info()
                    msg = '{n}: There was a problem sending CONS3RT agent log file: {f}\n{e}'.format(
                        n=ex.__class__.__name__, f=item_path, e=str(ex))
                    raise AssetMailerError, msg, trace
                else:
                    log.info('Successfully sent email with file: {f}'.format(f=item_path))

    def send_text_file(self, text_file, sender=None, recipient=None):
        """Sends an email with the contents of the provided text file

        :return: None
        """
        log = logging.getLogger(self.cls_logger + '.send_text_file')

        if not isinstance(text_file, basestring):
            msg = 'arg text_file must be a string, found type: {t}'.format(t=text_file.__class__.__name__)
            raise TypeError(msg)

        if not os.path.isfile(text_file):
            msg = 'The provided text_file was not found or is not a file: {f}'.format(f=text_file)
            raise OSError(msg)

        # Determine sender/recipient
        if sender is None:
            sender = default_sender_email
        if recipient is None:
            recipient = self.recipient_email

        # Set the email subject
        file_name = text_file.split(os.path.sep)[-1]
        subject = self.subject + 'File: '.format(f=file_name)

        # Read the input text file
        try:
            fp = open(text_file, 'rb')
            mail_message = MIMEText(fp.read())
            fp.close()
        except OSError:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem reading text file: {f}\n{e}'.format(
                n=ex.__class__.__name__, f=text_file, e=str(ex))
            raise AssetMailerError, msg, trace

        # Configure the mail message
        mail_message['Subject'] = subject
        mail_message['From'] = sender
        mail_message['To'] = recipient

        # Set the SMTP server to be localhost
        log.debug('Sending email with subject {s} to {e}...'.format(s=subject, e=recipient))
        try:
            s = smtplib.SMTP('localhost')
            s.sendmail(sender, [recipient], mail_message.as_string())
            s.quit()
        except Exception:
            _, ex, trace = sys.exc_info()
            msg = '{n}: There was a problem sending email message to {r}\n{e}'.format(
                n=ex.__class__.__name__, r=recipient, e=str(ex))
            raise AssetMailerError, msg, trace
        else:
            log.info('Sent email to: {r}'.format(r=recipient))


def main():
    """Handles external calling for this module

    Execute this python module and provide the args shown below to
    external call this module to send email messages!

    :return: None
    """
    log = logging.getLogger(mod_logger + '.main')
    parser = argparse.ArgumentParser(description='This module allows sending email messages.')
    parser.add_argument('-f', '--file', help='Full path to a plain text file', required=False)
    parser.add_argument('-s', '--sender', help='Email address of the sender', required=False)
    parser.add_argument('-r', '--recipient', help='Email address of the recipient', required=False)
    args = parser.parse_args()

    am = AssetMailer()
    err = None
    if args.file:
        try:
            am.send_text_file(text_file=args.file, sender=args.sender, recipient=args.recipient)
        except Exception:
            _, ex, trace = sys.exc_info()
            err = '{n}: There was a problem sending email with file {f} from sender {s} to recipient {r}:\n{e}'.format(
                n=ex.__class__.__name__, f=args.file, s=args.sender, r=args.recipient, e=str(ex))
            log.error(err)
    else:
        try:
            am.send_cons3rt_agent_logs()
        except Exception:
            _, ex, trace = sys.exc_info()
            err = '{n}: There was a problem sending cons3rt agent log files:\n{e}'.format(
                n=ex.__class__.__name__, e=str(ex))
            log.error(err)
    if err is None:
        log.info('Successfully send email')


if __name__ == '__main__':
    main()
