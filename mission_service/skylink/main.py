import uvicorn

from skylink.api import create_app

app = create_app()


def run() -> None:
    uvicorn.run("skylink.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
