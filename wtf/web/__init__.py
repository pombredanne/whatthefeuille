from collections import namedtuple
import datetime
from uuid import uuid4

from pyramid.config import Configurator
from pyramid.decorator import reify
from pyramid.request import Request as BaseRequest
from pyramid.security import authenticated_userid

from pyes.query import FieldQuery, FieldParameter
from pyramid_beaker import session_factory_from_settings

from wtf import logger


class Request(BaseRequest):
    """
    Custom request class
    """

    @reify
    def db(self):
        """
        Get the Elastic Search connection
        """
        settings = self.registry.settings
        return settings['elasticsearch']

    @reify
    def user(self):
        """
        Get the logged in user
        """
        email = authenticated_userid(self)
        if email is not None:
            query = FieldQuery(FieldParameter('email', email))
            res = self.db.search(query)
            if len(res) == 0:
                doc = {
                    'id': str(uuid4()),
                    'email': email,
                    'registered': datetime.datetime.utcnow(),
                }
                res = self.db.index(doc, 'users', 'usertype', doc['id'])
                if res['ok'] == False:
                    logger.error("Signup failure")
                    logger.error(res)
                    raise HTTPServerError()
                self.db.refresh()
                res = [namedtuple('User', doc.keys())(**doc)]

            if len(res) > 0:
                return res[0]

        return None


def main(global_config, **settings):
    # defaults
    if 'mako.directories' not in settings:
        settings['mako.directories'] = 'wtf:templates'

    session_factory = session_factory_from_settings(settings)

    # creating the config
    config = Configurator(settings=settings, session_factory=session_factory)

    config.include('wtf.models')

    # thumbs
    config.include('wsgithumb')
    config.add_thumb_view('thumbs')

    # Use our custom Request class
    config.set_request_factory(Request)

    # routing
    config.add_route('index', '/')
    config.add_route('profile', '/profile')
    config.add_route('logout', '/logout')
    config.add_route('about', '/about')
    config.add_route('upload', '/upload')
    config.add_route('upload_plant', '/upload_plant')
    config.add_route('upload_plant_snaps', '/upload_plant_snaps')
    config.add_route('snapshot', '/snapshot/{file:.*}')
    config.add_route('warped', '/warped/{file:.*}')
    config.add_route('pick', '/pick')
    config.add_route('picture', '/picture/{file:.*}')
    config.add_route('plants', '/plant')
    config.add_route('plant', '/plant/{name:.*}')

    config.add_static_view('media', 'wtf:media/')

    config.scan("wtf.web.views")
    return config.make_wsgi_app()
