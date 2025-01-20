from typing import List
from .agent import Agent, AgentParam
from .agent import AgentTextParam, AgentSelectParam, AgentUrlParam, AgentApiKeyParam


class SystemGenerationAgent(Agent):

    params = [
        AgentTextParam(
            name="system_prompt", description="The system prompt to use", required=True
        ),
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
