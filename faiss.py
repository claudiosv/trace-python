# https://gist.github.com/j-adamczyk/74ee808ffd53cd8545a49f185a908584#file-knn_with_faiss-py

import numpy as np
import faiss


class FaissKNeighbors:
    def __init__(self, k=5):
        self.index = None
        self.y = None
        self.k = k

    def fit(self, X, y):
        self.index = faiss.IndexFlatL2(X.shape[1])
        self.index.add(X.astype(np.float32))
        self.y = y

    def predict(self, X):
        distances, indices = self.index.search(X.astype(np.float32), k=self.k)
        votes = self.y[indices]
        predictions = np.array([np.argmax(np.bincount(x)) for x in votes])
        return predictions

"""
the index attribute holds the data structure created by faiss to speed up nearest neighbor search
data that we put in the index has to be the Numpy float32 type
we use IndexFlatL2 here, which is the simplest exact nearest neighbor search with Euclidean distance (L2 norm), very similar to the default Scikit-learn KNeighborsClassifier; you can also use other metrics (metrics docs) and types of indices (indices docs), e. g. for approximate nearest neighbor search
the .search() method returns distances to k nearest neighbors and their indices; we only care about the indices here, but you could e. g. implement distance weighted nearest neighbors with the additional information
indices returned by .search() are 2D matrix, where n-th row contains indices of the k nearest neighbors; with self.y[indices], we turn those indices into the classes of the nearest neighbors, so we know the votes for each sample
np.argmax(np.bincount(x)) returns the most popular number from the x array, which is the predicted class; we do this for every row, i. e. for every sample that we have to classify
"""