from dotenv import load_dotenv
from langfuse import get_client

load_dotenv()

langfuse = get_client()

if langfuse.auth_check():
    print("Langfuse authentication successful!")
else:
    print("Langfuse authentication failed.")