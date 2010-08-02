"""
usage: python splitdisp.py datafiledir statusfile.txt
       python splitdisp.py datafiledir ordersfile.txt


"""

import sys
import re
import disp
from fileinput import input


COUNTRIES = ["England", "France", "Germany", "Turkey",
             "Italy", "Russia", "Austria"]
RACES = ["Federation", "Klingon", "Ferengi", "Romulan",
         "Cardassian", "Dominion", "Borg"]

def remove_empty_categories(s):
  """if a line ends with colon, and the next line does to, skip the first """

  held = []
  for l in s:
    if l.strip().endswith(":"):
      held = [l]
    elif held and not l.strip():
      held.append(l)
    else:
      if held:
        for ll in held:
          yield ll
        held = []
      yield l
  # lose anything left in held
   

def start(datafiledir, fname_in):
  outfname="status"
  if "orders" in fname_in:
    outfname="orders"
  else:
    assert "status" in fname_in

  inf = open(fname_in)

  country,race = None,None
  
  season = ""
  
  outs = {"public": [], "full":[]}
  
  def new_race(r):
    if r not in outs:
      outs[r] = outs["public"][:]
  
  for line in inf:
    if line.strip().startswith("Season "):
      ignore, month, type, year = line.strip().split()
      season = "%s_%s_%s" % (year, month, type)

      if type == "Retreats" and outfname == "orders":
        print "Remember to infiltrate someone for the dominion"
  
    if ":" in line and "(" in line and ")" in line:
      country, race = line.strip().split()
      race = race.replace("(","").replace(")","").replace(":","")
  
      assert country in COUNTRIES, country
      assert race in RACES, race
    
    sendto=set() # all if left blank
    infiltrated = "Infiltrated" in line
    cloaked = "Cloaked" in line
    
    if cloaked:
      new_race("Romulan")
      sendto.add("Romulan") # by explicitly writing romulan we remove
                            # other powers from the recieve
    if infiltrated:
      new_race("Dominion")
      if cloaked:
        sendto.add("Dominion")
  
    if sendto: # restricted

      # interpret the Knows(...) attributes
      for attr in line.split():
        if attr.startswith("Knows("):
          attr = attr.replace("Knows(","").replace(")","")
          for r in attr.split(","):
            assert r in RACES, r
            new_race(r)
            sendto.add(r)

          # info about who knows what is also restricted
          line = re.sub(r" Knows\(.*\)","",line)
          
      sendto.add("full") # everything goes to full
    else: # public
      sendto = outs # all
  
    for r in sendto:
      l = line
      if r not in ["Dominion", "full"]: # only the dominion and the
                                        # full set include infiltrations
        l = l.replace(" Infiltrated", "")
      outs[r].append(l)
    
  for race, out in outs.items():
    if race != "full":
       continue

    fname_base="%s_%s_%s" % (season,outfname,race)
    fname_text=fname_base+".txt"
    fname_png=fname_base+".png"

    textf=open(fname_text, "w")
    textf.writelines(remove_empty_categories(out))
    print "Wrote %s" % fname_text
    textf.close()

    if outfname == "status":
      disp.start(datafiledir, fname_text, fname_png)
      print "Wrote %s" % fname_png
  
if __name__ == "__main__":
  start(*sys.argv[1:])
  
