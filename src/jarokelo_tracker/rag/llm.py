from levisllmhub.chatgpt import chatgpt as chatgpt_client

def answer_with_llm(prompt, answering_llm, headless):
    if answering_llm.lower() == "chatgpt":
        return chatgpt_client.ask_chatgpt(prompt=prompt, headless=headless)
    else:
        raise ValueError(f"Unknown LLM: {answering_llm}")