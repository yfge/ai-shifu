from .llmconfig import LLMConfig


class LLM:
    def __init__(self, config: LLMConfig):
        self.config = config

    def run(self, *args, **kwargs):
        pass

    def get_model(self):
        pass
