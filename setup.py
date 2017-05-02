from distutils.core import setup
setup(
  name = 'simple_ws',
  packages = ['simple_ws'], # this must be the same as the name above
  version = '0.1',
  description = 'Simple websocket implementation in python using asyncio',
  author = 'Ole Kristian Aune, Even Dalen, Audun Wigum Arbo',
  author_email = 'even.dalen@live.no',
  url = 'https://github.com/WSnettverksprog/python-WS', # use the URL to the github repo
  download_url = 'https://github.com/WSnettverksprog/python-WS/archive/0.1.tar.gz', # I'll explain this in a second
  keywords = ['websocket', 'ws', 'asyncio', 'simple'], # arbitrary keywords
  classifiers = [],
)