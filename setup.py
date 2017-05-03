from distutils.core import setup

try:
   import pypandoc
   description = pypandoc.convert('README.md', 'rst')
except (IOError, ImportError):
   description = 'Simple websocket implementation in python using asyncio'
    
setup(
  name = 'simple_ws',
  packages = ['simple_ws'], 
  version = '0.2',
  description = description,
  author = 'Ole Kristian Aune, Even Dalen, Audun Wigum Arbo',
  author_email = 'even.dalen@live.no',
  url = 'https://github.com/WSnettverksprog/python-WS', 
  download_url = 'https://github.com/WSnettverksprog/python-WS/archive/0.1.tar.gz', 
  keywords = ['websocket', 'ws', 'asyncio', 'simple'], 
  classifiers = [],
)
