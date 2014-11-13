#!/usr/bin/python

# -*- coding: utf-8 -*-

# Copyright (C) 2009-2012:
# Gabes Jean, naparuba@gmail.com
#    Gerhard Lausser, Gerhard.Lausser@consol.de
#    Gregory Starck, g.starck@gmail.com
#    Hartmut Goebel, h.goebel@goebel-consult.de
#
# This file is part of Shinken.
#
# Shinken is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Shinken is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Shinken.  If not, see <http://www.gnu.org/licenses/>.

"""
This class is for linking the WebUI with LDAP.
Based on the work the shinken-monitoring/mod-auth-active-directory.
link: https://github.com/shinken-monitoring/mod-auth-active-directory
"""

import os

try:
    import ldap
except ImportError:
    ldap = None

from shinken.log import logger
from shinken.basemodule import BaseModule


properties = {
    'daemons': ['webui', 'skonf', 'synchronizer'],
    'type': 'ad_webui'
}


# called by the plugin manager
def get_instance(plugin):
    logger.debug("[WebUI LDAP] Get an LDAP module for plugin %s" %
                 plugin.get_name())
    if not ldap:
        raise Exception('The module python-ldap is not found. Please install '
                        'it.')
    instance = LDAP_Webui(plugin)
    return instance
class LDAP_Webui(BaseModule):
    def __init__(self, modconf):
        BaseModule.__init__(self, modconf)
        self.ldap_uri = getattr(modconf, 'ldap_uri', None)
        self.username = getattr(modconf, 'username', '')
        self.password = getattr(modconf, 'password', '')
        self.basedn = getattr(modconf, 'basedn', '')

        # added for compatible with nagios with Apache mod_authnz_ldap
        # For other ldap_* options you can add them just like the ldap_user
        # one, if desired.
        self.ldap_users = []
        if hasattr(modconf, 'ldap_user'):
            ldap_user_list = getattr(modconf, 'ldap_user', '')
            ldap_users = ldap_user_list.split(',')
            if ldap_users != []:
                for user in ldap_users:
                    self.ldap_users.append(user.strip())


        # If we got no uri, we bailout...
        if not self.ldap_uri:
            self.active = False
        else:
            self.active = True
        self.con = None

        # for little result return to the client. If attributes are None in search_ext_s
        # all the attributes with the specified user will be returned.
        self.retrieve_attributes = ["email"]
        self.auth_key = 'dn'
        self.search_format = "(&(objectCategory=Person)(objectClass=User)(sAMAccountName=%s))"


    # Try to connect if we got true parameter
    def init(self):
        if not self.active:
            logger.error("[WebUI LDAP] Init error, lost LDAP uri in "
                         "configuration file. LDAP error: %s, %s" %
                         (e, str(e.__dict__)))
            return None

    # Give LDAP dn for a user
    def find_user_dn(self, username):

        logger.info(
            "[WebUI LDAP] Trying to get user dn for user %s" % username)
        search_scope = ldap.SCOPE_SUBTREE

        # wait for at most 3s to get an result, or an error ldap.TIMEOUT will
        # be raised. For more info: http://www.python-ldap.org/doc/html/
        # ldap.html?highlight=simple_bind_s#ldap.ldapObject.search
        time_out = 3

        # search for at most one user with name "username" for compatible

      # with mod_authnz_ldap
        size_limit = 1

        search_filter = self.search_format % username
        logger.info("[WebUI LDAP] Filter %s" % search_filter)
        try:
            res = self.con.search_ext_s(base=self.basedn,
                                        scope=search_scope,
                                        filterstr=search_filter,
                                        attrlist=self.retrieve_attributes,
                                        timeout=time_out,
                                        sizelimit=size_limit)
        except ldap.TIMEOUT, e:
            logger.error("[WebUI LDAP] LDAP error: %s, %s" %
                         (e, str(e.__dict__)))
            return None
        logger.info("[WebUI LDAP] Find user dn of %s" % username)

        if res == []:
            # user can not be authenticated
            return None
        else:
            dn, attrs = res[0]
            logger.info(res)
            logger.info(attrs)
            return dn



    def connect(self):
        logger.debug("[WebUI LDAP] Trying to initialize the LDAP"
                     " connection")
        self.con = ldap.initialize(self.ldap_uri)
        self.con.set_option(ldap.OPT_REFERRALS, 0)

        logger.debug("[WebUI LDAP] Trying to connect to LDAP %s "
                     "with user %s  on baseDN %s" %
                     (self.ldap_uri, self.username, self.basedn))
        # Any errors will throw an ldap.LDAPError exception or related
        # exception, so you can return.
        try:
            self.con.simple_bind_s(self.username, self.password)
        except ldap.LDAPError, e:
            logger.error("[WebUI LDAP] Bind error. Can not bind to "
                         "LDAP server with user %s. LDAP error: %s, %s" %
                         (self.username, e, str(e.__dict__)))
            return None
        logger.info("[WebUI LDAP] LDAP Connection done")


    def disconnect(self):
        self.con = None


    # To load the webui application
    def load(self, app):
        self.app = app


    # Try to auth a user in the LDAP dir
    def check_auth(self, username, password):
        if not username or not password:
            return False

        # First we try to connect, because there is no "KEEP ALIVE" option
        # available, so we will get a drop after one day...
        if not self.con:
            self.connect()

        user_dn = self.find_user_dn(username)

        logger.debug(
            "[WebUI LDAP] Trying to authenticate with user %s" % username)
        # Any errors will throw an ldap.LDAPError exception or related
        # exceptions, so you can know if the password is correct.
        try:
            self.con.simple_bind_s(user_dn, password)
            # authenticate success
            logger.debug("[WebUI LDAP] Authenticate success by LDAP with "
                         "user %s" % username)
        except ldap.LDAPError, e:
            # authenticate error
            logger.error("[WebUI LDAP] LDAP auth error: %s" % str(e))
            return False

        logger.debug("[WebUI LDAP] Trying to authorize with user %s" % username)
        if username in self.ldap_users:
            logger.debug("[WebUI LDAP] Authorize success with user %s" %
                         username)
            # authorize success
            self.disconnect()
            return True
        else:
            #authorize error
            self.disconnect()
            return False
