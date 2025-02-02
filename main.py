from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_ollama import ChatOllama

from services.chat_ollama_with_memory import ChatOllamaWithMemory

# Initialize FastAPI app
app = FastAPI()

# Initialize the ChatOllama instance
chat_with_memory = ChatOllamaWithMemory(model="deepseek-r1:8b")

# Define a Pydantic model for the request body
class UserMessage(BaseModel):
    message: str


# Create an endpoint to handle user messages
@app.post("/chat")
async def generate_poem(user_message: UserMessage):
    try:
        # Prepare the message for the model
        message = [
            ("user", user_message.message)
        ]

        # Get the AI's response
        ai_response = chat_with_memory.invoke(message)
        print(ai_response)
        # Return the response
        return {"response": ai_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)