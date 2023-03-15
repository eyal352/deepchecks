# ----------------------------------------------------------------------------
# Copyright (C) 2021-2023 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""The regression_error_distribution check module."""
from typing import Dict

import numpy as np
import pandas as pd
import plotly.express as px
from scipy.stats import kurtosis
from sklearn.metrics import mean_squared_error

from deepchecks.core import CheckResult, ConditionCategory, ConditionResult
from deepchecks.recommender.dataset import RecDataset
from deepchecks.tabular import SingleDatasetCheck
from deepchecks.recommender import Context
from deepchecks.utils.strings import format_number

__all__ = ['OperationsAmountSegmentPerformance']


class OperationsAmountSegmentPerformance(SingleDatasetCheck):
    """Check for systematic error and abnormal shape in the regression error distribution.

    The check shows the distribution of the regression error, and enables to set conditions on two
    of the distribution parameters: Systematic error and Kurtosis value.
    Kurtosis is a measure of the shape of the distribution, helping us understand if the distribution
    is significantly "wider" from a normal distribution.
    Systematic error, otherwise known as the error bias, is the mean prediction error of the model.

    Parameters
    ----------
    n_top_samples : int , default: 3
        amount of samples to show which have the largest under / over estimation errors.
    n_bins : int , default: 40
        number of bins to use for the histogram.
    n_samples : int , default: 1_000_000
        number of samples to use for this check.
    random_state : int, default: 42
        random seed for all check internals.
    """

    def __init__(self,
                 n_top_samples: int = 3,
                 scorer=None,
                 n_bins: int = 40,
                 random_state: int = 42,
                 **kwargs):
        super().__init__(**kwargs)
        self.scorer = scorer
        self.n_top_samples = n_top_samples
        self.n_bins = n_bins
        self.random_state = random_state

    def run_logic(self, context: Context, dataset_kind) -> CheckResult:
        """Run check.

        Returns
        -------
        CheckResult
            value is the kurtosis value (Fisher’s definition (normal ==> 0.0)).
            display is histogram of error distribution and the largest prediction errors.

        Raises
        ------
        DeepchecksValueError
            If the object is not a Dataset instance with a label
        """
        dataset: RecDataset = context.get_data_by_kind(dataset_kind)
        model = context.model
        scorer = context.get_single_scorer(self.scorer)
        per_user_scores = pd.Series(scorer(model, dataset), index=dataset.data[dataset.user_index_name].dropna())
        user_mean_scores = per_user_scores.groupby(level=0).agg(np.mean)
        user_op_amount = per_user_scores.groupby(level=0).agg('count')
        user_mean_scores.index = user_op_amount
        op_amount_score = pd.Series(user_mean_scores.reindex(), index=user_op_amount).groupby(level=0).agg(np.mean)

        if context.with_display:
            fig = px.histogram(
                x=op_amount_score.index,
                y=op_amount_score.values,
                nbins=self.n_bins,
                histfunc='avg',
                title='Operations Amount Segment Performance',
                labels={'x': 'Operations Amount', 'y': f'{scorer.name}'},
                height=500
            )

            fig.add_vline(x=np.median(op_amount_score), line_dash='dash', line_color='purple', annotation_text='median',
                          annotation_position=(
                'top left' if np.median(op_amount_score) < np.mean(op_amount_score) else 'top right'
            ))
            fig.add_vline(x=np.mean(op_amount_score), line_dash='dot', line_color='purple', annotation_text='mean',
                          annotation_position=(
                'top right' if np.median(op_amount_score) < np.mean(op_amount_score) else 'top left'
            ))

            display = fig
        else:
            display = None

        return CheckResult(value=op_amount_score, display=display)