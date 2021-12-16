from typing import List, Optional
import logging
import subprocess
import signal
from logging import Logger


class TendermintParams:  # pylint: disable=too-few-public-methods
    """Tendermint node parameters."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        proxy_app: str,
        #        rpc_laddr: str,
        #        p2p_laddr: str,
        #        p2p_seeds: List[str],
        consensus_create_empty_blocks: bool,
        home: Optional[str] = None,
    ):
        """
        Initialize the parameters to the Tendermint node.
        :param proxy_app: ABCI address.
        :param rpc_laddr: RPC address.
        :param p2p_laddr: P2P address.
        :param p2p_seeds: P2P seeds.
        :param consensus_create_empty_blocks: if true, Tendermint node creates empty blocks.
        :param home: Tendermint's home directory.
        """
        self.proxy_app = proxy_app
        #        self.rpc_laddr = rpc_laddr
        #        self.p2p_laddr = p2p_laddr
        #        self.p2p_seeds = p2p_seeds
        self.consensus_create_empty_blocks = consensus_create_empty_blocks
        self.home = home


class TendermintNode:
    """A class to manage a Tendermint node."""

    def __init__(self, params: TendermintParams, logger: Optional[Logger] = None):
        """
        Initialize a Tendermint node.
        :param params: the parameters.
        :param logger: the logger.
        """
        self.params = params
        self.logger = logger or logging.getLogger()

        self._process: Optional[subprocess.Popen] = None

    def _build_init_command(self) -> List[str]:
        """Build the 'init' command."""
        cmd = [
            "tendermint",
            "init",
        ]
        if self.params.home is not None:  # pragma: nocover
            cmd += ["--home", self.params.home]
        return cmd

    def _build_node_command(self) -> List[str]:
        """Build the 'node' command."""
        cmd = [
            "tendermint",
            "node",
            f"--proxy_app={self.params.proxy_app}",
            #            f"--rpc.laddr={self.params.rpc_laddr}",
            #            f"--p2p.laddr={self.params.p2p_laddr}",
            #            f"--p2p.seeds={','.join(self.params.p2p_seeds)}",
            f"--consensus.create_empty_blocks={str(self.params.consensus_create_empty_blocks).lower()}",
        ]
        if self.params.home is not None:  # pragma: nocover
            cmd += ["--home", self.params.home]
        return cmd

    def init(self) -> None:
        """Initialize Tendermint node."""
        cmd = self._build_init_command()
        subprocess.call(cmd)  # nosec

    def start(self) -> None:
        """Start a Tendermint node process."""
        if self._process is not None:  # pragma: nocover
            return
        cmd = self._build_node_command()
        self._process = subprocess.Popen(  # nosec # pylint: disable=consider-using-with
            cmd
        )

    def stop(self) -> None:
        """Stop a Tendermint node process."""
        if self._process is None:  # pragma: nocover
            return
        self._process.send_signal(signal.SIGTERM)
        self._process.wait(timeout=30)
        poll = self._process.poll()
        if poll is None:  # pragma: nocover
            self._process.terminate()
            self._process.wait(2)
        self._process = None

    def prune_blocks(self) -> None:
        """prune blocks from the Tendermint state"""
        subprocess.call(["tendermint", "unsafe_reset_all"])
