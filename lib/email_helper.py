# Copyright 2018 The Fuego Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""
Send and receive email

"""
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pathlib


def send_email(fromAccount, toaddr, bcc, subject, body, attachments=[]):
    """Send an email using credentials of fromAccount to given recepients

    Args:
        fromAccount (tuple): tuple of (email, password) of from account
        toaddr (str or list): email address(es) to send email to as string e.g. 'joe@gmail.com'
        bcc (str or list): email address(es) to bcc the email
        subject (str): subject of the email
        body (str): body of the email
        attachments (list): optional list of attachements files
    """
    (fromEmail, fromPass) = fromAccount
    if isinstance(toaddr, str):
        toaddr = [toaddr]
    if isinstance(bcc, str):
        bcc = [bcc]

    parts=[]
    for filePath in attachments:
        #convert image to base64 encoding 
        attachFh = open(filePath, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload((attachFh).read())
        encoders.encode_base64(part)
        filename = pathlib.PurePath(filePath).name
        filename = filename.replace(';','_') # gmail considers ';' to mark end of filename
        part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
        parts.append(part)

    #setup message headers
    msg = MIMEMultipart()
    msg['From'] = fromEmail
    msg['To'] = ', '.join(list(toaddr))
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    for part in parts:
        msg.attach(part)

    #send the message
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
    except Exception as e:
        print("Setting Server Failed", e)
        return

    try:
        server.starttls()
    except Exception as e:
        print("Start tls failed", e)
        return

    try:
        server.login(fromEmail, fromPass)
    except Exception as e:
        print("Server Access Failed", e)
        return

    try:
        text = msg.as_string()
    except Exception as e:
        print("Message String Failed", e)
        return

    try:
        server.sendmail(fromEmail, toaddr + bcc, text)
    except Exception as e:
        print("Sending Email Failed", e)
        # print("From Addess ", fromEmail)
        # print("To Address", toaddr)
        # print("Text", text)
        # server.sendmail(fromEmail, toaddr, text)
        return
        
    try:
        server.quit()
    except Exception as e:
        print("Quiting Server Failed", e)


def check_email(email, passwd):
    '''check():
        Inputs: None

        Outputs:
            - locations: string list of locations of the fires that triggered the    emails
            - answers: boolean list of yes (1) or no (0) for the fire being there
    '''
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    # imaplib module implements connection based on IMAPv4 protocol
    mail.login(email, passwd)
    # >> ('OK', [username at gmail.com Vineet authenticated (Success)'])
    mail.list() # Lists all labels in GMail
    mail.select('inbox') # Connected to inbox.
    result, data = mail.uid('search', None, "UNSEEN")
    locations = []
    answers = []
    # search and return uids instead
    i = len(data[0].split()) # data[0] is a space separate string
    if i!=0:
        for x in range(i):
            latest_email_uid = data[0].split()[x] # unique ids wrt label selected
            result, email_data = mail.uid('fetch', latest_email_uid, '(RFC822)')
            # fetch the email body (RFC822) for the given ID
            raw_email = email_data[0][1]
            #continue inside the same for loop as above
            raw_email_string = raw_email.decode('utf-8')
            # converts byte literal to string removing b''
            email_message = email.message_from_string(raw_email_string)
            subject = email_message['subject']
            locations.append(subject[35:])
            # this will loop through all the available multiparts in mail
            for part in email_message.walk():
                if part.get_content_type() == "text/plain": # ignore attachments/html
                    body = part.get_payload(decode=True)
                    ans = body[0:3]

            if ans == 'YES':
                answers.append(1)
            else:
                answers.append(0)

            mail.store(latest_email_uid, '+FLAGS', '\\Deleted')

        mail.expunge()
    mail.close()
    mail.logout()

    return locations, answers
