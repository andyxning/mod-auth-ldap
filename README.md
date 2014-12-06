[![Build Status](https://travis-ci.org/andyxning/mod-auth-ldap.svg)](https://travis-ci.org/andyxning/mod-auth-ldap)

mod-auth-ldap
=========================

Shinken module for WebUI authentification with OpenLDAP

Changes with [shinken-monitoring/mod-auth-active-directory](https://github.com/shinken-monitoring/mod-auth-active-directory)
-------------------------
* Be compatible with nagios ldap authentication and authorization with Apache installed. The nagios ldap auth with Apache will directly check the ldap with user inputed username and password. For more info with the authentication and authorization with Apache's [mod_authnz_ldap](http://httpd.apache.org/docs/current/mod/mod_authnz_ldap.html).There are two steps to auth a user.
  * authentication
    * check that the user http client provided exactly exists
    * check that the user password is correct
  * authorization
    * the user is in ldap_user(other ldap_* are not support by this module, however you can add it if you want. It will be easy to do this.) 

TODO
----
* check if the ldap configutation file's contents has been changed before each auth, thus to simulate the reload functionality after change the ldap_user option in auth-ldap.cfg file, in order to prevent a reload of the Shinken's broker daemon.
