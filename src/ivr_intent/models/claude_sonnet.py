"""Claude Sonnet 5.5 IVR intent router."""
from ._anthropic import AnthropicRouter


class ClaudeSonnetRouter(AnthropicRouter):
    model = "claude-sonnet-5-5"
    PRICING = (2.00, 10.00)                   # $/MTok input, output (Anthropic price list)
    THINKING = {"type": "between_tools"}      # Sonnet 5.5 rejects thinking "disabled"
