# ----------------------------------------------------------------------------
# Copyright (C) 2021-2022 Deepchecks (https://www.deepchecks.com)
#
# This file is part of Deepchecks.
# Deepchecks is distributed under the terms of the GNU Affero General
# Public License (version 3 or later).
# You should have received a copy of the GNU Affero General Public License
# along with Deepchecks.  If not, see <http://www.gnu.org/licenses/>.
# ----------------------------------------------------------------------------
#
"""The dataset module containing the tabular Dataset class and its functions."""
import collections
import typing as t
from operator import itemgetter

import numpy as np
import pandas as pd

from deepchecks.core.errors import DeepchecksNotSupportedError, DeepchecksValueError
from deepchecks.nlp.utils.task_type import TaskType

__all__ = ['TextData', 'TTokenLabel', 'TClassLabel', 'TTextLabel']

from deepchecks.utils.logger import get_logger

TDataset = t.TypeVar('TDataset', bound='TextData')
TSingleLabel = t.Tuple[int, str]
TClassLabel = t.Sequence[t.Union[TSingleLabel, t.Tuple[TSingleLabel]]]
TTokenLabel = t.Sequence[t.Sequence[t.Union[str, int]]]
TTextLabel = t.Union[TClassLabel, TTokenLabel]


class TextData:
    """
    TextData wraps together the raw text data and the labels for the nlp task.

    The TextData class contains additional data and methods intended for easily accessing
    metadata relevant for the training or validating of ML models.

    Parameters
    ----------
    raw_text : t.Sequence[str], default: None
        The raw text data, a sequence of strings representing the raw text of each sample.
        If not given, tokenized_text must be given, and raw_text will be created from it by joining the tokens with
        spaces.
    tokenized_text : t.Sequence[t.Sequence[str]], default: None
        The tokenized text data, a sequence of sequences of strings representing the tokenized text of each sample.
        Only relevant for task_type 'token_classification'.
        If not given, raw_text must be given, and tokenized_text will be created from it by splitting the text by
        spaces.
    label : t.Optional[TTextLabel], default: None
        The label for the text data. Can be either a text_classification label or a token_classification label.
        If None, the label is not set.
        - text_classification label - For text classification the accepted label format differs between multilabel and
          single label cases. For single label data, the label should be passed as a sequence of labels, with one entry
          per sample that can be either a string or an integer. For multilabel data, the label should be passed as a
          sequence of sequences, with the sequence for each sample being a binary vector, representing the presence of
          the i-th label in that sample.
        - token_classification label - For token classification the accepted label format is the IOB format or similar
          to it. The Label must be a sequence of sequences of strings or integers, with each sequence corresponding to
          a sample in the tokenized text, and exactly the length of the corresponding tokenized text.
    task_type : str, default: None
        The task type for the text data. Can be either 'text_classification' or 'token_classification'. Must be set if
        label is provided.
    dataset_name : t.Optional[str] , default: None
        The name of the dataset. If None, the dataset name will be defined when running it within a check.
    index : t.Optional[t.Sequence[int]] , default: None
        The index of the samples. If None, the index is set to np.arange(len(raw_text)).
    """

    _text: t.Sequence[str]
    _label: TTextLabel
    index: t.Sequence[t.Any]
    _task_type: t.Optional[TaskType]
    _has_label: bool
    _is_multilabel: bool = False
    name: t.Optional[str] = None

    def __init__(
            self,
            raw_text: t.Optional[t.Sequence[str]] = None,
            tokenized_text: t.Optional[t.Sequence[t.Sequence[str]]] = None,
            label: t.Optional[TTextLabel] = None,
            task_type: t.Optional[str] = None,
            dataset_name: t.Optional[str] = None,
            index: t.Optional[t.Sequence[t.Any]] = None,
    ):
        # Require explicitly setting task type if label is provided
        if task_type in [None, 'other']:
            if label is not None:
                if isinstance(label, t.Sequence):
                    if pd.notnull(label).any():
                        raise DeepchecksValueError('task_type must be set when label is provided')
                else:
                    raise DeepchecksValueError('task_type must be set when label is provided')

            self._task_type = TaskType.OTHER
        elif task_type == 'text_classification':
            self._task_type = TaskType.TEXT_CLASSIFICATION
        elif task_type == 'token_classification':
            self._task_type = TaskType.TOKEN_CLASSIFICATION
        else:
            raise DeepchecksNotSupportedError(f'task_type {task_type} is not supported, must be one of '
                                              f'text_classification, token_classification, other')

        if raw_text is None and tokenized_text is None:
            raise DeepchecksValueError('raw_text and tokenized_text cannot both be None')
        elif raw_text is None:
            self._validate_tokenized_text(tokenized_text)
            raw_text = [' '.join(tokens) for tokens in tokenized_text]
        elif tokenized_text is None:
            self._validate_text(raw_text)
            if self._task_type == TaskType.TOKEN_CLASSIFICATION:
                tokenized_text = [text.split() for text in raw_text] #TODO: Improve this (remove special characters etc.)
        else:
            self._validate_text(raw_text)
            self._validate_tokenized_text(tokenized_text)
            if len(raw_text) != len(tokenized_text):
                raise DeepchecksValueError('raw_text and tokenized_text must have the same length')

        if index is None:
            index = np.arange(len(raw_text))
        elif len(index) != len(raw_text):
            raise DeepchecksValueError('index must be the same length as raw_text')

        self.index = index
        self._text = raw_text
        self._tokenized_text = tokenized_text
        self._validate_and_set_label(label, raw_text, tokenized_text)

        if dataset_name is not None:
            if not isinstance(dataset_name, str):
                raise DeepchecksNotSupportedError(f'dataset_name type {type(dataset_name)} is not supported, must be a'
                                                  f' str')
        self.name = dataset_name

    @staticmethod
    def _validate_text(raw_text: t.Sequence[str]):
        """Validate text format."""
        error_string = 'raw_text must be a Sequence of strings'
        if not isinstance(raw_text, collections.abc.Sequence):
            raise DeepchecksValueError(error_string)
        if not all(isinstance(x, str) for x in raw_text):
            raise DeepchecksValueError(error_string)

    @staticmethod
    def _validate_tokenized_text(tokenized_text: t.Sequence[t.Sequence[str]]):
        """Validate tokenized text format."""
        error_string = 'tokenized_text must be a Sequence of sequences of strings'
        if not isinstance(tokenized_text, collections.abc.Sequence):
            raise DeepchecksValueError(error_string)
        if not all(isinstance(x, collections.abc.Sequence) for x in tokenized_text):
            raise DeepchecksValueError(error_string)
        if not all(isinstance(x, str) for tokens in tokenized_text for x in tokens):
            raise DeepchecksValueError(error_string)

    def _validate_and_set_label(self, label: t.Optional[TTextLabel], raw_text: t.Sequence[str],
                                tokenized_text: t.Sequence[t.Sequence[str]]):
        """Validate and process label to accepted formats."""
        # If label is not set, create an empty label of nulls
        self._has_label = True
        if label is None:
            self._has_label = False
            label = [None] * len(raw_text)

        if not isinstance(label, collections.abc.Sequence) or isinstance(label, str):
            raise DeepchecksValueError('label must be a Sequence')

        if not len(label) == len(raw_text):
            raise DeepchecksValueError('label must be the same length as raw_text')

        if self.task_type == TaskType.TEXT_CLASSIFICATION:
            if all((isinstance(x, collections.abc.Sequence) and not isinstance(x, str)) for x in label):
                self._is_multilabel = True
                multilabel_error = 'multilabel was identified. It must be a Sequence of Sequences of 0 or 1.'
                if not all(all(y in (0, 1) for y in x) for x in label):
                    raise DeepchecksValueError(multilabel_error)
                if any(len(label[0]) != len(label[i]) for i in range(len(label))):
                    raise DeepchecksValueError('All multilabel entries must be of the same length, which is the number'
                                               ' of classes.')
            elif not all(isinstance(x, (str, int)) for x in label):
                raise DeepchecksValueError('label must be a Sequence of strings or ints or a Sequence of Sequences'
                                           'of strings or ints (for multilabel classification)')

        if self.task_type == TaskType.TOKEN_CLASSIFICATION:
            token_class_error = 'label must be a Sequence of Sequences of either strings or integers'
            if not all(isinstance(x, collections.abc.Sequence) for x in label):
                raise DeepchecksValueError(token_class_error)

            for i in range(len(label)):  # TODO: Runs on all labels, very costly
                if not (all(isinstance(x, str) for x in label[i]) or all(isinstance(x, int) for x in label[i])):
                    raise DeepchecksValueError(token_class_error)
                if not len(label[i]) == len(tokenized_text[i]):
                    raise DeepchecksValueError(f'label must be the same length as tokenized_text. '
                                               f'However, for sample index {self.index[i]} of length '
                                               f'{len(tokenized_text[i])} received label of length {len(label[i])}')

        self._label = label

    def copy(self: TDataset, raw_text: t.Optional[t.Sequence[str]] = None,
             tokenized_text: t.Optional[t.Sequence[t.Sequence[str]]] = None,
             label: t.Optional[TTextLabel] = None,
             index: t.Optional[t.Sequence[int]] = None) -> TDataset:
        """Create a copy of this Dataset with new data."""
        cls = type(self)
        if raw_text is None:
            raw_text = self.text
        if tokenized_text is None:
            tokenized_text = self.tokenized_text
        if label is None:
            label = self.label
        if index is None:
            index = self.index
        get_logger().disabled = True  # Make sure we won't get the warning for setting class in the non multilabel case
        new_copy = cls(raw_text=raw_text, tokenized_text=tokenized_text, label=label, task_type=self._task_type.value,
                       dataset_name=self.name, index=index)
        get_logger().disabled = False
        return new_copy

    def sample(self: TDataset, n_samples: int, replace: bool = False, random_state: t.Optional[int] = None,
               drop_na_label: bool = False) -> TDataset:
        """Create a copy of the dataset object, with the internal data being a sample of the original data.

        Parameters
        ----------
        n_samples : int
            Number of samples to draw.
        replace : bool, default: False
            Whether to sample with replacement.
        random_state : t.Optional[int] , default None
            Random state.
        drop_na_label : bool, default: False
            Whether to take sample only from rows with exiting label.

        Returns
        -------
        Dataset
            instance of the Dataset with sampled internal dataframe.
        """
        samples = self.index
        if drop_na_label and self.has_label():
            samples = samples[pd.notnull(self._label)]
        n_samples = min(n_samples, len(samples))

        np.random.seed(random_state)
        sample_idx = np.random.choice(range(len(samples)), n_samples, replace=replace)
        if len(sample_idx) > 1:
            data_to_sample = {
                'raw_text': list(itemgetter(*sample_idx)(self._text)),
                'tokenized_text': list(itemgetter(*sample_idx)(self._tokenized_text)) if self._tokenized_text else None,
                'label': list(itemgetter(*sample_idx)(self._label)),
                'index': [self.index[i] for i in sample_idx]}
        else:
            data_to_sample = {'raw_text': [self._text[sample_idx[0]]],
                              'tokenized_text': [self._tokenized_text[sample_idx[0]]] if self._tokenized_text else None,
                              'label': [self._label[sample_idx[0]]],
                              'index': self.index[sample_idx]}
        return self.copy(**data_to_sample)

    def get_raw_sample(self, index: t.Any) -> str:
        """Get the raw text of a sample.

        Parameters
        ----------
        index : int
            Index of sample to get.

        Returns
        -------
        str
            Raw text of sample.
        """
        return self._text[self.index.index(index)]

    def get_tokenized_sample(self, index: t.Any) -> t.List[str]:
        """Get the tokenized text of a sample.

        Parameters
        ----------
        index : int
            Index of sample to get.

        Returns
        -------
        List[str]
            Tokenized text of sample.
        """
        if self._tokenized_text is None:
            raise DeepchecksValueError('Dataset does not contain tokenized text')
        return self._tokenized_text[self.index.index(index)]

    @staticmethod
    def separate_text(text: str):
        return text.replace_many(['.', ',', ';', ':', '!', '?', '(', ')', '[', ']', '{', '}', '"'], [' ']).split()

    @property
    def n_samples(self) -> int:
        """Return number of samples in the dataset.

        Returns
        -------
        int
            Number of samples in dataset
        """
        return len(self._text)

    def __len__(self):
        """Return number of samples in the dataset."""
        return self.n_samples

    @property
    def task_type(self) -> t.Optional[TaskType]:
        """Return the task type.

        Returns
        -------
        t.Optional[TaskType]
            Task type
        """
        return self._task_type

    @property
    def text(self) -> t.Sequence[str]:
        """Return sequence of raw text samples.

        Returns
        -------
        t.Sequence[str]
           Sequence of raw text samples.
        """
        return self._text

    @property
    def tokenized_text(self) -> t.Sequence[t.Sequence[str]]:
        """Return sequence of tokenized text samples.

        Returns
        -------
        t.Sequence[t.Sequence[str]]
           Sequence of tokenized text samples.
        """
        return self._tokenized_text

    @property
    def label(self) -> TTextLabel:
        """Return the label defined in the dataset.

        Returns
        -------
        TTextLabel
        """
        return self._label

    @property
    def is_multilabel(self) -> bool:
        """Return True if label is multilabel.

        Returns
        -------
        bool
            True if label is multilabel.
        """
        return self._is_multilabel

    def has_label(self) -> bool:
        """Return True if label was set.

        Returns
        -------
        bool
           True if label was set.
        """
        return self._has_label

    @classmethod
    def cast_to_dataset(cls, obj: t.Any) -> 'TextData':
        """Verify Dataset or transform to Dataset.

        Function verifies that provided value is a non-empty instance of Dataset,
        otherwise raises an exception, but if the 'cast' flag is set to True it will
        also try to transform provided value to the Dataset instance.

        Parameters
        ----------
        obj
            value to verify

        Raises
        ------
        DeepchecksValueError
            if the provided value is not a TextData instance;
            if the provided value cannot be transformed into Dataset instance;
        """
        if not isinstance(obj, cls):
            raise DeepchecksValueError(f'{obj} is not a {cls.__name__} instance')
        return obj.copy()

    @classmethod
    def datasets_share_task_type(cls, *datasets: 'TextData') -> bool:
        """Verify that all provided datasets share same label name and task types.

        Parameters
        ----------
        datasets : List[TextData]
            list of TextData to validate

        Returns
        -------
        bool
            True if all TextData share same label names and task types, otherwise False

        Raises
        ------
        AssertionError
            'datasets' parameter is not a list;
            'datasets' contains less than one dataset;
        """
        assert len(datasets) > 1, "'datasets' must contains at least two items"

        task_type = datasets[0].task_type

        for ds in datasets[1:]:
            if ds.task_type != task_type:
                return False

        return True

    def len_when_sampled(self, n_samples: int):
        """Return number of samples in the sampled dataframe this dataset is sampled with n_samples samples."""
        return min(len(self), n_samples)

    def is_sampled(self, n_samples: int):
        """Return True if the dataset number of samples will decrease when sampled with n_samples samples."""
        return len(self) > n_samples