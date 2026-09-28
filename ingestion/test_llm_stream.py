from flask_rag_production.services.llm import OllamaLLM


llm = OllamaLLM()

prompt = "What is Flask? Answer in two short sentences."

print("\nLLM STREAM\n")

for chunk in llm.generate_stream(prompt):
    print(chunk, end="", flush=True)

print("\n")