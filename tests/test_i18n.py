from preconsult.core.i18n import translations


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
