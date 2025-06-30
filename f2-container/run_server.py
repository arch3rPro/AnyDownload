import uvicorn

if __name__ == "__main__":
    uvicorn.run("f2-container.api_server:app", host="0.0.0.0", port=8000, reload=True)
