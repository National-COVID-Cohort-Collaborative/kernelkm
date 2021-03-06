import numpy as np
from .kernel_k_means import KernelKMeans
from .my_matrix import MyMatrix


class GapStat:
    """Gap statistic for kernel k-means algorithm

    Gap statistic is a method for choosing an appropriate k (number of clusters) for
    k means clustering. See here for a good explanation:
    https://towardsdatascience.com/k-means-clustering-and-the-gap-statistics-4c5d414acd29
    """

    def __init__(self, datamat, patient_id_list, max_k=10, B=4, max_iter=100):
        """
        patient_id_list: square numpy matrix that defines pairwise similarity between data points (here patients)
        max_k: largest k (number of clusters) to investigate [10]
        B: number of permutations/randomizations for gapstat [4]
        max_iter: maximum number of iterations for k means clustering [100]
        """
        shape = datamat.shape
        if shape[0] != shape[1]:
            raise ValueError("datamat needs to be a square matrix")
        if shape[0] != len(patient_id_list):
            raise ValueError("datamat needs to have same dimension as patient_id_list")
        self._matrix = datamat
        self._pat_id_list = patient_id_list
        self._max_iter = max_iter
        self._max_k = max_k
        self._B = B

    def calculate_good_k(self, do_all_k=False):
        """Calculate a good k to use for k means clustering using the gap statistic

        data check in KernelKMeans class!
        do_all_k: If true, do not stop after we have found the optimum k, but go on up to self._max_k,
        which we need for outputting a GapStat figure and debugging, but do not need to actually get the 
        optimum k.
        """
        kkm = KernelKMeans(self._matrix, self._pat_id_list, self._max_iter)
        gap_stat = []
        s_stat = []
        opt_k = None
        # to test up to self._max_k we need the following range!
        for i in range(self._max_k):
            k = i + 1  # cluster count 
            centroids, centroid_assignments, errors = kkm.calculate(k=k)
            W_k_observed = self._calculate_W_k(self._matrix, centroids, centroid_assignments)
            W_k_expectation, s_k = self._get_avg_permuted_W_k(k)
            gap_k = W_k_expectation - W_k_observed
            gap_stat.append(gap_k)
            s_stat.append(s_k)
            # check if gap(k-1) \geq gap(k) - s_{k}
            if i > 0:
                if gap_stat[i-1] - gap_stat[i] + s_stat[i] > 0:
                    if not opt_k:
                        opt_k = k-1
                    if not do_all_k:
                        return opt_k, gap_stat
        if not opt_k:
            # couldnt find a good k, so set it to the highest value we tested
            opt_k = self._max_k
        return opt_k, gap_stat  # if we get here we do not have great clusters

    def _get_avg_permuted_W_k(self, this_k: int):
        w_k_estimate = []

        mm = MyMatrix(self._matrix)

        for i in range(self._B):
            randomized_M = mm.get_permuted_symmetric()
            kkm = KernelKMeans(randomized_M, self._pat_id_list, self._max_iter)
            centroids, centroid_assignments, errors = kkm.calculate(k=this_k)
            w_k_star = self._calculate_W_k(randomized_M, centroids, centroid_assignments)
            w_k_estimate.append(w_k_star)
        s_dk = np.std(w_k_estimate)
        s_k = s_dk * np.sqrt(1+1/self._B)
        return np.mean(w_k_estimate), s_k

    def _calculate_D_r(self, matrix, centroid, assigned_to_centroid):
        """
        sum of pairwise distances
        """
        D_j = 0
        n_r = np.count_nonzero(assigned_to_centroid)
        for i, i_bool in enumerate(assigned_to_centroid):
            for j, j_bool in enumerate(assigned_to_centroid):
                if (i < j):  # do top half of matrix along diagonal
                    continue
                if i_bool and j_bool:
                    d_ij = np.sqrt(np.sum((matrix[i, ]-matrix[j, ])**2))
                    D_j += d_ij
        return D_j/(n_r)

    def _calculate_W_k(self, matrix, centroids, centroid_assignments):
        k = len(centroids)
        W_k = 0
        for i in range(k):
            centroid = centroids[i]
            # check which patients are assigned to centroid i and make a boolean matrix
            # to indicate whether a patient belongs to centroid i (True) or not (False)
            assigned = [x == i for x in centroid_assignments]
            D_r = self._calculate_D_r(matrix, centroid, assigned)
            W_k += D_r
        return W_k
