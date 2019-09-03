# -*- coding: utf-8 -*-
import cherrypy

from . import describe
from .v1 import activity, activity_set, api_key, applet, assetstore, file,     \
    collection, context, folder, group, item, resource, response, screen,      \
    system, token, user, notification


class ApiDocs(object):
    exposed = True

    def GET(self):
        # Since we only have v1 right now, just redirect to the v1 page.
        # If we get more versions, this should show an index of them.
        raise cherrypy.HTTPRedirect(cherrypy.url() + '/v1')


def addApiToNode(node):
    node.api = ApiDocs()
    _addV1ToNode(node.api)

    return node


def _addV1ToNode(node):
    node.v1 = describe.ApiDocs()
    node.v1.describe = describe.Describe()
    node.v1.activity = activity.Activity()
    node.v1.activity_set = activity_set.ActivitySet()
    node.v1.api_key = api_key.ApiKey()
    node.v1.applet = applet.Applet()
    node.v1.assetstore = assetstore.Assetstore()
    node.v1.collection = collection.Collection()
    node.v1.context = context.Context()
    node.v1.file = file.File()
    node.v1.folder = folder.Folder()
    node.v1.group = group.Group()
    node.v1.item = item.Item()
    node.v1.notification = notification.Notification()
    node.v1.resource = resource.Resource()
    node.v1.response = response.ResponseItem()
    node.v1.screen = screen.Screen()
    node.v1.system = system.System()
    node.v1.token = token.Token()
    node.v1.user = user.User()

    return node
