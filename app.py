#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import babel
import dateutil.parser
import logging
import json

from datetime import datetime
from helpers import Fillable, csv
from flask import Flask, Response, request, abort, flash, redirect, render_template, url_for
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import Form
from forms import *
from logging import Formatter, FileHandler
from sys import exc_info

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(Fillable, db.Model):
    __tablename__ = 'Venue'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.Text())

    shows = db.relationship('Show', backref='venue')

    def to_minimal_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'num_upcoming_shows': Show.query.filter(Show.venue == self, Show.start_time > datetime.now()).count()
        }

    def to_form_dict(self):
        return {
            'name': self.name,
            'genres': csv(self.genres),
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'website': self.website,
            'facebook_link': self.facebook_link,
            'seeking_talent': self.seeking_talent,
            'seeking_description': self.seeking_description,
            'image_link': self.image_link,
        }

    def to_dict(self):
        past_shows = []
        upcoming_shows = []
        
        for show in self.shows:
            show_dict = show.to_artist_dict()

            if show.start_time > datetime.now():
                upcoming_shows.append(show_dict)
            else: past_shows.append(show_dict)

        return {
            'id': self.id,
            'name': self.name,
            'genres': csv(self.genres),
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'website': self.website,
            'facebook_link': self.facebook_link,
            'seeking_talent': self.seeking_talent,
            'seeking_description': self.seeking_description,
            'image_link': self.image_link,
            'past_shows': past_shows,
            'upcoming_shows': upcoming_shows,
            'past_shows_count': len(past_shows),
            'upcoming_shows_count': len(upcoming_shows),
        }

class Artist(Fillable, db.Model):
    __tablename__ = 'Artist'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120), nullable=False)
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.Text())

    shows = db.relationship('Show', backref='artist')

    def to_index_dict(self):
        return { 'id': self.id, 'name': self.name }
    
    def to_search_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'num_upcoming_shows': Show.query.filter(Show.artist == self, Show.start_time > datetime.now()).count()
        }

    def to_form_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'genres': csv(self.genres),
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'website': self.website,
            'facebook_link': self.facebook_link,
            'seeking_venue': self.seeking_venue,
            'seeking_description': self.seeking_description,
            'image_link': self.image_link
        }
    
    def to_dict(self):
        past_shows = []
        upcoming_shows = []

        for show in self.shows:
            show_dict = show.to_venue_dict()

            if show.start_time > datetime.now():
                upcoming_shows.append(show_dict)
            else: past_shows.append(show_dict)

        return {
            'id': self.id,
            'name': self.name,
            'genres': csv(self.genres),
            'city': self.city,
            'state': self.state,
            'phone': self.phone,
            'website': self.website,
            'facebook_link': self.facebook_link,
            'seeking_venue': self.seeking_venue,
            'seeking_description': self.seeking_description,
            'image_link': self.image_link,
            'past_shows': past_shows,
            'upcoming_shows': upcoming_shows,
            'past_shows_count': len(past_shows),
            'upcoming_shows_count': len(upcoming_shows)
        }

class Show(Fillable, db.Model):
    __tablename__ = 'Show'
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'))
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'))
    start_time = db.Column(db.DateTime)

    def to_artist_dict(self):
        return {
            'artist_id': self.artist.id,
            'artist_name': self.artist.name,
            'artist_image_link': self.artist.image_link,
            'start_time': self.start_time
        }

    def to_venue_dict(self):
        return {
            'venue_id': self.venue.id,
            'venue_name': self.venue.name,
            'venue_image_link': self.venue.image_link,
            'start_time': self.start_time
        }
    
    def to_dict(self):
        return {
            'venue_id': self.venue.id,
            'venue_name': self.venue.name,
            'artist_id': self.artist.id,
            'artist_name': self.artist.name,
            'artist_image_link': self.artist.image_link,
            'start_time': self.start_time
        }

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    
    date = dateutil.parser.parse(value) if not isinstance(value, datetime) else value
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    venues = Venue.query.all()
    areas = []

    for venue in venues:
        try:
            area = next(a for a in areas if a['city'] == venue.city and a['state'] == venue.state)
        except StopIteration:
            area = {
                'city': venue.city,
                'state': venue.state,
                'venues': []
            }
            areas.append(area)

        area['venues'].append(venue.to_minimal_dict())
    
    return render_template('pages/venues.html', areas=areas)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = request.form.get('search_term', '')

    if search_term:
        words = search_term.split()
        matches = Venue.query.filter(*(Venue.name.ilike(f'%{word}%') for word in words)).all()
    else: matches = []

    results = {
        "count": len(matches),
        "data": [venue.to_minimal_dict() for venue in matches]
    }

    return render_template('pages/search_venues.html', results=results, search_term=search_term)


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue: abort(404)
    return render_template('pages/show_venue.html', venue=venue.to_dict())

#  Create Venue
#  ----------------------------------------------------------------


@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    venue = Venue()
    venue.fill(_except=['id', 'genres'], **request.form)
    venue.genres = ','.join(request.form.getlist('genres'))
    venue_id = None

    try:
        db.session.add(venue)
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully listed!')
    except:
        print(exc_info())
        db.session.rollback()
        flash('An error occurred. Venue ' + venue.name + ' could not be listed.')
    finally:
        db.session.close()
    
    if venue_id: return redirect(url_for('show_venue', venue_id=venue_id))
    return redirect(url_for('index'))


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue: abort(404)

    try:
        db.session.delete(venue)
        db.session.commit()
    except:
        print(exc_info())
        db.session.rollback()
    finally:
        db.session.close()

    return ''

#  Artists
#  ----------------------------------------------------------------


@app.route('/artists')
def artists():
    artists = [artist.to_index_dict() for artist in Artist.query.all()]
    return render_template('pages/artists.html', artists=artists)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = request.form.get('search_term', '')

    if search_term:
        words = search_term.split()
        matches = Artist.query.filter(*(Artist.name.ilike(f'%{word}%') for word in words)).all()
    else: matches = []

    results = {
        "count": len(matches),
        "data": [artist.to_search_dict() for artist in matches]
    }

    return render_template('pages/search_artists.html', results=results, search_term=search_term)


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist: abort(404)
    return render_template('pages/show_artist.html', artist=artist.to_dict())

#  Update
#  ----------------------------------------------------------------


@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist: abort(404)
    form = ArtistForm(**artist.to_form_dict())
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    artist = Artist.query.get(artist_id)
    if not artist: abort(404)

    try:
        artist.fill(_except=['id', 'genres'], **request.form)
        if 'genres' in request.form: artist.genres = ','.join(request.form.getlist('genres'))
        db.session.commit()
        flash('Artist ' + artist.name + ' was successfully updated!')
    except:
        print(exc_info())
        db.session.rollback()
        flash('An error occurred. Artist ' + artist.name + ' could not be updated.')
    finally:
        db.session.close()

    return redirect(url_for('show_artist', artist_id=artist_id))


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue: abort(404)
    form = VenueForm(**venue.to_form_dict())
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get(venue_id)
    if not venue: abort(404)

    try:
        venue.fill(_except=['id', 'genres'], **request.form)
        if 'genres' in request.form: venue.genres = ','.join(request.form.getlist('genres'))
        db.session.commit()
        flash('Venue ' + venue.name + ' was successfully updated!')
    except:
        print(exc_info())
        db.session.rollback()
        flash('An error occurred. Venue ' + venue.name + ' could not be updated.')
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------


@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    artist = Artist()
    artist.fill(_except=['id', 'genres'], **request.form)
    artist.genres = ','.join(request.form.getlist('genres'))
    artist_id = None

    try:
        db.session.add(artist)
        db.session.commit()
        artist_id = artist.id
        flash('Artist ' + artist.name + ' was successfully listed!')
    except:
        print(exc_info())
        db.session.rollback()
        flash('An error occurred. Venue ' + artist.name + ' could not be listed.')
    finally:
        db.session.close()
    
    if artist_id: return redirect(url_for('show_artist', artist_id=artist_id))
    return redirect(url_for('index'))


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    shows = [show.to_dict() for show in Show.query.all()]
    return render_template('pages/shows.html', shows=shows)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    show = Show()
    show.fill(_except=['id'], **request.form)

    try:
        db.session.add(show)
        db.session.commit()
        flash('Show was successfully listed!')
    except:
        print(exc_info())
        db.session.rollback()
        flash('An error occurred. Show could not be listed.')
    finally:
        db.session.close()
    
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
