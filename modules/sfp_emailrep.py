# -*- coding: utf-8 -*-
# -------------------------------------------------------------------------------
# Name:         sfp_emailrep
# Purpose:      Searches EmailRep.io for email address reputation.
#
# Author:      <bcoles[at]gmail[.]com>
#
# Created:     2019-08-07
# Copyright:   (c) bcoles 2019
# Licence:     GPL
# -------------------------------------------------------------------------------

import json
import time
from sflib import SpiderFoot, SpiderFootPlugin, SpiderFootEvent

class sfp_emailrep(SpiderFootPlugin):
    """EmailRep:Footprint,Investigate,Passive:Search Engines:apikey:Search EmailRep.io for email address reputation."""

    meta = {
		'name': "EmailRep",
		'summary': "Search EmailRep.io for email address reputation.",
		'flags': [ "apikey" ],
		'useCases': [ "Footprint", "Investigate", "Passive" ],
		'categories': [ "Search Engines" ],
        'dataSource': {
            'website': "https://emailrep.io/",
            'model': "FREE_AUTH_LIMITED",
            'references': [
                "https://docs.emailrep.io/"
            ],
            'apiKeyInstructions': [
                "Visit emailrep.io/free",
                "Request a free API Key",
                "The API key will be sent to registered email account on approval"
            ],
            'favIcon': "https://emailrep.io/assets/img/favicon.png",
            'logo': "https://emailrep.io/assets/img/logo-light.png",
            'description': "Illuminate the \"reputation\" behind an email address.\n"
                               "EmailRep uses hundreds of factors like domain age, traffic rankings, "
                               "presence on social media sites, professional networking sites, personal connections, "
                               "public records, deliverability, data breaches, dark web credential leaks, "
                               "phishing emails, threat actor emails, and more to answer these types of questions.\n",
        }
	}
	

    opts = {
        'api_key': '',
    }

    optdescs = {
        'api_key': 'EmailRep API key.',
    }

    results = None
    errorState = False

    def setup(self, sfc, userOpts=dict()):
        self.sf = sfc
        self.results = self.tempStorage()
        self.errorState = False

        for opt in list(userOpts.keys()):
            self.opts[opt] = userOpts[opt]

    def watchedEvents(self):
        return ['EMAILADDR']

    def producedEvents(self):
        return ['RAW_RIR_DATA', 'EMAILADDR_COMPROMISED', 'MALICIOUS_EMAILADDR']

    # https://emailrep.io/docs/
    def query(self, qry):
        headers = {
            'Accept': "application/json"
        }

        if self.opts['api_key'] != '':
            headers['Key'] = self.opts['api_key']

        res = self.sf.fetchUrl(
            'https://emailrep.io/' + qry,
            headers=headers,
            useragent='SpiderFoot',
            timeout=self.opts['_fetchtimeout']
        )

        # Documentation does not indicate rate limit threshold (50 queries/day)
        time.sleep(1)

        if res['content'] is None:
            return None

        if res['code'] == '400':
            self.sf.error('API error: Bad request', False)
            self.errorState = True
            return None

        if res['code'] == '401':
            self.sf.error('API error: Invalid API key', False)
            self.errorState = True
            return None

        if res['code'] == '429':
            self.sf.error('API error: Too Many Requests', False)
            self.errorState = True
            return None

        if res['code'] != '200':
            self.sf.error('Unexpected reply from EmailRep.io: ' + res['code'], False)
            self.errorState = True
            return None

        try:
            data = json.loads(res['content'])
        except BaseException as e:
            self.sf.debug("Error processing JSON response: " + str(e))
            return None

        return data

    def handleEvent(self, event):
        eventName = event.eventType
        srcModuleName = event.module
        eventData = event.data

        if eventData in self.results:
            return None

        self.results[eventData] = True

        self.sf.debug("Received event, %s, from %s" % (eventName, srcModuleName))

        if self.opts['api_key'] == '':
            self.sf.error("Warning: You enabled sfp_emailrep but did not set an API key! Queries will be rate limited.", False)

        res = self.query(eventData)

        if res is None:
            return None

        details = res.get('details')

        if not details:
            return None

        credentials_leaked = details.get('credentials_leaked')
        if credentials_leaked:
            evt = SpiderFootEvent('EMAILADDR_COMPROMISED', eventData + " [Unknown]", self.__name__, event)
            self.notifyListeners(evt)

        malicious_activity = details.get('malicious_activity')
        if malicious_activity:
            evt = SpiderFootEvent('MALICIOUS_EMAILADDR', 'EmailRep [' + eventData + ']', self.__name__, event)
            self.notifyListeners(evt)

        if malicious_activity or credentials_leaked:
            evt = SpiderFootEvent('RAW_RIR_DATA', str(res), self.__name__, event)
            self.notifyListeners(evt)

# End of sfp_emailrep class
