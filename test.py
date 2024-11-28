from flair.data import Sentence
from flair.models import SequenceTagger
from flair.nn import Classifier

# make a sentence
sentence = Sentence("Cheap Samsung phones")
# sentence = Sentence('Bebida Alcoolica D Boa Mista C/Mel E Limao 700ml Cx 6un')

# load the NER tagger
# tagger = Classifier.load("ner-ontonotes-fast")
tagger = SequenceTagger.load("ner")

# run NER over sentence
tagger.predict(sentence)

# print the sentence with all annotations
print(sentence)
