import os
import logging

from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import memcache

from feeds import *
from models import *


errormap = {'1': 'Error retrieving feed. Check the URL is correct.',
            '2': 'Error scheduling feed task.'}

class MainPage(webapp.RequestHandler):
    def get(self):
        feeds = Feed.all()

        if users.get_current_user():
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        
        template_values = {
            'feeds': feeds,
            'url': url,
            'url_linktext': url_linktext,
            'error_message': errormap.get(self.request.get('e')),
            }

        path = os.path.join(os.path.dirname(__file__) + '/../templates/', 'index.html')
        self.response.out.write(template.render(path, template_values))

class AddFeed(webapp.RequestHandler):
    
    def post(self):
        error_code = create_feed(self.request.get('feedurl'))
        if error_code != 0:
            self.redirect('/?e=%s' % error_code)
        else:
            #Add this feed to the task queue
            self.redirect('/')

class GetFeed(webapp.RequestHandler):
    def post(self):
        get_feed(self.request.get('key'))
        
        