"""Claude Haiku 5.5 IVR intent router."""
from ._anthropic import AnthropicRouter


class ClaudeHaikuRouter(AnthropicRouter):
    model = "claude-haiku-5-5"
    PRICING = (0.10, 0.50)                    # $/MTok input, output (Anthropic price list)
    THINKING = {"type": "disabled"}           # Haiku 5.5 may disable thinking at effort <= high
