from app.services.tarkov_item_import_service import (
    classify_scav_case_eligibility,
    _mapped_category,
)


def test_classifies_stable_default_and_custom_weapon_presets():
    items = {
        "base": {
            "types": ["gun"],
            "properties": {"defaultPreset": "default"},
        },
        "default": {
            "types": ["preset"],
            "properties": {"default": True, "baseItem": "base"},
        },
        "custom": {
            "types": ["preset"],
            "properties": {"default": False, "baseItem": "base"},
        },
    }

    eligibility = classify_scav_case_eligibility(items)

    assert eligibility == {"base": False, "default": True, "custom": False}


def test_uses_base_weapon_when_default_id_is_generated():
    generated_id = "707265736574000000000002"
    items = {
        "x17": {
            "types": ["gun"],
            "properties": {"defaultPreset": generated_id},
        },
        generated_id: {
            "types": ["preset"],
            "properties": {"default": True, "baseItem": "x17"},
        },
    }

    eligibility = classify_scav_case_eligibility(items)

    assert eligibility["x17"] is True
    assert eligibility[generated_id] is False


def test_category_mapping_is_case_insensitive():
    assert _mapped_category("Assault Rifle") == "Guns"
    assert _mapped_category("chest-rig") == "Rigs"
    assert _mapped_category("Item") is None
