#!/usr/bin/env python3
"""Held-out MarkupSafe source/native HTML attribute correspondence observer.
This adapter does not alter frozen cross-domain V1 rules."""
import html.parser,hashlib,json
from pathlib import Path
from markupsafe import Markup,escape

class Inspector(html.parser.HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.attrs=[]
 def handle_starttag(self,tag,attrs):
  if tag=='div':self.attrs.append(attrs)

source='x" onmouseover="alert(1)'
def examine(value):
 s='<div data-v="'+str(value)+'"></div>'
 parser=Inspector();parser.feed(s);parser.close()
 attr=parser.attrs[0] if len(parser.attrs)==1 else []
 return {'html':s,'attributes':attr,'relation':len(parser.attrs)==1 and len(attr)==1 and attr[0]==('data-v',source)}
h1=examine(escape(source))
h2=examine(Markup(source))
assert h1['relation'] is True, h1
assert h2['relation'] is False, h2
assert any(k=='onmouseover' for k,v in h2['attributes']),h2
# Frozen protocol rules: without independent interpretation, no positive warrant.
decisions={'H1':'WARRANTED_BOUNDED','H2':'REJECTED_BOUNDED','H3':'UNKNOWN'}
dependency={'H1':['html-attribute-relation','source-revision','escape-native','html-parser-oracle'],
            'H2':['html-attribute-relation','source-revision','markup-native','html-parser-oracle'],
            'H3':[]}
def withdraw(authority):
 return {k:('UNKNOWN_WITHDRAWN' if authority in dependency[k] else value) for k,value in decisions.items()}
assert [k for k in decisions if withdraw('escape-native')[k]!=decisions[k]]==['H1']
assert [k for k in decisions if withdraw('markup-native')[k]!=decisions[k]]==['H2']
assert [k for k in decisions if withdraw('html-parser-oracle')[k]!=decisions[k]]==['H1','H2']
assert withdraw('source-revision')['H3']=='UNKNOWN'
result={'status':'WARRANTED_BOUNDED_THIRD_ADAPTER_IF_NATIVE_CI_GREEN',
        'protocol_sha':'9c8b427c679398fd80ea56d9a91a1627b2e96b6d',
        'preregistration_sha':'662b595768d1af4aeb429fbbb3841578c21cecc1',
        'source_sha':'4e111271b1494995708a9e878a10829b5e10c7ba',
        'source_input_sha256':hashlib.sha256(source.encode()).hexdigest(),
        'observer':'Python html.parser HTMLParser independent of MarkupSafe; attribute context only',
        'H1':h1,'H2':h2,'H3':'NO_INTERPRETATION_RELATION',
        'decisions':decisions,
        'withdraw_escaped':withdraw('escape-native'),
        'withdraw_markup':withdraw('markup-native'),
        'withdraw_oracle':withdraw('html-parser-oracle'),
        'limitations':'Expert-supplied relation. No autonomous interpretation acquisition or general browser security result.'}
Path('verified').mkdir(exist_ok=True)
Path('verified/third-source.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print('HELD_OUT_MARKUPSAFE_OBSERVER_PASS')
