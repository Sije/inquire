#!/usr/bin/env python2

""" Python question answering """
from __future__ import absolute_import
import argparse
import codecs
import uuid
import json
import logging as log

from . import config
from .retrieval import documents
from .classification import model
from .extraction import get_extractor, NoExtractorError

config.init()

def answer_question(question, confidence=False):
    """
    Main pipeline for question answering
    Takes a question and returns the most likely answer
    """
    question = question.strip()
    log.info("answering question: " + question)
    coarse, fine = classify_question(question)
    try:
        extractor = get_extractor(coarse, fine)
    except NoExtractorError:
        cache_question(question, None)
        # return ("I don't know how to answer that type of question yet.", 1.0)
        if confidence:
            return (None, 1.0)
        return "Sorry, no answers found."

    # wait to get docs until we know we can handle the question
    log.debug("retrieving documents...")
    docs = documents.get_documents(question)
    #answer_candidates(docs)

    # returns a sorted list of tuples
    answers = extractor(question, docs).answer()
    if answers is None:
        cache_question(question, [])
        log.info("No answers found!")
        if confidence:
            return (None, 1.0)
        return "Sorry, no answers found."
    else:
        cache_question(question, answers)
        log.info("best answer: " + answers[0][0])
        if config.DEBUG:
            print_top_answers(answers)
        # else:
        #     print_answer(answers[0][0])
    if confidence:
        return answers[0]
    return answers[0][0]

def classify_question(question):
    """
    load the model and classify the question
    returns the coarse and fine classes
    """
    log.debug("classifying question...")
    clf = model.Classifier().load_model()
    coarse, fine = clf.predict(question)
    log.info("question classified as: {}: {}".format(coarse, fine))
    return coarse, fine

def cache_question(question, answers):
    """ write the question and answers to the cache file """
    if config.CACHE_QUESTION:
        with codecs.open(config.QUESTION_CACHE_FILE, "a", "utf-8") as out:
            out.write(json.dumps({
                str(uuid.uuid4()): {'question': question, 'answers': answers}
            }, ensure_ascii=False) + '\n')


def print_answer(answer):
    """ print the selected answer """
    print("-" * 40)
    print(u"Answer: " + answer)
    print("-" * 40)

def print_top_answers(answers):
    """ print all the answer candidates """
    print("Possible answers:")
    print("-" * 40)
    for res in answers:
        print(unicode(u"{0:.2f}\t{1}".format(res[1], res[0])))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Answer a question')
    parser.add_argument("question")
    parser.add_argument("-d", "--debug", help="set logger to debug level", action="store_true")
    parser.add_argument("-m", "--mock_search", help="don't make a real search engine request",
                        action="store_true")
    parser.add_argument("-C", "--nocache", help="don't cache the question/answer",
                        action="store_true")
    args = parser.parse_args()
    config.init(debug=args.debug)
    if args.mock_search:
        config.BING_MOCK_REQUEST = True
    if args.nocache:
        config.CACHE_QUESTION = False
    answer_question(args.question)

