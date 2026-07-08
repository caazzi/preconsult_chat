from reflex_app.preconsult.i18n import translations


def test_i18n_fallback_to_en_when_lang_unknown():
    t = translations.get("xx", translations["en"])
    assert t["title"] == "PreConsult"
    assert t["start_btn"] == "Continue"


def test_i18n_all_pt_keys_have_corresponding_en():
    for key in translations["pt"]:
        assert key in translations["en"], f"Chave '{key}' existe em PT mas falta em EN"


def test_i18n_missing_pt_key_falls_back():
    fake_dict = {"en": {"hello": "Hello"}}
    result = fake_dict.get("pt", fake_dict["en"])
    assert result["hello"] == "Hello"


def test_i18n_gender_opts_includes_prefer_not():
    assert "Prefer not to say" in translations["en"]["gender_opts"]
    assert "Prefiro não informar" in translations["pt"]["gender_opts"]


def test_get_localized_value_unknown_category_returns_key():
    from reflex_app.preconsult.state import State
    state = State()
    state.lang = "en"
    result = state.get_localized_value("nonexistent", "some_key")
    assert result == "some_key"


def test_get_localized_value_empty_key_returns_empty():
    from reflex_app.preconsult.state import State
    state = State()
    result = state.get_localized_value("duration", "")
    assert result == ""
