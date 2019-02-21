#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2019 Child Mind Institute MATTER Lab
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
from ..rest import Resource, filtermodel, setResponseHeader, setContentDisposition
from datetime import datetime
from girder.utility import ziputil
from girder.constants import AccessType, TokenScope
from girder.exceptions import RestException
from girder.api import access
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item as ItemModel


class ResponseItem(Resource):

    def __init__(self):
        super(Item, self).__init__()
        self.resourceName = 'responseItem'
        self._model = ItemModel()
        self.route('POST', (), self.createResponseItem)


    @access.user(scope=TokenScope.DATA_WRITE)
    @filtermodel(model=ItemModel)
    @autoDescribeRoute(
        Description('Create a new user response item.')
        .responseClass('Item')
        .param('subject_id', 'The ID of the user that is the subject.',
               required=False, default=None)
        .jsonParam('metadata', 'A JSON object containing the metadata keys to add',
                   paramType='form', requireObject=True, required=False)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createResponseItem(self, subject_id, metadata):
        informant = self.getCurrentUser()
        subject_id = subject_id if subject_id is not None else informant
        now = datetime.now()
        UserResponsesFolder = Folder()._model.createFolder(
            parent={'_id': informant}, parentType='user', name='Responses',
            reuseExisting=True, public=False)
        UserSubjectResponsesFolder = Folder()._model.createFolder(
            parent=UserResponsesFolder, parentType='folder', name=subject._id,
            reuseExisting=True, public=False)
        newItem = self._model.createItem(
            folder=UserSubjectResponsesFolder,
            name=now.strftime("%Y-%m-%d-%H-%M-%S"), creator=informant,
            description="{}response on {} at {}".format(
                "{} ".format(
                    metadata.name
                ) if metadata and 'name' in metadata else "",
                now.strftime("%Y-%m-%d"),
                now.strftime("%H:%M:%S")
            ), reuseExisting=False)
        if metadata:
            newItem = self._model.setMetadata(newItem, metadata)
        return newItem
