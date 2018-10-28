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
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import time

"""
When a possible event is detected, this sends an email 
(or possibly another kind of message) containing information about the current detection
"""

def send_email(toaddr, accuracy, location, filename, motion_filename, boxed_filename):
    '''send(toaddr, accuracy, location):
        Inputs:
            - toaddr: email address or list of addresses to send email to as string e.g. 'joe@gmail.com'
            - accuracy: decimal accuracy of the detection from Caffe
            - location: string for location identification e.g. 'High Point East'

        Outputs:
            - time: the time that the email was sent to send a follow up email 5 minutes later.
    '''

    #build message text
    rounded_accuracy = round(accuracy,3)*100
    fromaddr = "fuego.response@gmail.com"    # address of sender
    #if we have a list of emails, join them into a string
    try:
        if not isinstance(toaddr, basestring):
            msgto = ', '.join(list(toaddr))
        else:
            msgto = toaddr
    except:
        print("BASE STRING?")
    subjectText = 'Alert: {accuracy}% Chance of Fire at {location}'
    subjectText = subjectText.format(
                        accuracy=rounded_accuracy, 
                        location=location
                        )

    body = "Attached are the images our algorithms used to detect the fires as well as a \
link to the website. If there is fire, please respond 'YES'; if there is not fire, \
please respond 'NO'. This will help our algorithms learn more and give you less false positives."

    #convert image to base64 encoding 
    attachment = open(filename, "rb")   #path of the picture
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
    
    attachment2 = open(motion_filename, "rb")   #path of the picture
    part2 = MIMEBase('application', 'octet-stream')
    part2.set_payload((attachment2).read())
    encoders.encode_base64(part2)
    part2.add_header('Content-Disposition', "attachment; filename= %s" % motion_filename)
    
    attachment3 = open(boxed_filename, "rb")   #path of the picture
    part3 = MIMEBase('application', 'octet-stream')
    part3.set_payload((attachment3).read())
    encoders.encode_base64(part3)
    part3.add_header('Content-Disposition', "attachment; filename= %s" % boxed_filename)


    #setup message headers
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = msgto
    msg['Subject'] = subjectText
    msg.attach(MIMEText(body, 'plain'))
    msg.attach(part)
    msg.attach(part2)
    msg.attach(part3)

    #send the message
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
    except:
        print("Setting Server Failed")
    try:
        server.starttls()
    except:
        print("Start tls failed")
    try:
        server.login(fromaddr, "fuegocarl")     # Password
    except:
        print("Server Access Failed")
    try:
        text = msg.as_string()
    except:
        print("Message String Failed")
    try:
        server.sendmail(fromaddr, toaddr, text)
    except:
        print("Sending Email Failed")
        print("From Addess ", fromaddr)
        print("To Address", toaddr)
        print("Text", text)
        server.sendmail(fromaddr, toaddr, text)
        
    try:
        server.quit()
    except:
        print("Quiting Server Failed")

    return time.time()

def check_email():
    '''check():
        Inputs: None

        Outputs:
            - locations: string list of locations of the fires that triggered the    emails
            - answers: boolean list of yes (1) or no (0) for the fire being there
    '''
    mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
    # imaplib module implements connection based on IMAPv4 protocol
    mail.login('fuego.response@gmail.com', 'fuegocarl')
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