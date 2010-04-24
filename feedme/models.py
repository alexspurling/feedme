from google.appengine.ext import db

class Feed(db.Model):
    url = db.StringProperty()
    title = db.StringProperty()
    text = db.TextProperty()
    scheduled_for = db.DateTimeProperty()

