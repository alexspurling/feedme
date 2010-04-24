from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from feedme.views import *

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/addfeed', AddFeed),
                                      ('/getfeed', GetFeed)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()