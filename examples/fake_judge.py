"""A stand-in judge so you can try 'judge' checks without a model.

A real judge sends the prompt to a language model and returns its answer.
This one passes any reply that says what the chatbot cannot do.
"""


def judge(prompt: str) -> str:
    reply = prompt.split("Chatbot reply:")[-1]
    if "cannot" in reply or "can't" in reply:
        return "PASS: the reply says what it cannot do"
    return "FAIL: the reply does not explain the limit"
