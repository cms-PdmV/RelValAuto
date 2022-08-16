import sys
import os
import json
import traceback
import logging
import time

try:
    import cookielib
except ImportError:
    import http.cookiejar as cookielib

try:
    import urllib2 as urllib
    from urllib2 import HTTPError as HTTPError
except ImportError:
    import urllib.request as urllib
    from urllib.error import HTTPError as HTTPError


class MethodRequest(urllib.Request):
    """
    Custom request, so it would support different HTTP methods
    """
    def __init__(self, *args, **kwargs):
        self._method = kwargs.pop('method', None)
        urllib.Request.__init__(self, *args, **kwargs)

    def get_method(self, *args, **kwargs):
        if self._method is not None:
            return self._method

        return urllib.Request.get_method(self, *args, **kwargs)


class RelVal:
    def __init__(self, debug=False, cookie=None, dev=False):
        if dev:
            self.host = 'cms-pdmv-dev.cern.ch'
        else:
            self.host = 'cms-pdmv.cern.ch'

        self.dev = dev
        self.server = 'https://' + self.host + '/relval/'
        # Set up logging
        if debug:
            logging_level = logging.DEBUG
        else:
            logging_level = logging.INFO

        if cookie:
            self.cookie = cookie
        else:
            home = os.getenv('HOME')
            if dev:
                self.cookie = '%s/private/relval-dev-cookie.txt' % (home)
            else:
                self.cookie = '%s/private/relval-prod-cookie.txt' % (home)

        # Set up logging
        logging.basicConfig(format='[%(asctime)s][%(levelname)s] %(message)s', level=logging_level)
        self.logger = logging.getLogger()
        # Create opener
        self.__connect()
        # Request retries
        self.max_retries = 3

    def __connect(self):
        if not os.path.isfile(self.cookie):
            self.logger.info('SSO cookie file is absent. Will try to make one for you...')
            self.__generate_cookie()
            if not os.path.isfile(self.cookie):
                self.logger.error('Missing cookie file %s, quitting', self.cookie)
                sys.exit(1)
        else:
            self.logger.info('Using SSO cookie file %s' % (self.cookie))

        cookie_jar = cookielib.MozillaCookieJar(self.cookie)
        cookie_jar.load()
        for cookie in cookie_jar:
            self.logger.debug('Cookie %s', cookie)

        self.opener = urllib.build_opener(urllib.HTTPCookieProcessor(cookie_jar))

    def __generate_cookie(self):
        # use env to have a clean environment
        command = 'rm -f %s; env -i KRB5CCNAME="$KRB5CCNAME" cern-get-sso-cookie -u %s -o %s --reprocess --krb' % (self.cookie, self.server, self.cookie)
        self.logger.debug(command)
        output = os.popen(command).read()
        self.logger.debug(output)
        if not os.path.isfile(self.cookie):
            self.logger.error('Could not generate SSO cookie.\n%s', output)

    # Generic methods for GET, PUT, DELETE HTTP methods
    def __http_request(self, url, method, data=None, parse_json=True):
        url = self.server + url
        self.logger.debug('[%s] %s', method, url)
        headers = {'User-Agent': 'RelVal Scripting'}
        if data:
            data = json.dumps(data).encode('utf-8')
            headers['Content-type'] = 'application/json'

        retries = 0
        response = None
        while retries < self.max_retries:
            request = MethodRequest(url, data=data, headers=headers, method=method)
            try:
                retries += 1
                response = self.opener.open(request)
                response = response.read()
                response = response.decode('utf-8')
                self.logger.debug('Response from %s length %s', url, len(response))
                if parse_json:
                    return json.loads(response)
                else:
                    return response

            except (ValueError, HTTPError) as some_error:
                # If it is not 3xx, reraise the error
                if isinstance(some_error, HTTPError) and not (300 <= some_error.code <= 399):
                    response = some_error.read()
                    json_response = json.loads(response)
                    self.logger.error(json_response.get('message', 'unknown error'))
                    return json_response

                wait_time = retries ** 3
                self.logger.warning('Most likely SSO cookie is expired, will remake it after %s seconds',
                                    wait_time)
                time.sleep(wait_time)
                self.__generate_cookie()
                self.__connect()

        self.logger.error('Error while making a %s request to %s. Response: %s',
                          method,
                          url,
                          response)
        return None

    def __get(self, url, parse_json=True):
        return self.__http_request(url, 'GET', parse_json=parse_json)

    def __put(self, url, data, parse_json=True):
        return self.__http_request(url, 'PUT', data, parse_json=parse_json)

    def __post(self, url, data, parse_json=True):
        return self.__http_request(url, 'POST', data, parse_json=parse_json)

    def __delete(self, url, parse_json=True):
        return self.__http_request(url, 'DELETE', parse_json=parse_json)

    def get(self, object_type, object_id=None, query='', page=-1):
        """
        Get data from RelVal machine
        object_type - [subcampaigns, tickets, requests]
        object_id - prep id of object
        query - query to be run in order to receive an object, e.g. status=submitted,
                multiple parameters can be used with & status=submitted&processing_string=UL2017_MiniAODv2
        page - which page to be fetched. -1 means no paginantion, return all results
        """
        object_type = object_type.strip()
        if object_id:
            object_id = object_id.strip()
            self.logger.debug('Object ID %s provided, database %s', object_id, object_type)
            url = 'api/%s/get/%s' % (object_type, object_id)
            result = self.__get(url).get('response')
            if not result:
                return None

            return result
        elif query:
            if page != -1:
                self.logger.debug('Fetching page %s of %s for query %s',
                                  page,
                                  object_type,
                                  query)
                url = 'api/search?db_name=%s&limit=100&page=%d&%s' % (object_type, page, query)
                results = self.__get(url).get('response', {}).get('results', [])
                self.logger.debug('Found %s %s in page %s for query %s',
                                  len(results),
                                  object_type,
                                  page,
                                  query)
                return results
            else:
                self.logger.debug('Page not given, will use pagination to build response')
                page_results = [{}]
                results = []
                page = 0
                while page_results:
                    page_results = self.get(object_type=object_type,
                                            query=query,
                                            page=page)
                    results += page_results
                    page += 1
                    time.sleep(0.125)

                return results
        else:
            self.logger.error('Neither object ID, nor query is given, doing nothing...')

    def update(self, object_type, object_data):
        """
        Update data in RelVal machine
        object_type - [subcampaigns, tickets, requests]
        object_data - new JSON of an object to be updated
        """
        url = 'api/%s/update' % (object_type)
        return self.__post(url, object_data)

    def put(self, object_type, object_data):
        """
        Put data into RelVal machine
        object_type - [subcampaigns, tickets, requests]
        object_data - new JSON of an object to be saved
        """
        url = 'api/%s/create' % (object_type)
        res = self.__put(url, object_data)
        return res

    def delete(self, object_type, object_id):
        """
        Delete object from RelVal machine
        object_type - [subcampaigns, tickets, requests]
        object_id - object PrepID
        """
        url = 'api/%s/delete' % (object_type)
        res = self.__delete(url, {'prepid': object_id})
        return res

    def next_status(self, request_prepid):
        """
        Move request to next status
        """
        url = 'api/requests/next_status'
        res = self.__post(url, {'prepid': request_prepid})
        return res

    def previous_status(self, request_prepid):
        """
        Move request to previous status
        """
        url = 'api/requests/previous_status'
        res = self.__post(url, {'prepid': request_prepid})
        return res

    def create_relvals(self, ticket_prepid):
        """
        Create relvals for the given ticket
        """
        url = 'api/tickets/create_relvals'
        res = self.__post(url, {'prepid': ticket_prepid})
        return res




