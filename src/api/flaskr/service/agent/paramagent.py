from typing import List
from .agent import Agent, AgentParam


class ParamAgent(Agent):
    def run(self, *args, **kwargs):
        pass

    def get_params(self) -> List[AgentParam]:
        pass
