from typing import List
from abc import abstractmethod
from .agent import Agent, AgentParam


class LLMAgent(Agent):
    @abstractmethod
    def run(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_params(self) -> List[AgentParam]:
        pass

    @abstractmethod
    def get_type(self) -> str:
        pass

    @abstractmethod
    def save_params(self, params: List[AgentParam]):
        pass
