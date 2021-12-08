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

"""Test the base round classes."""

import re
from typing import (
    AbstractSet,
    Any,
    Callable,
    Dict,
    FrozenSet,
    Generator,
    List,
    Mapping,
    Optional,
    Type,
    cast,
)
from unittest import mock

import pytest

from packages.valory.skills.abstract_round_abci.base import (
    ABCIAppInternalError,
    AbstractRound,
    BasePeriodState,
    BaseTxPayload,
    CollectDifferentUntilAllRound,
    CollectDifferentUntilThresholdRound,
    CollectSameUntilThresholdRound,
    CollectionRound,
    ConsensusParams,
    OnlyKeeperSendsRound,
    TransactionNotValidError,
    VotingRound,
)


MAX_PARTICIPANTS: int = 4


def get_participants() -> FrozenSet[str]:
    """Participants"""
    return frozenset([f"agent_{i}" for i in range(MAX_PARTICIPANTS)])


class DummyTxPayload(BaseTxPayload):
    """Dummy Transaction Payload."""

    transaction_type = "DummyPayload"
    _value: str
    _vote: bool

    def __init__(self, sender: str, value: Any, vote: bool = False) -> None:
        """Initialize a dummy transaction payload."""

        super().__init__(sender, None)
        self._value = value
        self._vote = vote

    @property
    def value(self) -> Any:
        """Get the tx value."""
        return self._value

    @property
    def vote(self) -> bool:
        """Get the vote value."""
        return self._vote


class DummyPeriodState(BasePeriodState):
    """Dummy Period state for tests."""

    def __init__(
        self,
        participants: Optional[AbstractSet[str]] = None,
        period_count: Optional[int] = None,
        period_setup_params: Optional[Dict] = None,
        most_voted_keeper_address: Optional[str] = None,
    ) -> None:
        """Initialize DummyPeriodState."""

        super().__init__(
            participants=participants,
            period_count=period_count,
            period_setup_params=period_setup_params,
        )
        self._most_voted_keeper_address = most_voted_keeper_address

    @property
    def most_voted_keeper_address(
        self,
    ) -> Optional[str]:
        """Returns value for _most_voted_keeper_address."""
        return self._most_voted_keeper_address


def get_dummy_tx_payloads(
    participants: FrozenSet[str],
    value: Any = None,
    vote: bool = False,
    is_value_none: bool = False,
) -> List[DummyTxPayload]:
    """Returns a list of DummyTxPayload objects."""
    return [
        DummyTxPayload(
            sender=agent,
            value=(value or agent) if not is_value_none else value,
            vote=vote,
        )
        for agent in sorted(participants)
    ]


class DummyRound(AbstractRound):
    """Dummy round."""

    round_id = "round_id"
    allowed_tx_type = DummyTxPayload.transaction_type
    payload_attribute = "value"

    def end_block(self) -> None:
        """end_block method."""


class DummyCollectionRound(CollectionRound, DummyRound):
    """Dummy Class for CollectionRound"""


class DummyCollectDifferentUntilAllRound(CollectDifferentUntilAllRound, DummyRound):
    """Dummy Class for CollectDifferentUntilAllRound"""


class DummyCollectDifferentUntilThresholdRound(
    CollectDifferentUntilThresholdRound, DummyRound
):
    """Dummy Class for CollectDifferentUntilThresholdRound"""


class DummyCollectSameUntilThresholdRound(CollectSameUntilThresholdRound, DummyRound):
    """Dummy Class for CollectSameUntilThresholdRound"""


class DummyOnlyKeeperSendsRound(OnlyKeeperSendsRound, DummyRound):
    """Dummy Class for OnlyKeeperSendsRound"""


class DummyVotingRound(VotingRound, DummyRound):
    """Dummy Class for VotingRound"""


class BaseRoundTestClass:
    """Base test class."""

    period_state: BasePeriodState
    participants: FrozenSet[str]
    consensus_params: ConsensusParams

    _period_state_class: Type[BasePeriodState]
    _event_class: Any

    @classmethod
    def setup(
        cls,
    ) -> None:
        """Setup test class."""

        cls.participants = get_participants()
        cls.period_state = cls._period_state_class(
            participants=cls.participants
        )  # type: ignore
        cls.consensus_params = ConsensusParams(max_participants=MAX_PARTICIPANTS)

    def _test_no_majority_event(self, round_obj: AbstractRound) -> None:
        """Test the NO_MAJORITY event."""
        with mock.patch.object(round_obj, "is_majority_possible", return_value=False):
            result = round_obj.end_block()
            assert result is not None
            _, event = result
            assert event == self._event_class.NO_MAJORITY

    def _complete_run(self, test_runner: Generator, iter_count: int = 4) -> None:
        """
        This method represents logic to execute test logic defined in _test_round method.

        _test_round should follow these steps

        1. process first payload
        2. yield test_round
        3. test collection, end_block and thresholds
        4. process rest of the payloads
        5. yield test_round
        6. yield state, event ( returned from end_block )
        7. test state and event

        :param test_runner: test runner
        """

        for _ in range(iter_count):
            next(test_runner)


class BaseCollectDifferentUntilAllRoundTest(BaseRoundTestClass):
    """Tests for rounds derived from CollectDifferentUntilAllRound."""

    def _test_round(
        self,
        test_round: CollectDifferentUntilAllRound,
        round_payloads: List[BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
    ) -> Generator:
        """Test round."""

        first_payload = round_payloads.pop(0)
        test_round.process_payload(first_payload)
        yield test_round
        assert test_round.collection == {
            first_payload.sender,
        }
        assert test_round.end_block() is None

        for payload in round_payloads:
            test_round.process_payload(payload)
        yield test_round
        assert test_round.collection_threshold_reached

        actual_next_state = cast(
            self._period_state_class,  # type: ignore
            state_update_fn(self.period_state, test_round),
        )

        res = test_round.end_block()
        yield res
        if exit_event is None:
            assert res is exit_event
        else:
            assert res is not None
            state, event = res
            state = cast(self._period_state_class, state)  # type: ignore
            for state_attr_getter in state_attr_checks:
                assert state_attr_getter(state) == state_attr_getter(actual_next_state)
            assert event == exit_event
        yield


class BaseCollectSameUntilThresholdRoundTest(BaseRoundTestClass):
    """Tests for rounds derived from CollectSameUntilThresholdRound."""

    def _test_round(
        self,
        test_round: CollectSameUntilThresholdRound,
        round_payloads: Mapping[str, BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        most_voted_payload: Any,
        exit_event: Any,
    ) -> Generator:
        """Test rounds derived from CollectionRound."""

        (_, first_payload), *payloads = round_payloads.items()

        test_round.process_payload(first_payload)
        yield test_round
        assert test_round.collection[first_payload.sender] == first_payload
        assert not test_round.threshold_reached
        assert test_round.end_block() is None

        self._test_no_majority_event(test_round)
        with pytest.raises(ABCIAppInternalError, match="not enough votes"):
            _ = test_round.most_voted_payload

        for _, payload in payloads:
            test_round.process_payload(payload)
        yield test_round
        assert test_round.threshold_reached
        assert test_round.most_voted_payload == most_voted_payload

        actual_next_state = cast(
            self._period_state_class,  # type: ignore
            state_update_fn(self.period_state, test_round),
        )
        res = test_round.end_block()
        yield res
        assert res is not None

        state, event = res
        state = cast(self._period_state_class, state)  # type: ignore

        for state_attr_getter in state_attr_checks:
            assert state_attr_getter(state) == state_attr_getter(actual_next_state)
        assert event == exit_event
        yield


class BaseOnlyKeeperSendsRoundTest(BaseRoundTestClass):
    """Tests for rounds derived from OnlyKeeperSendsRound."""

    def _test_round(
        self,
        test_round: OnlyKeeperSendsRound,
        keeper_payloads: BaseTxPayload,
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
    ) -> Generator:
        """Test for rounds derived from OnlyKeeperSendsRound."""

        assert test_round.end_block() is None
        assert not test_round.has_keeper_sent_payload

        test_round.process_payload(keeper_payloads)
        yield test_round
        assert test_round.has_keeper_sent_payload

        yield test_round
        actual_next_state = cast(
            self._period_state_class,  # type: ignore
            state_update_fn(self.period_state, test_round),  # type: ignore
        )
        res = test_round.end_block()
        yield res
        assert res is not None

        state, event = res
        state = cast(self._period_state_class, state)  # type: ignore
        for state_attr_getter in state_attr_checks:
            assert state_attr_getter(state) == state_attr_getter(actual_next_state)
        assert event == exit_event
        yield


class BaseVotingRoundTest(BaseRoundTestClass):
    """Tests for rounds derived from VotingRound."""

    def _test_round(
        self,
        test_round: VotingRound,
        round_payloads: Mapping[str, BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
        threshold_check: Callable,
    ) -> Generator:
        """Test for rounds derived from VotingRound."""

        (sender, first_payload), *payloads = round_payloads.items()

        test_round.process_payload(first_payload)
        yield test_round
        assert not threshold_check(test_round)  # negative_vote_threshold_reached
        assert test_round.end_block() is None
        self._test_no_majority_event(test_round)

        for _, payload in payloads:
            test_round.process_payload(payload)
        yield test_round
        assert threshold_check(test_round)

        actual_next_state = cast(
            self._period_state_class,  # type: ignore
            state_update_fn(self.period_state, test_round),  # type: ignore
        )
        res = test_round.end_block()
        yield res
        assert res is not None

        state, event = res
        state = cast(self._period_state_class, state)  # type: ignore
        for state_attr_getter in state_attr_checks:
            assert state_attr_getter(state) == state_attr_getter(actual_next_state)
        assert event == exit_event
        yield

    def _test_voting_round_positive(
        self,
        test_round: VotingRound,
        round_payloads: Mapping[str, BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
    ) -> Generator:
        """Test for rounds derived from VotingRound."""

        return self._test_round(
            test_round,
            round_payloads,
            state_update_fn,
            state_attr_checks,
            exit_event,
            threshold_check=lambda x: x.positive_vote_threshold_reached,
        )

    def _test_voting_round_negative(
        self,
        test_round: VotingRound,
        round_payloads: Mapping[str, BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
    ) -> Generator:
        """Test for rounds derived from VotingRound."""

        return self._test_round(
            test_round,
            round_payloads,
            state_update_fn,
            state_attr_checks,
            exit_event,
            threshold_check=lambda x: x.negative_vote_threshold_reached,
        )

    def _test_voting_round_none(
        self,
        test_round: VotingRound,
        round_payloads: Mapping[str, BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
    ) -> Generator:
        """Test for rounds derived from VotingRound."""

        return self._test_round(
            test_round,
            round_payloads,
            state_update_fn,
            state_attr_checks,
            exit_event,
            threshold_check=lambda x: x.none_vote_threshold_reached,
        )


class BaseCollectDifferentUntilThresholdRoundTest(BaseRoundTestClass):
    """Tests for rounds derived from CollectDifferentUntilThresholdRound."""

    def _test_round(
        self,
        test_round: CollectDifferentUntilThresholdRound,
        round_payloads: Mapping[str, BaseTxPayload],
        state_update_fn: Callable,
        state_attr_checks: List[Callable],
        exit_event: Any,
    ) -> Generator:
        """Test for rounds derived from CollectDifferentUntilThresholdRound."""

        (_, first_payload), *payloads = round_payloads.items()

        test_round.process_payload(first_payload)
        yield test_round
        assert not test_round.collection_threshold_reached
        assert test_round.end_block() is None

        for _, payload in payloads:
            test_round.process_payload(payload)
        yield test_round
        assert test_round.collection_threshold_reached

        actual_next_state = cast(
            self._period_state_class,  # type: ignore
            state_update_fn(self.period_state, test_round),  # type: ignore
        )
        res = test_round.end_block()
        yield res
        assert res is not None

        state, event = res
        state = cast(self._period_state_class, state)  # type: ignore

        for state_attr_getter in state_attr_checks:
            assert state_attr_getter(state) == state_attr_getter(actual_next_state)
        assert event == exit_event
        yield

class _BaseRoundTestClass(BaseRoundTestClass):
    """Base test class."""

    period_state: BasePeriodState
    participants: FrozenSet[str]
    consensus_params: ConsensusParams
    tx_payloads: List[DummyTxPayload]

    _period_state_class = DummyPeriodState

    @classmethod
    def setup(
        cls,
    ) -> None:
        """Setup test class."""

        super().setup()
        cls.tx_payloads = get_dummy_tx_payloads(cls.participants)


class TestCollectionRound(_BaseRoundTestClass):
    """Test class for CollectionRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        test_round = DummyCollectionRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *_ = self.tx_payloads
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload

        with pytest.raises(
            ABCIAppInternalError,
            match="internal error: sender agent_0 has already sent value for round: round_id",
        ):
            test_round.process_payload(first_payload)

        with pytest.raises(
            ABCIAppInternalError,
            match=re.escape(
                "internal error: sender not in list of participants: ['agent_0', 'agent_1', 'agent_2', 'agent_3']"
            ),
        ):
            test_round.process_payload(DummyTxPayload("sender", "value"))

        with pytest.raises(
            TransactionNotValidError,
            match="sender agent_0 has already sent value for round: round_id",
        ):
            test_round.check_payload(first_payload)

        with pytest.raises(
            TransactionNotValidError,
            match=re.escape(
                "sender not in list of participants: ['agent_0', 'agent_1', 'agent_2', 'agent_3']"
            ),
        ):
            test_round.check_payload(DummyTxPayload("sender", "value"))


class TestCollectDifferentUntilAllRound(_BaseRoundTestClass):
    """Test class for CollectDifferentUntilAllRound."""

    def test_run(
        self,
    ) -> None:
        """Run Tests."""

        test_round = DummyCollectDifferentUntilAllRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = self.tx_payloads
        test_round.process_payload(first_payload)
        assert test_round.collection == {
            first_payload.value,
        }
        assert not test_round.collection_threshold_reached

        with pytest.raises(
            ABCIAppInternalError,
            match="internal error: payload attribute value with value agent_0 has already been added for round: round_id",
        ):
            test_round.process_payload(first_payload)

        with pytest.raises(
            TransactionNotValidError,
            match="payload attribute value with value agent_0 has already been added for round: round_id",
        ):
            test_round.check_payload(first_payload)

        for payload in payloads:
            test_round.process_payload(payload)


class TestCollectSameUntilThresholdRound(_BaseRoundTestClass):
    """Test CollectSameUntilThresholdRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        test_round = DummyCollectSameUntilThresholdRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = get_dummy_tx_payloads(
            self.participants, value="vote"
        )
        test_round.process_payload(first_payload)

        assert not test_round.threshold_reached
        with pytest.raises(ABCIAppInternalError, match="not enough votes"):
            _ = test_round.most_voted_payload

        for payload in payloads:
            test_round.process_payload(payload)

        assert test_round.threshold_reached
        assert test_round.most_voted_payload == "vote"

    def test_run_with_none(
        self,
    ) -> None:
        """Run tests."""

        test_round = DummyCollectSameUntilThresholdRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = get_dummy_tx_payloads(
            self.participants,
            value=None,
            is_value_none=True,
        )
        test_round.process_payload(first_payload)

        assert not test_round.threshold_reached
        with pytest.raises(ABCIAppInternalError, match="not enough votes"):
            _ = test_round.most_voted_payload

        for payload in payloads:
            test_round.process_payload(payload)

        assert test_round.threshold_reached
        assert test_round.most_voted_payload is None


class TestOnlyKeeperSendsRound(_BaseRoundTestClass):
    """Test OnlyKeeperSendsRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        test_round = DummyOnlyKeeperSendsRound(
            state=self.period_state.update(most_voted_keeper_address="agent_0"),
            consensus_params=self.consensus_params,
        )

        assert not test_round.has_keeper_sent_payload
        first_payload, *_ = self.tx_payloads
        test_round.process_payload(first_payload)

        with pytest.raises(
            ABCIAppInternalError,
            match="internal error: keeper already set the payload.",
        ):
            test_round.process_payload(first_payload)

        with pytest.raises(
            ABCIAppInternalError,
            match=re.escape(
                "internal error: sender not in list of participants: ['agent_0', 'agent_1', 'agent_2', 'agent_3']"
            ),
        ):
            test_round.process_payload(DummyTxPayload(sender="sender", value="sender"))

        with pytest.raises(
            ABCIAppInternalError, match="internal error: agent_1 not elected as keeper."
        ):
            test_round.process_payload(DummyTxPayload(sender="agent_1", value="sender"))

        with pytest.raises(
            TransactionNotValidError, match="keeper payload value already set."
        ):
            test_round.check_payload(first_payload)

        with pytest.raises(
            TransactionNotValidError,
            match=re.escape(
                "sender not in list of participants: ['agent_0', 'agent_1', 'agent_2', 'agent_3']"
            ),
        ):
            test_round.check_payload(DummyTxPayload(sender="sender", value="sender"))

        with pytest.raises(
            TransactionNotValidError, match="agent_1 not elected as keeper."
        ):
            test_round.check_payload(DummyTxPayload(sender="agent_1", value="sender"))


class TestVotingRound(_BaseRoundTestClass):
    """Test VotingRound."""

    def test_negative_threshold(
        self,
    ) -> None:
        """Runs test."""

        test_round = DummyVotingRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = get_dummy_tx_payloads(self.participants, vote=False)
        test_round.process_payload(first_payload)

        assert not test_round.negative_vote_threshold_reached
        for payload in payloads:
            test_round.process_payload(payload)

        assert test_round.negative_vote_threshold_reached

    def test_positive_threshold(
        self,
    ) -> None:
        """Runs test."""

        test_round = DummyVotingRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = get_dummy_tx_payloads(self.participants, vote=True)
        test_round.process_payload(first_payload)

        assert not test_round.positive_vote_threshold_reached
        for payload in payloads:
            test_round.process_payload(payload)

        assert test_round.positive_vote_threshold_reached


class TestCollectDifferentUntilThresholdRound(_BaseRoundTestClass):
    """Test CollectDifferentUntilThresholdRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        test_round = DummyCollectDifferentUntilThresholdRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = get_dummy_tx_payloads(self.participants, vote=False)
        test_round.process_payload(first_payload)

        assert not test_round.collection_threshold_reached
        for payload in payloads:
            test_round.process_payload(payload)

        assert test_round.collection_threshold_reached
