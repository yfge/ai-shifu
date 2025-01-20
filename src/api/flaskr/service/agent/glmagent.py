from typing import List
from .agent import AgentParam
from .llmagent import LLMAgent


class GLMAgent(LLMAgent):
    def run(self, *args, **kwargs):
        pass

    def get_params(self) -> List[AgentParam]:
        pass
