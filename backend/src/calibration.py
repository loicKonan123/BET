"""Calibration multiclasses sur une période ultérieure à l'apprentissage."""
import numpy as np
from scipy.optimize import minimize_scalar


def temperer(p, temperature=1.0):
    z = np.log(np.clip(np.asarray(p, dtype=float), 1e-9, 1)) / temperature
    z -= z.max(axis=-1, keepdims=True)
    out = np.exp(z)
    return out / out.sum(axis=-1, keepdims=True)


def temperature_optimale(p, y):
    p, y = np.asarray(p), np.asarray(y, dtype=int)
    if len(y) < 30 or len(set(y)) < 3:
        return 1.0
    def loss(t):
        return -np.log(temperer(p, t)[np.arange(len(y)), y]).mean()
    fit = minimize_scalar(loss, bounds=(0.5, 3.0), method="bounded")
    return float(fit.x) if fit.success else 1.0


class ClassifieurCalibre:
    """Le classifieur reste ajusté sur le passé ; T est appris sur le bloc suivant."""
    def __init__(self, base, temperature):
        self.base = base
        self.temperature = temperature
        self.classes_ = base.classes_

    def predict_proba(self, x):
        return temperer(self.base.predict_proba(x), self.temperature)

    def predict(self, x):
        return self.classes_[np.argmax(self.predict_proba(x), axis=1)]


def ajuster_calibre(base, x, y, dates, fraction=0.8):
    x, y = np.asarray(x), np.asarray(y)
    if len(y) < 80:
        return None
    cut = int(len(y) * fraction)
    # Pas de match d'une même date partagé entre apprentissage et calibration.
    while cut > 0 and dates[cut - 1] >= dates[cut]:
        cut -= 1
    if cut < 40 or len(y) - cut < 20 or len(set(y[:cut])) < 3:
        return None
    base.fit(x[:cut], y[:cut])
    return ClassifieurCalibre(base, temperature_optimale(base.predict_proba(x[cut:]), y[cut:]))
