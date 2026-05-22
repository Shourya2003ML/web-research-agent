from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.api.routes import router
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title = "Web Search Agent", version = "1.0.0")

#Allowing frontend to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],
    allow_methods = ["*"],
    allow_headers = ["*"],
)

app.include_router(router, prefix = "/api/v1")

if __name__ == "__main__":
    import uvicorn 
    uvicorn.run("app.main:app", host = "0.0.0.0", port = 8000, reload = True)