import datetime as dt
import tarfile
import time
import smtplib
import os.path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email():
    email_user = 'flashcardappbackup@gmail.com'
    server = smtplib.SMTP ('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_user, 'flashcard123')

    ## FILE TO SEND AND ITS PATH
    filename = 'cards.db'
    SourcePathName  = '/home/kaplanerbil/flashcardproject2/venv/computer-science-flash-cards/db/'
    #SourcePathName  = 'D:\workspaces\IdeaProjects\computer-science-flash-cards\db/'

    #backup file with different name using timestamp
    timestampStr = str(dt.datetime.now().strftime("%Y%m%d_%H-%M-%S"))
    make_tarfile(timestampStr+'cards.tar.gz', SourcePathName + filename)

    msg = MIMEMultipart()
    msg['From'] = 'from@domain.com'
    msg['To'] = 'kaplanerbil@gmail.com'
    msg['Subject'] = 'DB Backup'
    body = 'Please find Last cards in attachment'
    msg.attach(MIMEText(body, 'plain'))



    ## ATTACHMENT PART OF THE CODE IS HERE
    attachment = open(SourcePathName+timestampStr+'cards.tar.gz', 'rb')
    part = MIMEBase('application', "octet-stream")
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % timestampStr+'cards.tar.gz')
    msg.attach(part)
    server.send_message(msg)
    server.quit()


def send_email_at(send_time):
    time.sleep(send_time.timestamp() - time.time())
    send_email()
    print('email sent')


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


# first_email_time = dt.datetime(2020,2,13,3,0,0) # set your sending time in UTC
now = dt.datetime.now()
now_plus_1 = now + dt.timedelta(seconds = 5)
first_email_time = now_plus_1
interval = dt.timedelta(minutes=24*60) # set the interval for sending the email

send_time = first_email_time
while True:
    send_email_at(send_time)
    send_time = send_time + interval
