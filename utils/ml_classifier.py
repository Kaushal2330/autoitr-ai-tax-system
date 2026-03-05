from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import logging

logger = logging.getLogger(__name__)

class TransactionClassifier:
    def __init__(self):
        self.model = None
        self.categories = ['salary', 'interest', 'dividend', 'transfer', 'unknown']
        self._train_model()

    def classify(self, description):
        try:
            if not self.model:
                return 'unknown'

            prediction = self.model.predict([description.lower()])[0]
            return prediction
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return 'unknown'

    def _train_model(self):
        try:
            training_data = [
                ("salary credit", "salary"),
                ("interest credited", "interest"),
                ("dividend", "dividend"),
                ("transfer", "transfer")
            ]

            descriptions = [item[0] for item in training_data]
            labels = [item[1] for item in training_data]

            self.model = Pipeline([
                ('tfidf', TfidfVectorizer()),
                ('classifier', MultinomialNB())
            ])

            self.model.fit(descriptions, labels)
        except Exception as e:
            logger.error(f"Model training failed: {e}")
