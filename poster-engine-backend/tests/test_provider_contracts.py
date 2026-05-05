from packages.provider_adapters.adobe import AdobeMockAdapter
from packages.provider_adapters.canva import CanvaMockAdapter


def test_adobe_mock_contract():
    adapter = AdobeMockAdapter()
    result = adapter.generate_visual("ultra premium lipstick poster")
    assert result["provider"] == "adobe_mock"
    assert result["adobe_asset_id"].startswith("adobe_mock_")
    assert result["image_url"].startswith("mock://adobe/")
    assert result["metadata"]["mode"] == "mock"


def test_canva_mock_contract():
    adapter = CanvaMockAdapter()
    result = adapter.create_layout({"prompt": "poster", "brand": "Demo", "offer": "Inbox"})
    assert result["provider"] == "canva_mock"
    assert result["canva_design_id"].startswith("canva_mock_")
    assert result["export_url"].startswith("mock://canva/")
    assert result["metadata"]["mode"] == "mock"
