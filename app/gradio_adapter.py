"""Read-only discovery against an operator-selected, trusted Gradio runner.

Discovery is deliberately not exposed as an arbitrary-URL HTTP fetch endpoint.
Gradio stateful callbacks cannot all be inferred as safe standalone commands.
"""
from urllib.parse import urlparse


def inspect_runner(url: str, *, client_factory=None, auth=None):
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a trusted runner URL without embedded credentials")
    if client_factory is None:
        from gradio_client import Client
        client_factory = Client
    client = client_factory(url, auth=auth, verbose=False)
    spec = client.view_api(return_format="dict", print_info=False)
    return {"named_endpoints": spec.get("named_endpoints", {}),
            "execution_enabled": False,
            "note": "Named endpoint discovery only; campaign/state mapping requires explicit integration."}
