from langchain_core.runnables import Runnable
from loguru import logger
from backend.agents.general_agent.state import GeneralAgentState

class StreamNode(Runnable):
    def __init__(self) -> None:
        """
        Initialize the StreamNode.
        """
        super().__init__()

    def invoke(self, state: GeneralAgentState, **kwargs):
        pass

    async def ainvoke(self, state: GeneralAgentState, **kwargs):
        # StreamNode in our graph mainly acts as an endpoint to finalize state
        # Or format the output if required. 
        # Here we just pass the output through.
        logger.info("StreamNode reached - finalizing response.")
        
        # We might have output from direct response or websearch agent
        # Just returning an empty dict if the state update is already handled 
        # by previous nodes or subgraphs
        return {}
