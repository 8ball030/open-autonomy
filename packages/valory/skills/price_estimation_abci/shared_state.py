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

from typing import Any, Dict, Optional

from aea.skills.base import Model

from packages.valory.skills.price_estimation_abci.models import Block, Blockchain, Round


class SharedState(Model):
    """Keep the current shared state."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the state."""
        super().__init__(*args, **kwargs)

        # info request received from Tendermint
        self.info_received: bool = False

        # mapping from dialogue reference nonce to handler callback name
        self.request_to_handler: Dict[str, str] = {}

        self.current_round = Round()
        self.blockchain = Blockchain()

        # set on 'begin_block', populated on 'deliver_tx', unset and saved on 'end_block'
        self.current_block: Optional[Block] = None
