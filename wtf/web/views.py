import os
import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import (
    HTTPFound,
    HTTPNotFound,
    HTTPServerError,
)
from pyramid.response import FileResponse
from pyramid.security import authenticated_userid, forget
from pyramid.exceptions import Forbidden

from mako.lookup import TemplateLookup

from pyes.query import FieldQuery, FieldParameter


import wtf


import logging
log = logging.getLogger(__name__)


TOPDIR = os.path.dirname(wtf.__file__)
MEDIADIR = os.path.join(TOPDIR, 'media')
TMPLDIR = os.path.join(TOPDIR, 'templates')
TMPLS = TemplateLookup(directories=[TMPLDIR])
JOBTIMEOUT = 3600    # one hour
DOCDIR = os.path.join(TOPDIR, 'docs', 'build', 'html')


def time2str(data):
    if data is None:
        return 'Unknown date'
    return datetime.datetime.fromtimestamp(data).strftime('%Y-%m-%d %H:%M:%S')


@view_config(route_name='index', request_method='GET', renderer='index.mako')
def index(request):
    """Index page."""

    return {
        'messages': request.session.pop_flash(),
        'user': request.user,
    }


@view_config(route_name='profile', request_method=('GET', 'POST'),
             renderer='profile.mako')
def profile(request):
    """Profile page."""
    return {'user': request.user}


@view_config(route_name='about_index')
def about_index(request):
    """Redirects / to /index.html"""
    return HTTPFound('/about/index.html')


@view_config(route_name='about_file')
def about_dir(request):
    """Returns Sphinx files"""
    filename = request.matchdict['file']
    elmts = filename.split(os.sep)
    for unsecure in ('.', '..'):
        if unsecure in elmts:
            return HTTPNotFound()

    path = os.path.join(DOCDIR, filename)
    return FileResponse(path, request)


@view_config(route_name='sign')
def sign(request):
    """Initiates a Browser-ID challenge."""
    email = authenticated_userid(request)
    if email is None:
        raise Forbidden()

    # Signup new user
    query = FieldQuery(FieldParameter('email', email))
    res = request.elasticsearch.search(query)
    if len(res) == 0:
        doc = {
            'email': email,
            'registered': datetime.datetime.utcnow(),
        }
        res = request.elasticsearch.index(doc, 'users', 'usertype')
        if res['ok'] == False:
            log.error("Signup failure")
            log.error(res)
            raise HTTPServerError()

    return HTTPFound(location='/')


@view_config(route_name='logout')
def logout(request):
    """Logs out."""
    headers = forget(request)
    request.session.flash("Logged out")
    return HTTPFound(location='/', headers=headers)
