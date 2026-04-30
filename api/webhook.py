from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def healt():
    return {"status":"ok"}