from pathlib import Path

from flair.data import Corpus
from flair.datasets import ColumnCorpus
from flair.embeddings import TransformerWordEmbeddings
from flair.models import SequenceTagger
from flair.trainers import ModelTrainer

# Paths
data_folder = Path("resources/data")
model_output = Path("resources/taggers/ecommerce-ner")

# Define the column format (text column is 0, NER tags are in column 1)
columns = {0: "text", 1: "ner"}

# Load the corpus (train, dev, and test files must exist in the data folder)
corpus: Corpus = ColumnCorpus(
    data_folder,
    columns,
    train_file="train.txt",
    test_file="test.txt",
    dev_file="dev.txt",
)

# Define the tag dictionary
tag_dictionary = corpus.make_tag_dictionary(tag_type="ner")

# Use pre-trained Transformer embeddings (e.g., BERT)
embeddings = TransformerWordEmbeddings("bert-base-uncased")

# Create the sequence tagger
tagger = SequenceTagger(
    hidden_size=256,
    embeddings=embeddings,
    tag_dictionary=tag_dictionary,
    tag_type="ner",
    use_crf=True,
)

# Train the model
trainer = ModelTrainer(tagger, corpus)
trainer.train(
    model_output,
    learning_rate=0.1,
    mini_batch_size=32,
    max_epochs=10,
)
print("Training complete. Model saved to:", model_output)
