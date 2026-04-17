from app.providers.veo.adapter import VeoAdapter


def test_veo_callback_normalization():
    adapter = VeoAdapter()
    event = adapter.normalize_callback(
        headers={},
        payload={
            "name": "operations/abc",
            "done": True,
            "response": {
                "generateVideoResponse": {
                    "generatedSamples": [{"video": {"uri": "https://cdn.example.com/veo.mp4"}}]
                }
            },
        },
    )
    assert event.provider == "veo"
    assert event.state == "succeeded"
    assert event.provider_operation_name == "operations/abc"
