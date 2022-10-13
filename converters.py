# Based on https://github.com/giangpol/NLU-Evaluation-Scripts/tree/master/nlu_converters
import json
import shutil
import os
import hashlib
import zipfile
import pandas as pd


def parse_data(path):
    X = []
    y = []
    docs = {}
    with open(path, 'r') as f:
        for line in f:
            splitted = line.split(',')
            label = splitted[0]
            sent = ", ".join(splitted[2:]).strip()
            X.append(sent)
            y.append(label)
            if label not in docs:
                docs[label] = {'question': sent, 'answer': label, 'name': label, 'paraphrased_questions': []}
            else:
                docs[label]['paraphrased_questions'].append(sent)
    return docs, X, y


def parse_data_csv(path):
    df = pd.read_csv(path)
    X = []
    y = []
    docs = {}
    for _, row in df.iterrows():
        X.append(row['phrase'])
        y.append(row['intent'])
        if row['intent'] not in docs:
            docs[row['intent']] = {'question': row['phrase'], 'answer': row['intent'], 'name': row['intent'], 'paraphrased_questions': []}
        else:
            docs[row['intent']]['paraphrased_questions'].append(row['phrase'])
    return docs, X, y


class AnnotatedSentence:
    def __init__(self, text, intent, entities):
        self.text = text
        self.intent = intent
        self.entities = entities


class Converter(object):
    @staticmethod
    def tokenizer(s):
        return s.replace(".", " . ").replace(",", " , ").replace("'", " ' ").replace("?", " ? ").replace("!", " ! ").replace("&", " & ").replace(":"," : ").replace("-"," - ").replace("/"," / ").replace("("," ( ").replace(")"," ) ").replace("  "," ").split(" ")

    @staticmethod
    def detokenizer(s):
        return s.replace(" . ", ".").replace(" , ", ",").replace(" ' ","'").replace(" ? ","?").replace(" ! ","!").replace(" & ", "&").replace(" : ",":").replace(" - ","-").replace(" / ","/").replace(" ( ","(").replace(" ) ",")")

    @staticmethod
    def write_json(file, content):
        f = open(file, "w")
        f.write(content)
        f.close()

    @staticmethod
    def array_to_json(array):
        j = []
        for e in array:
            j.append({"name":e})
        return j


    def __init__(self):
        self.intents = set()
        self.entities = set()
        self.utterances = []

        self.name = ""
        self.desc = ""
        self.lang = ""


    def __add_intent(self, intent):
        raise NotImplementedError("Please implement this method")

    def __add_entity(self, entity):
        raise NotImplementedError("Please implement this method")

    def __add_utterance(self, sentence):
        raise NotImplementedError("Please implement this method")

    def import_corpus(self, file):
        raise NotImplementedError("Please implement this method")

    def export(self, file):
        raise NotImplementedError("Please implement this method")


class LuisConverter(Converter):
    LUIS_SCHEMA_VERSION = "2.2.0"

    def __init__(self):
        super(LuisConverter, self).__init__()
        self.bing_entities = set()

    def __add_intent(self, intent):
        self.intents.add(intent)

    def __add_entity(self, entity):
        self.entities.add(entity)

    def __add_bing_entity(self, entity):
        self.bing_entities.add(entity)

    def __add_utterance(self, sentence):
        entities = []
        for e in sentence.entities:
            #Calculate the position based on character count.
            words = (sentence.text).split(' ')
            index = 0
            for i in range(len(words)):
                if i == e["start"]:
                    start_index = index
                    end_index = index + len(words[i])
                elif i == e["stop"]:
                    end_index = index + len(words[i])
                    break
                index = index + len(words[i]) + 1
            #print start_index, end_index
            entities.append({"entity": e["entity"], "startPos": start_index, "endPos": end_index-1})
        self.utterances.append({"text": sentence.text, "intent": sentence.intent, "entities": entities})

    def import_corpus(self, filepath, lang="en"):
        docs, X, y = parse_data_csv(filepath)

        self.name = filepath
        self.desc = filepath
        if(lang == "en"):
            self.lang = "en-us"
        else:
            self.lang = lang

        for doc in docs.values():
            self.__add_intent(doc['name'])

            self.__add_utterance(AnnotatedSentence(doc["question"], doc['name'], []))
            for p in doc['paraphrased_questions']:
                self.__add_utterance(AnnotatedSentence(p, doc['name'], []))


    def export(self, filename):
        luis_json = {}
        luis_json["luis_schema_version"] = self.LUIS_SCHEMA_VERSION
        luis_json["versionId"] = "0.1.0"
        luis_json["name"] = self.name
        luis_json["desc"] = self.desc
        luis_json["culture"] = self.lang
        luis_json["intents"] = self.array_to_json(self.intents)
        luis_json["entities"] = self.array_to_json(self.entities)
        luis_json["bing_entities"] = self.array_to_json(self.bing_entities)
        luis_json["model_features"] = []
        luis_json["regex_features"] = []
        luis_json["regex_entities"] = []
        luis_json["composites"] = []
        luis_json["closedLists"] = []
        luis_json["utterances"] = self.utterances
        json_data = json.dumps(luis_json, indent=4, sort_keys=True, ensure_ascii=False)
        self.write_json(filename, json_data)



class DialogflowConverter(Converter):
    @staticmethod
    def zipdir(path, ziph):
        for root, dirs, files in os.walk(path):
            for file in files:
                ziph.write(os.path.join(root, file))

    @staticmethod
    def add_to_list(list, str_to_add):
        if str_to_add not in list:
            list.append(str_to_add)
        return list

    def __init__(self):
        super(DialogflowConverter, self).__init__()
        self.intents = {}
        self.entities = []


    def __add_entity(self, sentence):
        obj = None

        for e in self.entities:
            if e["name"] == sentence.entities["entity"]:
                obj = e
                break

        if obj == None:
            obj = {"name": sentence.entities["entity"], "values": []}
        self.entities.append(obj)


        s = Converter.tokenizer(sentence.text)
        value = ""
        e = sentence.entities

        for i in range(0, len(s)):
            if i in range(int(e["start"]), int(e["stop"])+1):
                value = value + " " + s[i]

        value = value.lstrip()
        value = " ".join(Converter.tokenizer(value)).replace("	", " ")
        self.add_to_list(obj["values"], value)

    def __add_utterance(self, sentence):
        entities = []

        for e in sentence.entities:
            entities.append({"entity":e["entity"],"startPos":e["start"],"endPos":e["stop"]})

        u = {"text": sentence.text, "intent": sentence.intent, "entities": entities}
        self.utterances.append(u)

        try:
            self.intents[u["intent"]]
        except KeyError as e:
            self.intents[u["intent"]] = []

        self.intents[u["intent"]].append(u)


    def import_corpus(self, filepath, name, lang):
        docs, X, y = parse_data_csv(filepath)

        self.name = name
        self.desc = filepath
        self.lang = lang

        for doc in docs.values():
            self.__add_utterance(AnnotatedSentence(doc["question"], doc['name'], []))
            for p in doc['paraphrased_questions']:
                self.__add_utterance(AnnotatedSentence(p, doc['name'], []))


    def __get_word(self, sentence, entity):
        s = Converter.tokenizer(sentence)
        value = ""
        e = entity
        for i in range(0, len(s)):
            if i in range(int(e["startPos"]), int(e["endPos"])+1):
                value = value + " " + s[i]
        value = value.lstrip()
        value = " ".join(Converter.tokenizer(value)).replace("	", " ")
        return value

    def __agent_to_json(self):
        my_json = {}
        my_json["language"] = self.lang
        my_json["enabledDomainFeatures"] = ['smalltalk-domain-on', 'smalltalk-fulfillment-on']
        my_json["defaultTimezone"] = "America/New_York"
        my_json["customClassifierMode"] = "use.after"
        my_json["mlMinConfidence"] = 0.2
        return json.dumps(my_json, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False)

    def __intent_to_json(self, intent):
        name = intent[0]['intent']

        my_json = {}
        my_json["name"] = name
        my_json["auto"] = True
        my_json["contexts"] = []
        my_json["priority"] = 500000
        my_json["fallbackIntent"] = False
        my_json["webhookUsed"] = False
        my_json["events"] = []

        response = {};
        response["affectedContexts"] = []
        response["resetContexts"] = False
        response["dataType"] = "@" + name
        response["name"] = name
        response["value"] = "$" + name
        parameter = {"isListe": False}
        message = {"type": 0, "speech":[]}
        response["parameters"] = [parameter]
        response["messages"] = [message]
        user_says = []

        counter = 0

        for s in intent:
            counter += 1

            j = {}
            words = []
            entities = s["entities"]
            sen = s["text"]
            entities = sorted(entities, key=lambda k: k['startPos'])

            for e in entities:
                word = Converter.detokenizer(self.__get_word(s["text"], e))
                split = ' '
                if word != '':
                    split = sen.split(word)

                if len(split[0]) > 0:
                    words.append({'text':split[0]})

                words.append({'text':word, 'userDefined':True, 'alias': e["entity"], 'meta':"@"+e["entity"]})

                try:
                    sen = split[1]
                except:
                    pass

            try:
                if len(entities) < 1:
                    words.append({'text':sen})
                elif len(split[1]) > 0:
                    words.append({'text':split[1]})
            except:
                pass

            j["data"] = words
            j["isTemplate"] = False
            j["count"] = 0
            j["id"] = hashlib.md5(str(counter).encode()).hexdigest()
            user_says.append(j)

        my_json["userSays"] = user_says
        my_json["responses"] = [response]

        return json.dumps(my_json, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False)

    def __entity_to_json(self, entity):
        my_json = {}
        my_json["name"] = entity["name"]
        my_json["isOverridable"] = True
        my_json["isEnum"] = True
        my_json["automatedExpansion"] = False

        entries = []
        for value in entity["values"]:
            e = {};
            e["value"] = Converter.detokenizer(value)
            e["synonyms"] = []
            entries.append(e)

        my_json["entries"] = entries
        return json.dumps(my_json, sort_keys=False, indent=4, separators=(',', ': '), ensure_ascii=False)


    def export(self, file):
        #create temp folder
        shutil.rmtree(self.name, ignore_errors=True)
        newpath = self.name
        if not os.path.exists(newpath):
            os.makedirs(newpath)
        os.makedirs(self.name +'/entities')
        os.makedirs(self.name +'/intents')

        #agent.json
        self.write_json(self.name +"/agent.json", self.__agent_to_json())
        #intents
        for i in self.intents:
            self.write_json(self.name +"/intents/" + i + ".json", self.__intent_to_json(self.intents[i]))
        #entities
        for e in self.entities:
            self.write_json(self.name +"/entities/" + e["name"] + ".json", self.__entity_to_json(e))

        #zip files
        zipf = zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED)
        self.zipdir(self.name, zipf)
        zipf.close()

        #remove temp files
        shutil.rmtree(self.name, ignore_errors=True)