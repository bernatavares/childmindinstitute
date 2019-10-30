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
from girderformindlogger.api import access
from girderformindlogger.constants import TokenScope
from girderformindlogger.models.applet import Applet as AppletModel
from girderformindlogger.utility import jsonld_expander, response


class Schedule(Resource):
    """API Endpoint for schedules."""

    def __init__(self):
        super(Schedule, self).__init__()
        self.resourceName = 'schedule'
        self.route('GET', (), self.getSchedule)

    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get schedule Array for the logged-in user.')
        .param(
            'timezone',
            'The <a href="https://en.wikipedia.org/wiki/'
            'List_of_tz_database_time_zones">TZ database name</a> of the '
            'timezone to return times in. Times returned in UTC if omitted.',
            required=False
        )
        .errorResponse()
    )
    def getSchedule(self, timezone=None):
        """
        Get a list of dictionaries keyed by activityID.
        """
        currentUser = self.getCurrentUser()
        return ({
            applet['applet'].get('_id', ''): {
                applet['activities'][activity].get('_id', ''): {
                    'lastResponse': response.getLatestResponseTime(
                        currentUser['_id'],
                        applet['applet']['_id'].split('applet/')[-1],
                        activity,
                        tz=timezone
                    ) #,
                    # 'nextScheduled': None,
                    # 'lastScheduled': None
                } for activity in list(
                    applet.get('activities', {}).keys()
                )
            } for applet in [
                jsonld_expander.formatLdObject(
                    applet,
                    'applet',
                    currentUser
                ) for applet in AppletModel().getAppletsForUser(
                    user=currentUser,
                    role='user'
                )
            ]
        })
