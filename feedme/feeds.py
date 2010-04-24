import feedparser
import logging
import urllib2
import re
import htmlentitydefs

from BeautifulSoup import BeautifulSoup

from google.appengine.api.urlfetch import fetch
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db

from models import *

class UrlResponse:
    is_valid = False
    new_url = None
    response = None

class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    perm_redirect = False
    
    def http_error_301(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_301(self, req, fp, code, msg, headers)
        logging.info("Result: %s" % result)
        self.perm_redirect = True
        return result

def download_feed(url):
    url_response = UrlResponse()
    
    redirect_handler = SmartRedirectHandler()
    opener = urllib2.build_opener(redirect_handler)
    f = opener.open(urllib2.Request(url))
    
    if redirect_handler.perm_redirect:
        url_response.new_url = f.url
    url_response.is_valid = f.code >= 200 and f.code < 300
    url_response.response = f.read()
    
    f.close()
    return url_response

def create_feed(url):
    feed = Feed.get_or_insert(url)
    feed.url = url
    
    url_response = download_feed(feed.url)
    if not url_response.is_valid:
        return 1
    elif url_response.new_url:
        #If this feed has been permenantly redirected, update the URL
        feed.url = url_response.new_url

    #Load the URL
    logging.info("Got feed: %s" % feed)

    #Load the feed url into the feedparser
    parser = feedparser.parse(url_response.response)
    
    if parser.feed:
        if parser.feed.has_key('title'):
            feed.title = parser.feed.title
        
        feed.text = ''
        feed.put()
        #Add feed to task queue
        task = taskqueue.Task(url='/getfeed', params={'key': feed.key()}, countdown='10')
        task.add()
        if task.was_enqueued:
            feed.scheduled_for = task.eta
            feed.put()
        else:
            #Something's wrong with the task queue
            return 2
    else:
        #something's wrong with this feed; return with error code 1
        return 1
        
    return 0;

#
# Removes HTML or XML character references and entities from a text string.
#
# @param text The HTML (or XML) source text.
# @return The plain text, as a Unicode string, if necessary.
def unescape(text):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    a = unichr(int(text[2:-1]))
                    #print repr(a)
                    return a
            except ValueError:
                pass
        else:
            # named entity
            try:
                #Convert non-breaking spaces to real spaces to make searching easier
                if text == "&nbsp;":
                    text = " "
                else:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)
    
def contains_keyword(map, key, keyword):
    if not map.has_key(key):
        return False
    #Get the text from the map
    alltext = map.get(key)
    #Remove new lines
    alltext = re.sub(r'[\n\r]', "", alltext)
    #Strip out all html tags
    alltext = ''.join(BeautifulSoup(alltext).findAll(text=True))
    #Unescape HTML/XML encoded chars
    alltext = unescape(alltext)
    #Search the string
    return alltext.find(keyword) >= 0

def get_feed(keyname):
    feed = db.get(db.Key(keyname))
    logging.info('the feed: %s' % feed)
    #If the feed doesn't exist, we just ignore this request
    if feed:
        #Download the feed
        url_response = download_feed(feed.url)
        if not url_response.is_valid:
            #Disable the feed and send an alert
            return 1
        elif url_response.new_url:
            #If this feed has been permenantly redirected, update the URL
            feed.url = url_response.new_url
        
        parser = feedparser.parse(url_response.response)
        logging.info(parser.feed)
        logging.info(parser.entries[0])
        
        search_term = "Science & Environment"
        term_found = False
        section_found = None
        
        for entry in parser.entries:
            for entry_key in ['title', 'author', 'summary']:
                if contains_keyword(entry, entry_key, search_term):
                    term_found = True
                    section_found = entry_key
                    break
            if term_found: break
            if entry.has_key('content'):
                for content in entry.content:
                    if contains_keyword(content, 'value', search_term):
                        term_found = True
                        section_found = 'content'
                        break
            if term_found: break
            if entry.has_key('tags'):
                for tag in entry.tags:
                    if contains_keyword(tag, 'term', search_term):
                        term_found = True
                        section_found = 'tags'
                        break
            if term_found: break
            
        if term_found:
            logging.info("Found term %s in section %s" % (search_term, section_found))
        else:
            logging.info("Search term %s not found" % search_term)
            
        