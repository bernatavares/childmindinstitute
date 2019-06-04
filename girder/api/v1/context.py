#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from ..describe import Description, autoDescribeRoute
from ..rest import Resource
from ast import literal_eval
from girder.api import access, rest
from girder.constants import TokenScope
from girder.exceptions import ValidationException
from girder.models.collection import Collection as CollectionModel
from girder.models.folder import Folder as FolderModel
from girder.utility import jsonld_expander
import itertools


class Context(Resource):
    """API Endpoint for folders."""

    def __init__(self):
        super(Context, self).__init__()
        self.resourceName = 'context'
        self._model = FolderModel()
        self.route('GET', (), self.getContext)
        self.route('GET', ('skin',), self.getSkin)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get JSON-LD Context for this Mindlogger Database.')
        .errorResponse()
    )
    def getContext(self):
        """
        Get a list of folders with given search parameters. Currently accepted
        search modes are:

        1. Searching by parentId and parentType, with optional additional
           filtering by the name field (exact match) or using full text search
           within a single parent folder. Pass a "name" parameter or "text"
           parameter to invoke these additional filters.
        2. Searching with full text search across all folders in the system.
           Simply pass a "text" parameter for this mode.
        """
        context = FolderModel().findOne({
            'name': 'JSON-LD',
            'parentCollection': 'collection',
            'parentId': CollectionModel().findOne({
                'name': 'Context'
            }).get('_id')
        })
        if context:
            return (context.get('meta', {}))
        user = self.getCurrentUser()
        context = FolderModel().setMetadata(
            folder=FolderModel().createFolder(
                parent=CollectionModel().createCollection(
                    name="Context",
                    creator=user,
                    public=True,
                    reuseExisting=True
                ),
                name="JSON-LD",
                parentType='collection',
                public=True,
                creator=user,
                reuseExisting=True
            ),
            metadata={
                "@context": {
                    "@language": "en-US",
                    "@base": rest.getApiUrl()
                }
            }
        )
        return (context.get('meta', {}))

    @access.public
    @autoDescribeRoute(
        Description('Get the application skinning information for this server.')
        .param(
            'lang',
            'Language of skin to get. Must follow <a href="https://tools.ietf.org/html/bcp47">BCP 47</a>',
            default='@context.@language',
            required=False
        )
    )
    def getSkin(self, lang):
        skinFolder = FolderModel().findOne({
            'name': 'Skin',
            'parentCollection': 'collection',
            'parentId': CollectionModel().findOne({
                'name': 'Context'
            }).get('_id')
        })
        skin = skinFolder.get('meta', {
            'name': '',
            'colors': {
                'primary': '#000000',
                'secondary': '#FFFFFF'
            },
            'about': ''
        })
        for s in ['name', 'about']:
            lookup = jsonld_expander.getByLanguage(
                skin[s],
                lang if lang and lang not in [
                    "@context.@language",
                    ""
                ] else None
            )
            skin[s] = lookup if lookup and lookup not in [
                None,
                [{}],
            ] else jsonld_expander.getByLanguage(
                skin[s],
                None
            )
            skin[s] = jsonld_expander.fileObjectToStr(skin[s][0]) if isinstance(
                skin[s],
                list
            ) and len(skin[s]) else skin[s]
        return (skin)
