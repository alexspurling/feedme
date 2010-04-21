import cgi
import os
import feedparser

from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache

class Feed(db.Model):
    url = db.StringProperty()
    title = db.StringProperty()
    text = db.TextProperty()

class MainPage(webapp.RequestHandler):
    def get(self):
        feeds = Feed.all()

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        
        errormap = {'1': 'Error retrieving feed. Check the URL is correct.'}
        error_message = None
        error_code = self.request.get('e')
        if error_code:
            error_message = errormap.get(error_code)
            
        template_values = {
            'feeds': feeds,
            'url': url,
            'url_linktext': url_linktext,
            'error_message': error_message,
            }

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, template_values))

class AddFeed(webapp.RequestHandler):
        
    def post(self):
        feed = Feed()
        feed.url = self.request.get('feedurl')
        parser = feedparser.parse(feed.url)
        error_code = 0
        if parser.feed:
            if parser.feed.has_key('title'):
                feed.title = parser.feed.title
            feed.put()
        else:
            #something's wrong with this feed
            error_code = 1
        
        if error_code > 0:
            self.redirect('/?e=%s' % error_code)
        else:
            self.redirect('/')

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/addfeed', AddFeed)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()