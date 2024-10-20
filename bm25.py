from rank_bm25 import BM25Okapi
from typing import List


class BM25:
    def __init__(self, corpus: List[str], preprocess_func=None):
        """
        Initializes the BM25 model with the given corpus and an optional preprocessing function.

        Parameters:
            corpus (List[str]): A list of documents, where each document is a string.
            preprocess_func (callable, optional): A function to preprocess documents and queries.
        """
        # Use the provided preprocess function if it exists; otherwise, just split the strings.
        self.tokenized_corpus = [self.preprocess(doc) if preprocess_func is None else preprocess_func(doc) for doc in
                                 corpus]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        self.corpus = corpus

    @staticmethod
    def preprocess(document: str) -> List[str]:
        """
        Basic preprocessing of the document by lowercasing and splitting into tokens.

        Parameters:
            document (str): The document to preprocess.

        Returns:
            List[str]: A list of tokens from the preprocessed document.
        """
        return document.split(" ")

    def search(self, query: str, top_n: int = 5) -> List[str]:
        """
        Searches the corpus for the most relevant documents to the query.

        Parameters:
            query (str): The search query as a string.
            top_n (int): Number of top relevant documents to return (default is 5).

        Returns:
            List[str]: A list of top N relevant documents.
        """
        tokenized_query = self.preprocess(query)  # Tokenize the query
        return self.bm25.get_top_n(tokenized_query, self.corpus, n=top_n)

    def add_document(self, document: str):
        """
        Adds a new document to the corpus and updates the BM25 model.

        Parameters:
            document (str): The new document as a string.
        """
        self.tokenized_corpus.append(self.preprocess(document))  # Preprocess and append the document
        self.bm25 = BM25Okapi(self.tokenized_corpus)  # Rebuild the model with the updated corpus

if __name__ == "__main__":


    # Define the query and documents
    query = "weather"
    documents = [
        "Hello there good man!",
    "It is quite windy in London",
    "How is the weather today?"
    ]
    bm25_model = BM25(documents)
    result = bm25_model.search(query, top_n=1)
    print(result)


