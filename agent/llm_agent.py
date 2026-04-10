from openai import OpenAI
import os

from .prompts import SYSTEM_PROMPT
from .parser import parse_action


class LLMAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ["API_BASE_URL"],
            api_key=os.environ["API_KEY"],
        )
        self.model = os.getenv("MODEL_NAME", "gpt-4o-mini")

    def act(self, observation):
        prompt = f"""
Logs: {observation['logs']}
Metrics: {observation['metrics']}
Alerts: {observation['alerts']}
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=50,
            )

            text = response.choices[0].message.content
            return parse_action(text)

        except Exception:
            return {"action_type": "noop", "target": None}