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

"""This module contains the behaviours for the 'abstract_round_abci' skill."""

from typing import Any, Dict, Optional, Type, cast

from aea.exceptions import enforce
from aea.skills.behaviours import FSMBehaviour

from packages.valory.skills.abstract_round_abci.behaviour_utils import BaseState


State = Type[BaseState]
Action = Optional[str]
TransitionFunction = Dict[State, Dict[Action, State]]


class AbstractRoundBehaviour(FSMBehaviour):
    """This behaviour implements an abstract round."""

    initial_state_cls: State
    transition_function: TransitionFunction = {}

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the behaviour."""
        super().__init__(**kwargs)

        self._round_to_state: Dict[str, str] = {}
        self._last_round_id: Optional[str] = None

        # this variable overrides the actual next transition
        # due to ABCI app updates.
        self._next_state: Optional[str] = None

    def setup(self) -> None:
        """Set up the behaviour."""
        self._register_states(self.transition_function)

    def teardown(self) -> None:
        """Tear down the behaviour"""

    def act(self) -> None:
        """Implement the behaviour."""
        if self._last_round_id is None:
            self._last_round_id = self.context.state.period.current_round_id

        if self.current is None:  # type: ignore
            return

        self._process_current_round()

        current_state = self.current_state
        if current_state is None:
            return

        current_state.act_wrapper()

        if current_state.is_done():
            if current_state.name in self._final_states:
                # we reached a final state - return.
                self.context.logger.debug("%s is a final state", current_state.name)
                self.current = None
            # if next state is set, overwrite successor (regardless of the event)
            # this branch also handle the case when matching round of current state is not set
            elif self._next_state is not None:
                self.context.logger.debug(
                    "overriding transition: current state: '%s', next state: '%s'",
                    self.current,
                    self._next_state,
                )
                self.current = self._next_state
                self._next_state = None
            else:
                # otherwise, read the event and compute the next transition
                event = current_state.event
                next_state_name = self.transitions.get(self.current, {}).get(
                    event, None
                )
                self.context.logger.debug(
                    "current state: '%s', event: '%s', next state: '%s'",
                    self.current,
                    event,
                    next_state_name,
                )
                self.current = next_state_name
            # self.current_state now points to the next state
            next_state = self.current_state
            if next_state is not None:
                next_state.reset()

    @property
    def current_state(self) -> Optional[BaseState]:
        """Get the current state."""
        if self.current is not None:
            return cast(Optional[BaseState], self.get_state(self.current))
        return None

    def _register_states(self, transition_function: TransitionFunction) -> None:
        """Register a list of states."""
        enforce(
            len(transition_function) != 0,
            "empty list of state classes",
            exception_class=ValueError,
        )
        for state, outgoing_transitions in transition_function.items():
            self._register_state_if_not_registered(
                state, initial=state == self.initial_state_cls
            )
            for event, next_state in outgoing_transitions.items():
                self._register_state_if_not_registered(
                    next_state, initial=next_state == self.initial_state_cls
                )
                self.register_transition(state.state_id, next_state.state_id, event)

    def _register_state_if_not_registered(
        self, state_cls: Type[BaseState], initial: bool = False
    ) -> None:
        """Register state, if not already registered."""
        if state_cls.state_id not in self._name_to_state:
            self._register_state(state_cls, initial=initial)

    def _register_state(
        self, state_cls: Type[BaseState], initial: bool = False
    ) -> None:
        """Register state."""
        name = state_cls.state_id
        if state_cls.matching_round is not None:
            enforce(
                state_cls.matching_round.round_id not in self._round_to_state,
                "round id already used",
                exception_class=ValueError,
            )
            self._round_to_state[state_cls.matching_round.round_id] = name
        return super().register_state(
            name,
            state_cls(name=name, skill_context=self.context),
            initial=initial,
        )

    def _process_current_round(self) -> None:
        """Process current ABCIApp round."""
        current_round_id = self.context.state.period.current_round_id
        if self._last_round_id == current_round_id:
            # round has not changed - do nothing
            return
        self._last_round_id = current_round_id
        # the state behaviour might not have the matching round
        self._next_state = self._round_to_state.get(current_round_id, None)

        # checking if current state behaviour has a matching round.
        #  if so, stop it and replace it with the new state behaviour
        #  if not, then leave it running; the next state will be scheduled
        #  when current state is done
        current_state = self.current_state
        if (
            current_state is not None
            and current_state.matching_round is not None
            and current_state.state_id != self._next_state
        ):
            current_state.stop()
            self.current = self._next_state
            return
