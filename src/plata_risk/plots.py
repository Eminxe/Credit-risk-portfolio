import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import roc_curve  # noqa: E402

from plata_risk.common import OUTPUTS  # noqa: E402

plt.rcParams.update({"figure.figsize": (8, 5), "font.size": 11, "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 160})


def save(name):
    plt.tight_layout()
    plt.savefig(OUTPUTS / name)
    plt.close()


def credit_plots(y, predictions, deciles):
    styles = {"logistic": {"color": "#244b68", "linestyle": "--", "label": "Logistic regression"},
              "hist_gradient_boosting": {"color": "#da7a35", "linestyle": "-", "label": "Gradient boosting"}}
    for name, p in predictions.items():
        fpr, tpr, _ = roc_curve(y, p)
        plt.plot(fpr, tpr, **styles[name])
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.xlabel("False positive rate")
    plt.ylabel("True positive rate")
    plt.title(f"UCI 350 | Grouped holdout ROC | n={len(y):,}")
    plt.legend()
    save("case01_roc.png")
    for name, p in predictions.items():
        observed, predicted = calibration_curve(y, p, n_bins=10, strategy="quantile")
        plt.plot(predicted, observed, marker="o", **styles[name])
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.xlabel("Mean predicted monthly default probability")
    plt.ylabel("Observed default-payment rate")
    plt.title("UCI 350 | Holdout calibration | quantile bins")
    plt.legend()
    save("case01_calibration.png")
    plt.bar(deciles.decile, deciles.observed_rate, color="#244b68", label="Observed")
    plt.plot(deciles.decile, deciles.mean_pd, "o-", color="#da7a35", label="Predicted")
    plt.xlabel("Risk decile (10 = highest predicted risk)")
    plt.ylabel("Monthly default-payment rate")
    plt.title("UCI 350 | Holdout default rates by risk decile")
    plt.xticks(range(1, 11))
    plt.legend()
    save("case01_default_by_decile.png")
