"""Surrogate Modeling and Bayesian Optimization for Origami Metasurfaces.

Provides Gaussian Process / Kriging approximation for fast parameter evaluation
and Expected Improvement (EI) acquisition for directed search.
"""

from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np


class GaussianProcessSurrogate:
    """Lightweight Gaussian Process Regressor with RBF Kernel for fast EM response prediction."""

    def __init__(self, length_scale: float = 1.0, noise_variance: float = 1e-4) -> None:
        self.length_scale = length_scale
        self.noise_variance = noise_variance
        self.X_train: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.K_inv: Optional[np.ndarray] = None

    def _rbf_kernel(self, X1: np.ndarray, X2: np.ndarray) -> np.ndarray:
        """Compute squared exponential covariance matrix K(X1, X2)."""
        dist_sq = np.sum(X1 ** 2, axis=1)[:, np.newaxis] + np.sum(X2 ** 2, axis=1)[np.newaxis, :] - 2.0 * np.dot(X1, X2.T)
        return np.exp(-0.5 * dist_sq / (self.length_scale ** 2))

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        """Fit Gaussian Process on design parameter matrix X and target metric vector y."""
        self.X_train = np.asarray(X, dtype=np.float64)
        self.y_train = np.asarray(y, dtype=np.float64)

        K = self._rbf_kernel(self.X_train, self.X_train) + self.noise_variance * np.eye(len(self.X_train))
        try:
            self.K_inv = np.linalg.inv(K)
        except np.linalg.LinAlgError:
            self.K_inv = np.linalg.pinv(K)

    def predict(self, X_new: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Predict posterior mean mu(x) and variance sigma^2(x) at query points X_new."""
        if self.X_train is None or self.y_train is None or self.K_inv is None:
            raise ValueError("Surrogate model must be fit before calling predict().")

        X_query = np.asarray(X_new, dtype=np.float64)
        K_star = self._rbf_kernel(X_query, self.X_train)
        K_star_star = self._rbf_kernel(X_query, X_query)

        # Posterior mean: mu = K* . K^-1 . y
        mu = np.dot(K_star, np.dot(self.K_inv, self.y_train))

        # Posterior covariance: cov = K** - K* . K^-1 . K*^T
        v = np.dot(K_star, self.K_inv)
        sigma2 = np.diag(K_star_star - np.dot(v, K_star.T))
        sigma = np.sqrt(np.maximum(1e-8, sigma2))

        return mu, sigma

    def expected_improvement(self, X_candidates: np.ndarray, best_y: float, xi: float = 0.01) -> np.ndarray:
        """Compute Expected Improvement (EI) acquisition function for maximization."""
        mu, sigma = self.predict(X_candidates)
        improvement = mu - best_y - xi
        z = improvement / sigma

        # Analytical normal CDF and PDF
        phi = 0.5 * (1.0 + np.vectorize(math.erf)(z / math.sqrt(2.0)))
        norm_pdf = (1.0 / math.sqrt(2.0 * math.pi)) * np.exp(-0.5 * (z ** 2))

        ei = improvement * phi + sigma * norm_pdf
        return np.maximum(0.0, ei)
