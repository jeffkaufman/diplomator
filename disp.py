"""
Usage:
  $ ls
  IMAGE_L.gif   icons  COORDINATES  statusfile
  
  $ python disp.py datafilesdir statusfile tmp.png

"""

import sys
import os.path
from random import random
import Image, ImageDraw
from math import sqrt, acos, sin
  
ILLEGAL_PLACEMENT = (5,5) # The special value 5,5 for coordinates indicates illegal placement


IMAGE = "IMAGE_L.png"
COORDS = "COORDINATES"
ICONS="icons"

use_images = True
use_names = True
use_flood_fill = True

def all(s):
  """old versions of python don't have all"""
  for x in s:
    if not x:
      return False
  return True

def parse_coords(COORDS):
  """ read the coordinates files and return {prov-name: (info)}

  The keys of the hash are upper case anmes of provinces

  The values are (x,y) pairs representing the coordinates of, in
  order, the place to draw the name, the place to draw an army, the
  place to draw a fleet, and the place to draw a fleet on the
  alternate coast.

  """
  
  inf = open(COORDS)
  coords = {}
  for line in inf:
    line = line.strip()
    if not line or not line[0].isalpha():
      continue
    n, c = line.split(None, 1)
    nX, nY, aX, aY, fX, fY, fsX, fsY = [2*int(z)+5 for z in c.split()]
    coords[n.upper()] = [(nX, nY), (aX, aY), (fX, fY), (fsX, fsY)]
  return coords


# we hard code the colors to flood fill with
colors = {"Klingon"    : (255,180,170),     # red
          "Cardassian" : (240,240,150),     # yellow
          "Borg"       : (180,180,180),     # black
          "Federation" : (190,190,255),     # blue
          "Dominion"   : (243,190,240),     # purple
          "Ferengi"    : (230,190,140),     # orange
          "Romulan"    : (190,240,190)}     # green


def parse_status(status_fname, provinces):
  """ the status file has all the information needed for future turns

  Returns options, powers

  options are the things that show up before the first section
  representing a country.  They can represent anything, from the
  season of the game to random information someone wanted to add.
  Unrecognized options are parsed but then ignored.
  
  options is a hash.  The keys are the names of the options ('Season',
  'Wormhole', ...), the values are tuples where each element of the
  tuple is one of the space separated components.  Ugh.  Example:

    options['Season'] = ('Spring', 'Moves', '2373')
    options['Wormhole'] = ('BLA', 'GOL')

  powers are the countries, and contain all the information about a
  country.  There should only be the 7 normal ones, though it's fine
  if some are missing.

  powers is a list of power tuples

  each power tuple is in the form:

    (country, race, units, scs)

  country is the text name of the power: 'Russia'

  race is the text race of the power: 'Cardassian'

  units is a list of the units of that power, consisting of unit
  tuples.

  unit tuples are in the form:

    (unitname, (attr1, attr2, attr3))

  unitname is the name of the province the unit is in, while attrs
  include all of the other information about the unit.  The status
  lines:

    Bla Fleet Assimilated(Cardassian)
    Mos Army Cloaked Disloged(War) Knows(Klingon,Cardassian)

  translate to 'a fleet in the black sea that is now borg but was
  assimilated from the cardassians' and 'a cloaked army in moscow that
  was disloged from warsaw (and so cannot retreat there) and both the
  klingons and cardassians know about it)'.  These would turn into the
  unit tuples:

    ('BLA', ('Fleet', 'Assimilated(Cardassian)'))
    ('MOS', ('Army', 'Cloaked', 'Disloged(War)',
             'Knows(Klingon,Cardassian)'))

  scs is a list of the supply centers belonging to that power.  This
  list consists of the text names of the supply centers.

  """
  

  
  inf = open(status_fname)
  
  options = {} # {option_name ->(optionarg1, optionarg2)}
  powers = []  # [(country, race, units, scs)]
  
  # units : [(unitname, (attr1, attr2, attr3))]
  # scs : [sc1, sc2, ...]

  power = []
  units = []
  scs = []
  for line in inf:
    line = line.strip()
    if not line or not line[0].isalpha():
      continue

    if line.endswith(":"):
      if power:
        power.append(units)
        power.append(scs)
        powers.append(power)
        power, units, scs = [], [], []

      line = line[:-1] # lose final :

      country, race = line.split(None)
      assert race.startswith("(") and race.endswith(")")
      race = race[1:-1] # lose parens
      power = [country, race]

    else:

      try:
        name, attrs = line.split(None, 1)
      except ValueError:
        name, attrs = line, ""

      attrs = attrs.split()
      if power:
        if not attrs or all(attr.upper() in provinces for attr in attrs):
          scs.append(name.upper())
          scs.extend([attr.upper() for attr in attrs]) 
        else:
          units.append((name.upper(), attrs))
      else:
        options[name]=attrs

  if power:
    power.append(units)
    power.append(scs)
    powers.append(power)

  return options, powers

def choose_loc(mode, coast, a, f, fs):
  if mode == "Fleet":
    if coast == "Secondary":
      return fs
    return f
  if mode == "Army":
    return a

  if a == ILLEGAL_PLACEMENT:
    return f
  return a

def get_image_fname(datafilesdir, race, mode, enterprise, trader,
                    cloaked, infiltrated, assimilated):
  """ given info on the unit, try and get a picture for it """

  
  fn = "%s_%s" % (race, mode)
  if enterprise:
    fn += "_Enterprise"
  if trader:
    fn += "_Trader"
  if cloaked:
    fn += "_Cloaked"
  if infiltrated:
    fn += "_Infiltrated"
  if assimilated:
    fn += "_" + assimilated
  fn += ".png"

  fn = os.path.join(datafilesdir,ICONS, fn)

  if os.path.exists(fn):
    return fn
  print "Missing", fn
  return None

def draw_powers(datafilesdir, powers, coords, draw, im):
  """ modify im to represent powers """
  
  used = set()

  draw_fnames = {}

  debug_interpret_locs = {}
  
  for country, race, units, scs in powers:
    for unitname, attrs in units:
      n, a, f, fs = coords[unitname]

      coast, mode, enterprise, infiltrated, cloaked, trader, assimilated, disloged = None, None, False, False, False, False, None, None

      other_attrs = []
      for attr in attrs:
        o_attr = attr
        attr = attr.lower()
        if attr in ["(sc)", "(wc)"]:
          coast = "Secondary"
        elif attr in ["(nc)", "(ec)"]:
          pass
        elif attr == "army":
          mode = "Army"
        elif attr == "fleet":
          mode = "Fleet"
        elif attr == "flarmy":
          mode = "Flarmy"
        elif attr == "infiltrated":
          infiltrated = True
        elif attr == "cloaked":
          cloaked = True
        elif attr == "trader":
          trader = True
        elif attr == "enterprise":
          enterprise = True
        elif o_attr.startswith("Assimilated("):
          assimilated = o_attr
        elif o_attr.startswith("Dislodged"):
          disloged = o_attr
        else:
          assert "Disloged" not in o_attr
          other_attrs.append(o_attr)

      loc = choose_loc(mode, coast, a, f, fs)

      color=colors[race]

      image_fname = None
      if use_images:
        image_fname = get_image_fname(datafilesdir, race, mode, enterprise, trader, cloaked, infiltrated, assimilated)

      if not image_fname:
        """ if we don't have some icons, draw ovals instead """
        
        while loc in used:
          loc = add(loc, (12, 12))
        used.add(loc)
        debug_interpret_locs[loc] = image_fname, unitname


        if mode == "Fleet":
          xy = [add(loc,(-5,-10)), add(loc,(5,10))]
        elif mode == "Army":
          xy = [add(loc,(-10,-5)), add(loc,(10,5))]
        else:
          xy = [add(loc,(-6,-6)), add(loc,(6,6))]

        if cloaked:
          draw.ellipse(xy, outline=color)
        else:
          draw.ellipse(xy, fill=color)

        if infiltrated:
          draw.ellipse([add(loc,(-1,-1)), add(loc,(1,1))], fill=(0,0,0))
        if trader:
          draw.line([loc[0], loc[1], loc[0], loc[1]-14], fill=(0,0,0))
      else:
        if loc not in draw_fnames:
          draw_fnames[loc] = ["","",""]
          debug_interpret_locs[loc] = image_fname, unitname
        sort = 0 #"normal"
        if trader:
          sort = 1 #"trader"
        elif disloged:
          sort = 2 #"disloged"
        draw_fnames[loc][sort] = image_fname

      if other_attrs:
        txt = "(%s)" % " ".join(attr[0].upper() for attr in other_attrs)
        draw.text(add(loc,(10,-5)),txt,fill=color)

  for loc, (normal, trader, disloged) in draw_fnames.items():
    t_loc = loc

    if normal:
      t_loc = add(loc, (0, -28))
    if trader:
      add_icon(im, trader, t_loc)
    if disloged:
      #assert normal
      add_icon(im, disloged, loc, offset=True)
    if normal:
      try:
        add_icon(im, normal, loc)
      except Exception:
        print loc, debug_interpret_locs[loc]
        raise

def dot(a,b):
  x0,y0=a
  x1,y1=b
  return x0*x1+y0*y1

def add(a,b):
  x0,y0=a
  x1,y1=b
  return x0+x1,y0+y1

def sub(a,b):
  x0,y0=a
  x1,y1=b
  return x0-x1,y0-y1

def mul(s, pt):
  x0,y0=pt
  return x0*s,y0*s

def perp(pt):
  # [x,y] . [ 0,1],
  #         [-1,0]
  x,y=pt
  return (-y, x)

def calculate_bezier(p, steps = 5000):
    """

    from http://www.pygame.org/wiki/BezierCurve with only small modifications
    
      Calculate a bezier curve from 4 control points and return a 
      list of the resulting points.
    
      The function uses the forward differencing algorithm described here: 
      http://www.niksula.cs.hut.fi/~hkankaan/Homepages/bezierfast.html
    
    """
    
    t = 1.0 / steps
    temp = t*t
    
    f = p[0]
    fd = mul(t, mul(3, sub(p[1], p[0])))
    fdd_per_2 = mul(temp, mul(3, add(sub(p[0], mul(2, p[1])), p[2])))
    fddd_per_2 = mul(t,
                     mul(temp,
                         mul(3,
                             add(mul(3,
                                     sub(p[1], p[2])),
                                 sub(p[3], p[0])))))

    
    fddd = add(fddd_per_2, fddd_per_2)
    fdd = add(fdd_per_2 , fdd_per_2)
    fddd_per_6 = mul(.33333, fddd_per_2)
    
    points = []
    for x in range(steps):
        points.append(f)
        f = add(add(add(f, fd), fdd_per_2), fddd_per_6)
        fd = add(add(fd, fdd), fddd_per_2)
        fdd = add(fdd, fddd)
        fdd_per_2 = add(fdd_per_2, fddd_per_2)
    points.append(f)
    return points

def distsq(a,b):
  """ the square of the distance from a to b """
  return (a[0]-b[0])*(a[0]-b[0])+(a[1]-b[1])*(a[1]-b[1])

def mkint(pt):
  x,y = pt
  return int(x),int(y)

def draw_wormhole(start,stop,img):
  """ make a bezier curve, color points near the bezier curve """
  
  sys.stderr.write("\nWormholeing...")

  st_a = mul(.4, sub(start,stop))
  st_b = mul(.2, sub(stop,start))
  
  c1=add(start, add(st_b, perp(mul(.5,st_b)))) 
  c2=add(stop, add(st_a, perp(mul(.5,st_a)))) 

  control_points = [start, c1, c2, stop]


  # for each point in a 14x14 square centered on each point on the
  # bezier curve, compute the minimum distance from that point to the
  # curve and put that info in all_points.  All points not in
  # all_pts.keys() should be left alone
  #
  all_pts = {} # pt -> dist to curve
  for x in range((len(control_points)-1)/3):
    b_points = calculate_bezier(control_points[3*x:3*x+4])
    for pt in b_points:
      for xx in range(-6,6):
        for yy in range(-6,6):
          d=xx*xx+yy*yy
          npt=mkint(add(pt,(xx,yy)))
          
          if npt not in all_pts or all_pts[npt] > d:
            all_pts[npt]=d

    sys.stderr.write(".")

  sys.stderr.write("\n\n")

  # now we have points and their distances to the curve.  color them
  # apropriately: no change right on the curve, darken the r and g as
  # we move away, then when we get too far fade back to no change
  for pt, d in all_pts.iteritems():

    # d is the distance squared from pt to the curve
    # r,g,b are the colors of the output pixel
    # alpha is how much to darken r and g by (range 0-1)
    r,g,b=img.getpixel(pt)

    alpha = d/20.0 # get darker proportional to the distance to the
                   # line squared, reaching 100% at sqrt(20) pixels
                   # away
                   
    if alpha > 1:
      # if we're all the way dark, go back towards the light
      alpha = 1-(alpha/2)
    if alpha < 0:
      # if we're all the way light, make no change
      alpha = 0

    alpha = (alpha)/6 # instead of darkening all the way, darken only 1/6

    assert 0<=alpha<=1 

    r,g,b=int(r-255*(alpha)), int(g-255*(alpha)), b      

    img.putpixel(pt, (r,g,b))
  sys.stderr.write("\n")


def draw_background(coords, powers, draw, img, options):
  """ modify img to show sc ownership, province names, and the wormhole """

  ownership = {}
  for country, race, units, scs in powers:
    for sc in scs:
      ownership[sc] = colors[race]

  if use_flood_fill:
    sys.stderr.write("\nFlood Filling")
    for name, (n, a, f, fs) in coords.items():
      if name in ownership:
        color = ownership[name]
        flood_fill(img, n, color)
        sys.stderr.write(".")
    sys.stderr.write("\n")

  if "Wormhole" in options:
    a, b = options["Wormhole"]
    start =  coords[a.upper()][0]
    stop = coords[b.upper()][0]
    draw_wormhole(start, stop, img)

  if use_names:
    for name, (n, a, f, fs) in coords.items():
      color = (0,0,0)
      if name in ownership and not flood_fill:
        color = ownership[name]
      draw.text(n, name, fill=color)
    

def alpha_paste(img_base, img_add, xyoffset):
  """ img.paste ignores the alpha channel, so we do it by hand """
  
  from_x_max, from_y_max = img_add.size

  def blend(a_color, b_color, alpha):
    return (a_color*alpha + b_color*(255-alpha))/255

  for x in range(from_x_max):
    for y in range(from_y_max):
      
      ar,ag,ab,aa = img_add.getpixel((x,y))
      br,bg,bb = img_base.getpixel(add((x,y), xyoffset))

      if aa < 5: # if it's almost all the way transparent, make it all the
                 # way
        aa = 0

      r,g,b,a = blend(ar,br,aa), blend(ag,bg,aa), blend(ab,bb,aa), 255

      img_base.putpixel(add((x,y), xyoffset), (r,g,b,a))

def within(img, x, y):
  img_x, img_y = img.size
  return 0 <= x < img_x and 0 <= y <= img_y

def flood_fill(image, loc, value):
  """ Flood fill on a region (not in old PIL)

  modified from http://article.gmane.org/gmane.comp.python.image/1753

  """
  x,y = loc
  
  if not within(image,x, y):
    return

  orig_color = image.getpixel((x, y))
  if orig_color == value:
    return
  
  edge = [(x, y)]
  image.putpixel((x, y), value)
  while edge:
    newedge = []
    for (x, y) in edge:
      for (s, t) in ((x+1, y), (x-1, y), (x, y+1), (x, y-1)):
        if within(image, s, t) and image.getpixel((s, t)) == orig_color:
          image.putpixel((s, t), value)
          newedge.append((s, t))
    edge = newedge

def real_size(ico):
  """ compute the size of the part of the image having alpha > 5 """
  
  x_max, y_max = ico.size

  rx_min, rx_max = x_max/2, x_max/2
  ry_min, ry_max = y_max/2, y_max/2

  for x in range(x_max):
    for y in range(y_max):
      r,g,b,a=ico.getpixel((x,y))
      if a >= 5:
        if x < rx_min:
          rx_min = x
        if x > rx_max:
          rx_max = x
        if y < ry_min:
          ry_min = y
        if y > ry_max:
          ry_max = y
  return rx_max-rx_min, ry_max-ry_min


def draw_standoffs(datafilesdir, coords, places, draw, im):
  for place in places:
    n, a, f, fs = coords[place.upper()]
    loc = choose_loc(None, None, a, f, fs)
    add_icon(im, os.path.join(datafilesdir,ICONS,"Standoff.png"), loc)
    
  
def add_icon(im, iconfname, loc, offset=False):
  """ add the icon in iconfname to im at loc

  if offset, adjust position by 1/3 of the real width and height

  """
  
  ico = Image.open(iconfname).convert()
  x,y = loc
  x_max, y_max = ico.size

  loc = x-x_max/2, y-y_max/2

  if offset:
    real_w, real_h = real_size(ico)
    loc = loc[0]+real_w/3, loc[1]+real_h/3

  alpha_paste(im, ico, loc)
  
def start(datafilesdir, status_fname, img_out):
  coords = parse_coords(os.path.join(datafilesdir,COORDS))
  options, powers = parse_status(status_fname, coords)

  im = Image.open(os.path.join(datafilesdir,IMAGE)).convert()
        
  draw = ImageDraw.Draw(im)
  draw_background(coords, powers, draw, im, options)
  draw_powers(datafilesdir, powers, coords, draw, im)

  if "PlacesCannotRetreatTo" in options:
    draw_standoffs(datafilesdir, coords, options["PlacesCannotRetreatTo"], draw, im)
  
  im.save(img_out)

if __name__ == "__main__":
  start(*sys.argv[1:])
