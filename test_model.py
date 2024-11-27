from pathlib import Path

from flair.data import Sentence
from flair.models import SequenceTagger

# Paths
model_path = Path("resources/taggers/ecommerce-ner/best-model.pt")

# Load the trained model
tagger = SequenceTagger.load(model_path)


# Test the model on user-provided input
def test_sentence(sentence_text: str):
    sentence = Sentence(sentence_text)
    tagger.predict(sentence)
    print("Annotated Sentence:")
    print(sentence.to_tagged_string())


# Example usage
if __name__ == "__main__":
    while True:
        user_input = input("\nEnter a product description (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            break
        test_sentence(user_input)
