import requests
import logging
import time
import random
import pprint

logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


class Client:
    HTTP_TIMEOUT = 60
    HTTP_HEADER_USER_TOKEN = 'AUTOFAQ-User-Token'

    def __init__(self, host_url='https://api.autofaq.ai', user_id=None, user_token=None, namespace='v1/setup'):
        self._host_url = host_url
        self._user_id = user_id
        self._token = user_token
        self._namespace = namespace

    def set_user(self, user_id=None, user_token=None):
        if user_id is not None:
            self._user_id = user_id
        if user_token is not None:
            self._token = user_token

    def set_host_url(self, host_url):
        self._host_url = host_url

    @property
    def id(self):
        return self._user_id

    @property
    def token(self):
        return self._token

    def _get(self, location, params=None):
        api_url = self._host_url + location
        logger.debug("{}".format(api_url))
        logger.debug("{}".format(params))
        headers = {self.HTTP_HEADER_USER_TOKEN: self._token}
        response = requests.get(api_url, params=params, headers=headers, timeout=Client.HTTP_TIMEOUT)
        logger.debug("response {}: {}".format(response.status_code, response.text))
        assert 'application/json' in response.headers['content-type']
        self._validate_reply_format(response)
        return response.json()

    def _post(self, location, params={}, headers={}):
        api_url = self._host_url + location
        logger.debug("{}".format(api_url))
        logger.debug("{}".format(params))
        headers = {self.HTTP_HEADER_USER_TOKEN: self._token, **headers}
        response = requests.post(api_url, json=params, headers=headers, timeout=Client.HTTP_TIMEOUT)
        logger.debug("response {}: {}".format(response.status_code, response.text))
        self._validate_reply_format(response)
        return response.json()

    def _put(self, location, params, headers={}):
        api_url = self._host_url + location
        logger.debug("{}".format(api_url))
        logger.debug("{} {}".format(params, headers))
        headers = {self.HTTP_HEADER_USER_TOKEN: self._token, **headers}
        response = requests.put(api_url, json=params, headers=headers, timeout=Client.HTTP_TIMEOUT)
        logger.debug("response {}: {}".format(response.status_code, response.text))
        self._validate_reply_format(response)
        return response.json()

    def _delete(self, location, params=None):
        api_url = self._host_url + location
        logger.debug("{}".format(api_url))
        logger.debug("{}".format(params))
        headers = {self.HTTP_HEADER_USER_TOKEN: self._token}
        response = requests.delete(api_url, params=params, headers=headers, timeout=Client.HTTP_TIMEOUT)
        logger.debug("response {}: {}".format(response.status_code, response.text))
        assert 'application/json' in response.headers['content-type']
        self._validate_reply_format(response)
        return response.json()

    @staticmethod
    def _validate_reply_format(response):
        # expect valid json body in any case
        try:
            response.json()
        except ValueError:
            logger.error(f"invalid json in response: {response.text}")
            raise

        if response.status_code == 200:
            # OK must not contain error
            assert 'error' not in response.json()
        else:
            # in case of abnormal status code we have error of some kind
            # expect json with details
            # 'error' field indicates code or text about error itself and 'message' field
            # 'message' field indicates general operation context
            assert isinstance(response.json()['error'], (str, int))
            assert isinstance(response.json()['message'], str)

    def get(self, location, params={}):
        return self._get(location, params)

    def post(self, location, params={}):
        return self._post(location, params)

    def put(self, location, params={}):
        return self._put(location, params)

    def delete(self, location, params={}):
        return self._delete(location, params)

    def create_service(self, params):
        post_params = dict(params)
        post_params.update(dict(user_id=self._user_id, user_token=self._token))
        response_json = self._post('/{}/services'.format(self._namespace), post_params)
        return response_json

    def get_service(self, service_id, include_suggested=0):
        response_json = self._get(
            "/{}/services/{}?user_token={}&user_id={}&include_suggested={}".format(
                self._namespace, service_id, self._token, self._user_id, include_suggested)
        )
        return response_json

    def get_service_status(self, service_id):
        response_json = self._get(
            "/{}/services/{}/status?user_token={}&user_id={}".format(
                self._namespace, service_id, self._token, self._user_id)
        )
        assert response_json['status'] in ["Unpublished", "Pending", "Serving", "Stopped"]
        return response_json

    def publish_service(self, service_id, wait_publish_completion=True, wait_timeout=40):
        response_json = self._post("/{}/services/{}/actions/publish".format(self._namespace, service_id))
        if wait_publish_completion:
            tstart = time.time()
            assert self.get_service_status(service_id)['status'] in {'Pending', 'Serving'}
            while self.get_service_status(service_id)['status'] == 'Pending':
                print('publish_service wait ..')
                time.sleep(2)
                assert (time.time() - tstart) < wait_timeout
            assert self.get_service_status(service_id)['status'] == 'Serving'
        return response_json

    def stop_service(self, service_id, wait_stop_completion=True, wait_timeout=30):
        response_json = self._post("/{}/services/{}/actions/stop".format(self._namespace, service_id))
        if wait_stop_completion:
            tstart = time.time()
            assert self.get_service_status(service_id)['status'] in {'Pending', 'Stopped'}
            while self.get_service_status(service_id)['status'] == 'Pending':
                print('stop_service wait ..')
                time.sleep(2)
                assert (time.time() - tstart) < wait_timeout
            assert self.get_service_status(service_id)['status'] == 'Stopped'
        return response_json

    def delete_service(self, service_id, expect_http_status_code=200):
        response_json = self._delete("/{}/services/{}".format(self._namespace, service_id))
        return response_json

    def create_document(
        self, service_id, question, answer, name=None,
        paraphrases=None, expired_at=None, ext={},
        status='OK'
    ):
        document_content = {
            'user_id': self._user_id,
            'user_token': self._token,
            'expired_at': expired_at,
            'question': question,
            'answer': answer,
            'ext': ext,
            'status': status,
            'service_id': service_id
        }
        if name is not None:
            document_content['name'] = name
        if paraphrases is not None:
            document_content['paraphrases'] = paraphrases  # list(map(lambda pph: {'text': pph}, pph_list))
        response_json = self._post(f'/{self._namespace}/documents', document_content)
        return response_json

    def get_top(self, service_id, service_token, query, query_url=None):
        query_url = query_url or '/v1/query'
        request_payload = {
            "service_id": service_id,
            "service_token": service_token,
            "query": query
        }
        response_json = self._post(query_url, request_payload)
        return response_json


class QnaAPI:
    def __init__(self, api_url, service_id, service_token):
        self._api_url = api_url
        self._service_id = service_id
        self._service_token = service_token
        self._session = requests.Session()

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def query(self, text, session_id=None, expect_http_status=200, params={}):
        logger.debug(f'query {self._api_url} {text}')
        orig_params = dict(
            query=text, service_id=self._service_id, service_token=self._service_token, session_id=session_id
        )
        orig_params.update(params)
        r = self._session.post(self._api_url + '/api/v1/query', json=orig_params)
        logger.debug(f'api_post response {pprint.pformat(r.json())}')
        if expect_http_status:
            assert r.status_code == expect_http_status, \
                f'response status {r.status_code} != {expect_http_status} expected'
            if expect_http_status == 200:
                assert 'error' not in r.json()
            else:
                assert 'error' in r.json()

        return r.json()
