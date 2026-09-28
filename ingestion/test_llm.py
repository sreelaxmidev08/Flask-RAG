from flask_rag_production.services.llm import OllamaLLM


llm = OllamaLLM()

prompt = "What is Flask? Answer in one short sentence."

answer = llm.generate(prompt)

print("\nLLM RESPONSE\n")
print(answer)