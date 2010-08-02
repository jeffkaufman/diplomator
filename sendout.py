"""

Send out status, orders, pictures etc

Usage:
  python sendout.py emailfile when

Example:
  python sendout.py stdip/player_emails.txt 2371_Spring_Retreats

player_emails should look like:
  Cardassian foo@example.com
  public bar@example.com

"""

import os
import sys
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

use_smtp = False

def parse_emails(fname):
  emails = {}
  for line in open(fname):
    race, addr = line.strip().split()
    emails[race] = addr
  return emails

def start(emailfile, when):

  year, season, type = when.split("_")

  emails = parse_emails(emailfile)

  files_for_players = {} # race -> [files]

  for a_file in os.listdir("."):
    if a_file.startswith(when):
      base, ext = a_file.split(".")
      ignore, ignore, ignore, ignore, race = base.split("_")

      if race not in files_for_players:
        files_for_players[race] = []
      files_for_players[race].append(a_file)

  for race, files in files_for_players.items():
    if race not in emails:
      print "Skipping", race, "(no email addr)"
      continue
    
    send_mail(send_from=emails["gm"],
              send_to=[emails[race]],
              subject="Resolutions %s %s %s %s Edition" % (season, type, year, race),
              text="Resolutions attached as text and images\n",
              files=files)

def send_mail(send_from, send_to, subject, text, files=[], server="localhost"):
  """ modified from http://snippets.dzone.com/posts/show/2038 """

  print "Sending %s to %s" % (files, send_to)
  
  assert type(send_to)==list
  assert type(files)==list

  msg = MIMEMultipart()
  msg['From'] = send_from
  msg['To'] = COMMASPACE.join(send_to)
  msg['Date'] = formatdate(localtime=True)
  msg['Subject'] = subject

  msg.attach( MIMEText(text) )

  for f in files:
    part = MIMEBase('application', "octet-stream")
    part.set_payload( open(f,"rb").read() )
    Encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
    msg.attach(part)

  if use_smtp:
    smtp = smtplib.SMTP(server)
    smtp.sendmail(send_from, send_to, msg.as_string())
    smtp.close()
  else:
    sendmail_location = "/usr/sbin/sendmail" # sendmail location
    p = os.popen("%s -t" % sendmail_location, "w")
    p.write(msg.as_string())
    
    status = p.close()
    if status:
       raise Exception("Sendmail failed with status %s" % status)


if __name__ == "__main__":
  start(*sys.argv[1:])
