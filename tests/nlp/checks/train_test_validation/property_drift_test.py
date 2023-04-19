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
"""Test for the NLP PropertyDrift check"""
import random
import typing as t

from hamcrest import *

from deepchecks.nlp.checks import PropertyDrift
from deepchecks.nlp.text_data import TextData


class TestTextClassification:

    def test_with_datasets_without_drift(self, tweet_emotion_train_test_textdata):
        # Arrange
        train, _ = tweet_emotion_train_test_textdata
        check = PropertyDrift().add_condition_drift_score_less_than()
        # Act
        result = check.run(train_dataset=train, test_dataset=train)
        condition_results = check.conditions_decision(result)
        # Assert
        assert len(condition_results) == 1
        assert condition_results[0].is_pass() is True

        assert_that(result.value, has_entries({
            "Formality": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "Language": {"Drift score": 0.0, "Method": "Cramer's V"},
            "Subjectivity": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "Average Word Length": {"Drift score": 0.0,"Method": "Kolmogorov-Smirnov"},
            "Text Length": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "Max Word Length": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "Toxicity": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "% Special Characters": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "Sentiment": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
            "Fluency": {"Drift score": 0.0, "Method": "Kolmogorov-Smirnov"},
        }))  # type: ignore


    def test_with_drifted_datasets(self, tweet_emotion_train_test_textdata):
        # Arrange
        train, test = tweet_emotion_train_test_textdata
        train = train.sample(20, random_state=0)
        test = test.sample(20, random_state=0)

        train.calculate_default_properties()
        test.calculate_default_properties()

        check = PropertyDrift().add_condition_drift_score_less_than()

        # Act
        result = check.run(train_dataset=train, test_dataset=test)
        condition_results = check.conditions_decision(result)

        # Assert
        assert len(condition_results) == 1
        assert condition_results[0].is_pass() is False

        assert_that(result.value, has_entries({
            "Subjectivity": {"Drift score": 0.15000000000000002, "Method": "Kolmogorov-Smirnov"},
            "Average Word Length": {"Drift score": 0.4, "Method": "Kolmogorov-Smirnov"},
            "Text Length": {"Drift score": 0.19999999999999996, "Method": "Kolmogorov-Smirnov"},
            "Max Word Length": {"Drift score": 0.19999999999999996, "Method": "Kolmogorov-Smirnov"},
            "% Special Characters": {"Drift score": 0.19999999999999996, "Method": "Kolmogorov-Smirnov"},
            "Sentiment": {"Drift score": 0.15000000000000002,"Method": "Kolmogorov-Smirnov"},
        }))  # type: ignore


class TestTokenClassification:

    def test_without_drift(self, small_wikiann: t.Tuple[TextData, TextData]):
        # Arrange
        train, _ = small_wikiann
        train.calculate_default_properties()
        check = PropertyDrift().add_condition_drift_score_less_than()
        # Act
        result = check.run(train_dataset=train, test_dataset=train)
        condition_results = check.conditions_decision(result)
        # Assert
        assert len(condition_results) == 1
        assert condition_results[0].is_pass() is True

        assert_that(result.value, has_entries({
            'Text Length': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            '% Special Characters': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Sentiment': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Average Word Length': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Subjectivity': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Max Word Length': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'})
        }))  # type: ignore


    def test_with_drift(self, small_wikiann: t.Tuple[TextData, TextData]):
        # Arrange
        train, test = small_wikiann

        train.calculate_default_properties(
            include_long_calculation_properties=False
        )
        test.calculate_default_properties(
            include_long_calculation_properties=False
        )

        check = PropertyDrift().add_condition_drift_score_less_than()

        # Act
        result = check.run(train_dataset=train, test_dataset=test)
        condition_results = check.conditions_decision(result)

        # Assert
        assert len(condition_results) == 1
        assert condition_results[0].is_pass() is False

        assert_that(result.value, has_entries({
            'Max Word Length': has_entries({'Drift score': 0.18000000000000005, 'Method': 'Kolmogorov-Smirnov'}),
            'Average Word Length': has_entries({'Drift score': 0.1, 'Method': 'Kolmogorov-Smirnov'}),
            '% Special Characters': has_entries({'Drift score': 0.16000000000000003, 'Method': 'Kolmogorov-Smirnov'}),
            'Text Length': has_entries({'Drift score': 0.30000000000000004, 'Method': 'Kolmogorov-Smirnov'}),
            'Subjectivity': has_entries({'Drift score': 0.14, 'Method': 'Kolmogorov-Smirnov'}),
            'Sentiment': has_entries({'Drift score': 0.08000000000000007, 'Method': 'Kolmogorov-Smirnov'})
        }))  # type: ignore


class TestMultiLabelClassification:

    def generate_dataset(self):
        return TextData(
            raw_text=[
                random.choice(['I think therefore I am', 'I am therefore I think', 'I am'])
                for _ in range(20)
            ],
            label=[
                random.choice([[0, 0, 1], [1, 1, 0], [0, 1, 0]])
                for _ in range(20)
            ],
            task_type='text_classification'
        )

    def test_without_drift(self):
        # Arrange
        train = self.generate_dataset()
        train.calculate_default_properties()
        check = PropertyDrift().add_condition_drift_score_less_than()
        # Act
        result = check.run(train_dataset=train, test_dataset=train)
        condition_results = check.conditions_decision(result)
        # Assert
        assert len(condition_results) == 1
        assert condition_results[0].is_pass() is True

        assert_that(result.value, has_entries({
            'Text Length': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            '% Special Characters': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Sentiment': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Average Word Length': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Subjectivity': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'}),
            'Max Word Length': has_entries({'Drift score': 0.0, 'Method': 'Kolmogorov-Smirnov'})
        }))  # type: ignore