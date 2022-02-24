# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2022 Valory AG
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

"""Integration tests for the valory/price_estimation_abci skill."""
import pytest

from tests.fixture_helpers import UseGnosisSafeHardHatNet
from tests.test_agents.base import (
    BaseTestEnd2EndAgentCatchup,
    BaseTestEnd2EndNormalExecution,
    MAX_FLAKY_RERUNS,
)

# round check log messages of the happy path
ROUND_CHECK_STRINGS = {
    "registration_startup": 1,
    "randomness_safe": 1,
    "select_keeper_safe": 1,
    "deploy_safe": 1,
    "validate_safe": 1,
    "randomness_oracle": 1,
    "select_keeper_oracle": 1,
    "deploy_oracle": 1,
    "validate_oracle": 1,
    "estimate_consensus": 2,
    "tx_hash": 2,
    "randomness_transaction_submission": 2,
    "select_keeper_transaction_submission_a": 2,
    "collect_signature": 2,
    "finalization": 2,
    "validate_transaction": 2,
    "reset_and_pause": 2,
    "collect_observation": 3,
}

# strict check log messages of the happy path
STRICT_CHECK_STRINGS = (
    "Finalized with transaction hash",
    "Signature:",
    "Got estimate of BTC price in USD:",
    "Got observation of BTC price in USD",
    "Period end",
)


class TestABCIPriceEstimationSingleAgent(
    BaseTestEnd2EndNormalExecution,
    UseGnosisSafeHardHatNet,
):
    """Test that the ABCI price_estimation skill with only one agent."""

    NB_AGENTS = 1
    agent_package = "valory/price_estimation:0.1.0"
    skill_package = "valory/price_estimation_abci:0.1.0"
    wait_to_finish = 180
    strict_check_strings = STRICT_CHECK_STRINGS
    round_check_strings_to_n_periods = ROUND_CHECK_STRINGS


class TestABCIPriceEstimationTwoAgents(
    BaseTestEnd2EndNormalExecution,
    UseGnosisSafeHardHatNet,
):
    """Test that the ABCI price_estimation skill with two agents."""

    NB_AGENTS = 2
    agent_package = "valory/price_estimation:0.1.0"
    skill_package = "valory/price_estimation_abci:0.1.0"
    wait_to_finish = 180
    strict_check_strings = STRICT_CHECK_STRINGS
    round_check_strings_to_n_periods = ROUND_CHECK_STRINGS


class TestABCIPriceEstimationFourAgents(
    BaseTestEnd2EndNormalExecution,
    UseGnosisSafeHardHatNet,
):
    """Test that the ABCI price_estimation skill with four agents."""

    NB_AGENTS = 4
    agent_package = "valory/price_estimation:0.1.0"
    skill_package = "valory/price_estimation_abci:0.1.0"
    wait_to_finish = 180
    strict_check_strings = STRICT_CHECK_STRINGS
    round_check_strings_to_n_periods = ROUND_CHECK_STRINGS


@pytest.mark.flaky(reruns=MAX_FLAKY_RERUNS)
class TestAgentCatchup(BaseTestEnd2EndAgentCatchup, UseGnosisSafeHardHatNet):
    """Test that an agent that is launched later can synchronize with the rest of the network"""

    NB_AGENTS = 4
    agent_package = "valory/price_estimation:0.1.0"
    skill_package = "valory/price_estimation_abci:0.1.0"
    KEEPER_TIMEOUT = 10
    wait_to_finish = 180
    restart_after = 45
    round_check_strings_to_n_periods = ROUND_CHECK_STRINGS
    stop_string = "'registration_startup' round is done with event: Event.DONE"
