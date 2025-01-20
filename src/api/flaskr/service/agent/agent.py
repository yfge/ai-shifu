from abc import ABC, abstractmethod
from typing import List


class AgentParam:
    name: str
    type: str
    description: str
    required: bool


class AgentUrlParam(AgentParam):
    type = "url"


class AgentTextParam(AgentParam):
    type = "text"


class AgentSelectParam(AgentParam):
    type = "select"


class AgentApiKeyParam(AgentParam):
    type = "api_key"


class Agent(ABC):
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
