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

import itertools
import tzlocal
from ..describe import Description, autoDescribeRoute
from ..rest import Resource, filtermodel, setResponseHeader, \
    setContentDisposition
from datetime import datetime
from girderformindlogger.utility import ziputil
from girderformindlogger.constants import AccessType, TokenScope
from girderformindlogger.exceptions import AccessException, RestException, \
    ValidationException
from girderformindlogger.api import access
from girderformindlogger.models.activity import Activity as ActivityModel
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.models.assignment import Assignment as AssignmentModel
from girderformindlogger.models.folder import Folder
from girderformindlogger.models.response_folder import ResponseFolder as \
    ResponseFolderModel, ResponseItem as ResponseItemModel
from girderformindlogger.models.roles import getCanonicalUser, getUserCipher
from girderformindlogger.models.user import User as UserModel
from girderformindlogger.models.upload import Upload as UploadModel
from girderformindlogger.utility.response import formatResponse, \
    string_or_ObjectID
from girderformindlogger.utility.resource import listFromString
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId
import hashlib



class ResponseItem(Resource):

    def __init__(self):
        super(ResponseItem, self).__init__()
        self.resourceName = 'response'
        self._model = ResponseItemModel()
        self.route('GET', (), self.getResponses)
        self.route('GET', ('last7Days', ':applet'), self.getLast7Days)
        self.route('POST', (':applet', ':activity'), self.createResponseItem)

    """
    TODO 🚧:
        '…, applet, and/or activity. '
        'Parameters act as cumulative filters, so mutually '
        'exclusive combinations will return an empty Array; called without '
        'any parameters returns all responses to which the logged-in user '
        'has access.'
        .param(
            'subject',
            'The ID (canonical or applet-specific) of the subject about whom '
            'to get responses or an Array thereof.',
            required=False
        )
        .param(
            'activity',
            'The ID of the activity for which to get responses or an Array '
            'thereof.',
            required=False
        )
        .param(
            'screen',
            'The ID of the screen for which to get responses or an Array '
            'thereof.',
            required=False
        )
    """
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get all responses for a given user.'
        )
        .param(
            'informant',
            'The ID (canonical or applet-specific) of the informant for whom '
            'to get responses or an Array thereof.',
            required=False
        )
        .param(
            'applet',
            'The ID of the applet for which to get responses or an Array '
            'thereof.',
            required=False
        )
        .errorResponse('ID was invalid.')
        .errorResponse(
            'Read access was denied for this applet for this user.',
            403
        )
    )
    def getResponses(
        self,
        informant=[],
        subject=[],
        applet=[],
        # activity=[],
        # screen=[]
    ):
        assert applet,  'you need to specify an applet'
        
        # grab the current user
        reviewer = self.getCurrentUser()

        # check that they are a reviewer for the applet.

        # get the applet information
        appletInfo = AppletModel().findOne({'_id': ObjectId(applet)})

        # TODO: for now, an applet only has one group
        reviewerGroupOfApplet = appletInfo['roles']['reviewer']['groups']

        assert len(reviewerGroupOfApplet) == 1, 'there should be only 1 group for an applet, for now.'
        reviewerGroupOfApplet = reviewerGroupOfApplet[0]['id']
        

        # check that the current user's userId is in the list of reveiwersOfApplet
        isAReviewer = list(filter(lambda x: x == reviewerGroupOfApplet, reviewer['groups']))

        # TODO: for now, if the user is not a reviewer, then fail.
        assert len(isAReviewer) == 1, 'the current user is not a reviewer'


        # Build a query to get all the data.
        # TODO: enable the query to filter by subjects, informants, and activities.

        props = {
            # "informant": [
            #     list(itertools.chain.from_iterable(
            #         [string_or_ObjectID(s) for s in listFromString(informant)]
            #     )),
            #     "baseParentId"
            # ],
            # "subject": [
            #     list(itertools.chain.from_iterable(
            #         [string_or_ObjectID(s) for s in listFromString(subject)]
            #     )),
            #     "meta.subject.@id"
            # ],
            "applet": [
                list(itertools.chain.from_iterable(
                    [string_or_ObjectID(s) for s in listFromString(applet)]
                )),
                "meta.applet.@id"
            ],
            # "activity": [
            # list(itertools.chain.from_iterable(
            #         [string_or_ObjectID(s) for s in listFromString(activity)]
            #     )),
            #     "meta.activity.@id"
            # ] # TODO: Add screen
        }

        # if not(len(props["informant"][0])):
        #     props["informant"][0] = [reviewer.get('_id')] # TODO: allow getting all available
    
        q = {
            props[prop][1]: {
                "$in": props[prop][0]
            } for prop in props if len(
                props[prop][0]
            )
        }
        print(q)

        allResponses = list(ResponseItemModel().find(
            query=q,
            user=reviewer,
            sort=[("created", DESCENDING)]
        ))


        # for each response in allResponses, we need to encode a userId
        # if the currentUser is also a manager, then we can put an email address.
        # if the currentUser is ONLY a reviewer, then give the subject a unique id.
        # the unique id is a hash of the baseParentId

        # HINT: in appletModel there is a userCipher function

        # TODO: check to see if the user is also a manager.
        # TODO: for now, an applet only has one group
        # get the manager group and make sure there is just 1:
        managerGroupOfApplet = appletInfo['roles']['manager']['groups']
        assert len(managerGroupOfApplet) == 1, 'there should be only 1 group for an applet, for now.'
        managerGroupOfApplet = managerGroupOfApplet[0]['id']

        # check to see if the current user is a manager too.       
        isAManager = len(list(filter(lambda x: x == managerGroupOfApplet, reviewer['groups'])))

        # Format the output response. If the user is a manager, then lookup an email and return it.
        # else, get the userCipher and use that for the userId.
        outputResponse = []
        for response in allResponses:
            userId = response['baseParentId']
            
            # encode the userId below:
            if isAManager:
                user = UserModel().findOne({'_id': ObjectId(userId)})
                encodedId = user['email']
            else:
                # TODO: create a user cipher, which is the hash of
                # an appletid concatenated with the user id
                appletIdUserId = applet + str(userId)
                # hash it:
                hash_object = hashlib.md5(appletIdUserId.encode())
                encodedId = hash_object.hexdigest()

            # format the response and add the userId
            formattedResponse = formatResponse(response)['thisResponse']
            formattedResponse['userId'] = encodedId
            outputResponse.append(formattedResponse)

        # lets format the output response in tidy format.
        # a list of objects, with columns:
        # ['itemURI', 'value', 'userId', 'schema:startDate', 'schema:endDate']

        formattedOutputResponse = []

        for response in outputResponse:
            tmp = {
                'schema:startDate': response['schema:startDate'],
                'schema:endDate': response['schema:endDate'],
                'userId': response['userId'],
            }
            for key, value in response['responses'].items():
                tmp['itemURI'] = key
                tmp['value'] = value
                formattedOutputResponse.append(tmp)

        return formattedOutputResponse

        # responseArray = [
        #     formatResponse(response) for response in allResponses
        # ]
        # return([
        #     response for response in responseArray if response not in [
        #         {},
        #         None
        #     ]
        # ])


    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description(
            'Get the last 7 days\' responses for the current user.'
        )
        .param(
            'applet',
            description='The ID of the Applet this response is to.'
        )
        .param(
            'subject',
            'The ID of the Subject this response is about.',
            required=False
        )
        .param(
            'referenceDate',
            'Final date of 7 day range. (Not plugged in yet).',
            required=False
        )
        .errorResponse('ID was invalid.')
        .errorResponse(
            'Read access was denied for this applet for this user.',
            403
        )
    )
    def getLast7Days(
        self,
        applet,
        subject=None,
        referenceDate=None
    ):
        from girderformindlogger.utility.response import last7Days
        from bson.objectid import ObjectId
        try:
            appletInfo = AppletModel().findOne({'_id': ObjectId(applet)})
            user = self.getCurrentUser()
            return(last7Days(applet, appletInfo, user.get('_id'), user, referenceDate))
        except:
            import sys, traceback
            print(sys.exc_info())
            print(traceback.print_tb(sys.exc_info()[2]))
            return({})



    @access.user(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Create a new user response item.')
        #.responseClass('Item')
        .modelParam(
            'applet',
            model=AppletModel,
            level=AccessType.READ,
            destName='applet',
            description='The ID of the Applet this response is to.'
        )
        .modelParam(
            'activity',
            model=ActivityModel,
            level=AccessType.READ,
            destName='activity',
            description='The ID of the Activity this response is to.'
        )
        .param('subject_id', 'The ID (canonical or applet-specific) of the '
               'user that is the subject.',
               required=False, default=None)
        .param(
            'pending',
            'Boolean, is this response in-progress rather than complete. '
            '(_not yet implemented_)',
            required=False, default=False)
        .jsonParam('metadata',
                   'A JSON object containing the metadata keys to add.',
                   paramType='form', requireObject=True, required=True)
        .errorResponse()
        .errorResponse('Write access was denied on the parent folder.', 403)
    )
    def createResponseItem(self, applet, activity, metadata, subject_id, pending, params):
        import threading
        from girderformindlogger.utility.response import aggregateAndSave
        # TODO: pending
        metadata['applet'] = {
            "@id": applet.get('_id'),
            "name": AppletModel().preferredName(applet),
            "url": applet.get(
                'url',
                applet.get('meta', {}).get('applet', {}).get('url')
            )
        }
        metadata['activity'] = {
            "@id": activity.get('_id'),
            "name": ActivityModel().preferredName(activity),
            "url": activity.get(
                'url',
                activity.get('meta', {}).get('activity', {}).get('url')
            )
        }
        informant = self.getCurrentUser()
        subject_id = subject_id if subject_id else str(
            informant['_id']
        )

        # subject_id = [
        #     getUserCipher(
        #         appletAssignment=assignment,
        #         user=subject_id
        #     ) for assignment in appletAssignments
        # ][0]
        try:
            subject_info = Folder().load(
                id=subject_id,
                user=informant,
                level=AccessType.READ
            )
        except AccessException:
            subject_info = {}
        metadata['subject'] = subject_info.get('meta', {}) if isinstance(
            subject_info,
            dict
        ) else {}
        metadata['subject']['@id'] = subject_id
        now = datetime.now(tzlocal.get_localzone())
        appletName=AppletModel().preferredName(applet)
        UserResponsesFolder = ResponseFolderModel().load(
            user=informant,
            reviewer=informant,
            force=True
        )
        UserAppletResponsesFolder = Folder().createFolder(
            parent=UserResponsesFolder, parentType='folder',
            name=appletName, reuseExisting=True, public=False)
        AppletSubjectResponsesFolder = Folder().createFolder(
            parent=UserAppletResponsesFolder, parentType='folder',
            name=subject_id, reuseExisting=True, public=False)
        try:
            newItem = self._model.createResponseItem(
                folder=AppletSubjectResponsesFolder,
                name=now.strftime("%Y-%m-%d-%H-%M-%S-%Z"), creator=informant,
                description="{} response on {} at {}".format(
                    Folder().preferredName(activity),
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S %Z")
                ), reuseExisting=False)
        except:
            raise ValidationException(
                "Couldn't find activity name for this response"
            )

        # for each blob in the parameter, upload it to a File under the item.
        for key, value in params.items():
            # upload the value (a blob)
            um = UploadModel()
            filename = "{}.{}".format(
                key,
                metadata['responses'][key]['type'].split('/')[-1]
            )
            newUpload = um.uploadFromFile(
                value.file,
                metadata['responses'][key]['size'],
                filename,
                'item',
                newItem,
                informant,
                metadata['responses'][key]['type']
            )
            # now, replace the metadata key with a link to this upload
            metadata['responses'][key] = "file::{}".format(newUpload['_id'])

        if metadata:
            newItem = self._model.setMetadata(newItem, metadata)

        if not pending:
            # create a Thread to calculate and save aggregates

            # TODO: probably uncomment this as we scale.
            # idea: thread all time, but synchronously do last7 days
            # agg = threading.Thread(target=aggregateAndSave, args=(newItem, informant))
            # agg.start()
            aggregateAndSave(newItem, informant)
            newItem['readOnly'] = True
        return(newItem)

def save():
    return(lambda x: x)

