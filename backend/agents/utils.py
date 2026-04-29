from langchain_core.callbacks import dispatch_custom_event
from langchain_core.callbacks import adispatch_custom_event


def stream_custom_event(
    event_name: str,
    step: str,
    message: str,
    **kwargs,
):
    dispatch_custom_event(
        name=event_name,
        data={
            "step": step,
            "message": message,
            **kwargs,
        },
    )

async def astream_custom_event(
    event_name: str,
    step: str,
    message: str,
    **kwargs,
):
    await adispatch_custom_event(
        name=event_name,
        data={
            "step": step,
            "message": message,
            **kwargs,
        },
    )