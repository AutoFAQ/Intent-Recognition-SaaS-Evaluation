# Based on https://github.com/giangpol/NLU-Evaluation-Scripts/tree/master/nlu_analysers
import urllib
import json
import requests
import time
import sys
import os
import subprocess
import tqdm
from google.cloud import dialogflow
from google.api_core.exceptions import ResourceExhausted
from requests.auth import HTTPBasicAuth
from collections import OrderedDict


class Analyser(object):
    @staticmethod
    def check_key(my_dict, my_key):
        try:
            t = my_dict[my_key]
        except KeyError:
            my_dict[my_key] = {'truePos': 0, 'falsePos': 0, 'falseNeg': 0}

    @staticmethod
    def try_div(dividend, divisor):
        try:
            return float(dividend) / float(divisor)
        except:
            return "n.a."

    @staticmethod
    def sort_dict(my_dict):
        for key in my_dict:
            if isinstance(my_dict[key], dict):
                my_dict[key] = Analyser.sort_dict(my_dict[key])

        sort_order = ['intents', 'entities', 'truePos', 'falseNeg', 'falsePos', 'precision', 'recall', 'f1']
        sort_order2 = set(my_dict.keys()) - set(sort_order)
        my_sort = list(sort_order2)
        my_sort.extend(sort_order)

        return [OrderedDict(sorted(my_dict.iteritems(), key=lambda kv: my_sort.index(kv[0])))]

    @staticmethod
    def calc_pres_rec_f1(dict, tp, fn, fp):
        dict["precision"] = Analyser.try_div(tp, tp + fp)
        dict["recall"] = Analyser.try_div(tp, tp + fn)
        try:
            dict["f1"] =  2 * ((dict["precision"] * dict["recall"]) / (dict["precision"] + dict["recall"]))
        except:
            dict["f1"] = "n.a."

        return dict

    @staticmethod
    def write_json(file, content):
        content = json.loads(content)

        #precision, recall, f1
        os_tp = 0
        os_fn = 0
        os_fp = 0

        for x in ["entities", "intents"]:
            s_tp = 0
            s_fn = 0
            s_fp = 0

            for key in content[x]:
                s_tp += content[x][key]["truePos"]
                s_fn += content[x][key]["falseNeg"]
                s_fp += content[x][key]["falsePos"]

                Analyser.calc_pres_rec_f1(content[x][key], content[x][key]["truePos"], content[x][key]["falseNeg"], content[x][key]["falsePos"])

            os_tp += s_tp
            os_fn += s_fn
            os_fp += s_fp

            Analyser.calc_pres_rec_f1(content[x], s_tp, s_fn, s_fp)

        Analyser.calc_pres_rec_f1(content, os_tp, os_fn, os_fp)

        #sort keys
        content = Analyser.sort_dict(content)

        f = open(file, "w")
        f.write( json.dumps(content, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False).encode('utf-8'))
        f.close()

    def __init__(self):
        self.analysis = {}



class LuisAnalyser(Analyser):
    @staticmethod
    def detokenizer(s):
        return s.replace(" . ", ".").replace(" , ", ",").replace(" ' ","'").replace(" ? ","?").replace(" ! ","!").replace(" & ", "&").replace(" : ",":").replace(" - ","-").replace(" / ","/").replace(" ( ","(").replace(" ) ",")")


    def __init__(self, application_id, subscription_key):
        super(LuisAnalyser, self).__init__()
        self.subscription_key = subscription_key
        self.application_id = application_id
        self.url = "https://westeurope.api.cognitive.microsoft.com/luis/prediction/v3.0/apps/"+self.application_id+"/slots/staging/predict?subscription-key="+self.subscription_key+"&verbose=true&show-all-intents=true&log=true&query=%s"

    def get_annotations(self, test_sentences):
        annotations = {'results':[]}

        query_times = []
        for s in test_sentences:
            start_time = time.time()
            encoded_text = urllib.parse.quote(s)
            annotations['results'].append(requests.get(self.url % encoded_text,data={},headers={}).json())
            query_time = time.time() - start_time
            query_times.append(query_time)

        return annotations, query_times


class DialogflowAnalyser(Analyser):
    def __init__(self, app_id, env_file):
        super(DialogflowAnalyser, self).__init__()
        self.app_id = app_id
        # Put your GOOGLE_APPLICATION_CREDENTIALS here (some.json")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = env_file
        self._session = '12312412'

    def get_annotations(self, test_sentences, language_code='en'):
        session_client = dialogflow.SessionsClient()
        results = []

        session = session_client.session_path(self.app_id, self._session)
        query_times = []
        for text in tqdm.tqdm(test_sentences):
            self.query_dialogflow(text, language_code, session_client, session, query_times, results)
            time.sleep(1)
        return results, query_times

    def query_dialogflow(self, text, language_code, session_client, session, query_times, results):
        start_time = time.time()
        text_input = dialogflow.TextInput(text=text, language_code=language_code)

        query_input = dialogflow.QueryInput(text=text_input)
        response = session_client.detect_intent(
            request={"session": session, "query_input": query_input}
        )
        query_times.append(time.time() - start_time)
        results.append(response)
