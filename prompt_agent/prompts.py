OPTIMIZE_PROMPT = """\
For the given prompt:
{prompt}

{prompt_templates}

Your task is to refine and optimize the prompt for better suitability when interacting with the LLM.

1. If the prompt is already clear, leave it unchanged.
2. Place your optimized version within <prompt> </prompt>.
3. The language of your output should match the original prompt.
4. Your focus is solely on optimizing the prompt, not providing a response to it.
"""


RAG_REFER_PROMPT = (
    "Here’s a similar, well-constructed prompt template you can use as a reference:\n"
)
