from PIL import Image
import os, sys

f = '/tmp/rel2_final.png'
ab = os.path.abspath(f)
if not os.path.exists(f):
    print('no file'); sys.exit(1)
im = Image.open(f)
print('orig', im.size)
im.thumbnail((900, 900))
out = os.path.join(os.path.dirname(ab), 'preview_rel2.png')
im.save(out)
print('saved', out, im.size)
