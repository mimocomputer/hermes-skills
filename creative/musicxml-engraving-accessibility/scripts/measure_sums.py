from lxml import etree
import sys

t = etree.parse(sys.argv[1])
root = t.getroot()
div = int(root.findtext('part/measure/attributes/divisions') or 1)
print('divisions per quarter:', div)
for pi, part in enumerate(root.findall('part')):
    print('part', pi + 1)
    for m in part.findall('measure')[:4]:
        total = {}
        cur = None
        for el in m:
            if el.tag == 'backup':
                cur = None
                continue
            if el.tag != 'note':
                continue
            key = el.findtext('voice')
            d = int(el.findtext('duration'))
            if el.find('chord') is None:
                total[key] = total.get(key, 0) + d
        print('  m', m.get('number'), {k: round(v / div, 3) for k, v in total.items()})
