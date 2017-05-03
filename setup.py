from distutils.core import setup

try:
   import pypandoc
   description = pypandoc.convert('README.md', 'rst')
   description = long_description.replace("\r","")
except (IOError, ImportError):
   description = 'Simple websocket implementation in python using asyncio'
    
setup(
  name = 'simple_ws',
  packages = ['simple_ws'], 
  version = '0.2.1',
  long_description = description,
  author = 'Ole Kristian Aune, Even Dalen, Audun Wigum Arbo',
  author_email = 'even.dalen@live.no',
  url = 'https://github.com/WSnettverksprog/simple_ws', 
  download_url = 'https://github.com/WSnettverksprog/simple_ws/archive/0.1.tar.gz', 
  keywords = ['websocket', 'ws', 'asyncio', 'simple'], 
)
