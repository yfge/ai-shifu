from typing import List
from .agent import AgentParam, AgentUrlParam, AgentApiKeyParam, AgentSelectParam
from .llmagent import LLMAgent


class ErnieAgent(LLMAgent):
    params = [
        AgentSelectParam(name="model", description="The model to use", required=True),
        AgentUrlParam(
            name="base_url", description="The base url to use", required=True
        ),
        AgentApiKeyParam(
            name="api_key", description="The API key to use", required=True
        ),
    ]

    def run(self, *args, **kwargs):
        pass

    def get_params(self) -> List[AgentParam]:
        pass
