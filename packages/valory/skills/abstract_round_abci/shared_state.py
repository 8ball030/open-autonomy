# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains the shared state for the price estimation ABCI application."""
import inspect
from typing import Any, Optional, Type

from aea.skills.base import Model

from packages.valory.skills.abstract_round_abci.base_models import AbstractRound, Period
from packages.valory.skills.abstract_round_abci.utils import locate


class SharedState(Model):
    """Keep the current shared state."""

    period: Period

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the state."""
        super().__init__(*args, **kwargs)

        initial_round_cls_dotted_path = kwargs.get("initial_round_cls")
        self.initial_round_cls = self._process_initial_round_cls(
            initial_round_cls_dotted_path
        )

    def setup(self) -> None:
        """Set up the model."""
        self.period = Period(self.initial_round_cls)

    @classmethod
    def _process_initial_round_cls(
        cls, initial_round_cls_dotted_path: Optional[str]
    ) -> Type[AbstractRound]:
        """Process the 'initial_round_cls' parameter."""
        if initial_round_cls_dotted_path is None:
            raise ValueError("'initial_round_cls' must be set")
        initial_round_cls = locate(initial_round_cls_dotted_path)
        if initial_round_cls is None:
            raise ValueError("'initial_round_cls' not found")
        if not inspect.isclass(initial_round_cls):
            raise ValueError(f"The object {initial_round_cls} is not a class")
        if not issubclass(initial_round_cls, AbstractRound):
            cls_name = AbstractRound.__name__
            cls_module = AbstractRound.__module__
            raise ValueError(
                f"The class {initial_round_cls} is not an instance of {cls_module}.{cls_name}"
            )
        return initial_round_cls