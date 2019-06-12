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

import copy
import datetime
import itertools
import json
import os
import six

from bson.objectid import ObjectId
from .activity import Activity as ActivityModel
from .applet import Applet
from .assignment import Assignment
from .folder import Folder as FolderModel
from .item import Item
from .model_base import AccessControlledModel
from girder import events
from girder.constants import AccessType
from girder.exceptions import ValidationException, GirderException
from girder.utility.progress import noProgress, setResponseTimeLimit
from girder.utility import loadJSON

class Screen(Item):
    def initialize(self):
        self.name = 'item'
        self.ensureIndices(('folderId', 'name', 'lowerName',
                            ([('folderId', 1), ('name', 1)], {})))
        self.ensureTextIndex({
            'name': 1,
            'description': 1
        })
        self.resourceColl = 'folder'
        self.resourceParent = 'folderId'

        self.exposeFields(level=AccessType.READ, fields=(
            '_id', 'size', 'updated', 'description', 'created', 'meta',
            'creatorId', 'folderId', 'name', 'baseParentType', 'baseParentId',
            'copyOfItem'))

    def createScreen(self, name, creator, activity=None, description='',
                     readOnly=False):
        """
        Create a new screen.

        :param name: The name of the item.
        :type name: str
        :param description: Description for the screen.
        :type description: str
        :param activity: The parent activity of the screen.
        :param creator: User document representing the creator of the screen.
        :type creator: dict
        :param readOnly: A ready-to-use screen
        :type readOnly: bool
        :returns: The screen item document that was created.
        """
        try:
            activity = ActivityModel().load(
                activity.get('_id', activity),
                level=AccessType.WRITE,
                user=creator
            )
        except:
            raise ValidationException(
                'Invalid Activity ID or inadequate access rights',
                'activity'
            )

        now = datetime.datetime.utcnow()

        if not isinstance(creator, dict) or '_id' not in creator:
            # Internal error -- this shouldn't be called without a user.
            raise GirderException('Creator must be a user.',
                                  'girder.models.item.creator-not-user')

        if 'baseParentType' not in activity:
            pathFromRoot = self.parentsToRoot({'folderId': activity['_id']},
                                              creator, force=True)
            activity['baseParentType'] = pathFromRoot[0]['type']
            activity['baseParentId'] = pathFromRoot[0]['object']['_id']

        return self.save({
            'name': self._validateString(name),
            'description': self._validateString(description),
            'folderId': ObjectId(activity['_id']),
            'creatorId': creator['_id'],
            'baseParentType': activity['baseParentType'],
            'baseParentId': activity['baseParentId'],
            'created': now,
            'updated': now,
            'size': 0,
            'readOnly': readOnly
        })


    def importUrl(self, url, user=None):
        """
        Gets a screen from a given URL, checks against the database, stores and
        returns that screen.
        """
        return(self.getFromUrl(url, 'screen', user))


    def load(self, id, level=AccessType.ADMIN, user=None):
        doc = super(Item, self).load(id=id, level=level, user=user)
        try:
            url = doc.get('meta', {}).get('url')
        except AttributeError:
            url = None
        if url:
            return(self.getFromUrl(url, 'screen', user))
        else:
            return(doc)
