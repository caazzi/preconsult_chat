"""
Security regression tests.

Run with:
    python -m pytest tests/test_security.py -v
"""
import os
import re
import importlib


# ---------------------------------------------------------------------------
# P1: Hardcoded IP must not appear in config
# ---------------------------------------------------------------------------
class TestP1_NoHardcodedIP:
    def test_config_source_has_no_hardcoded_ip(self):
        """The config module source must not contain the old public IP."""
        import preconsult.core.config as cfg
        src_path = cfg.__file__
        with open(src_path) as f:
            source = f.read()
        assert "34.151.247.35" not in source, "Hardcoded IP still present in config.py"


# ---------------------------------------------------------------------------
# P2: API key must be enforced (ValueError when unset)
# ---------------------------------------------------------------------------
class TestP2_APIKeyEnforced:
    def test_config_raises_without_api_key(self):
        """Importing config with no PRECONSULT_API_KEY must raise ValueError."""
        import dotenv
        original_load_dotenv = dotenv.load_dotenv
        dotenv.load_dotenv = lambda *args, **kwargs: None
        saved = os.environ.pop("PRECONSULT_API_KEY", None)
        try:
            import preconsult.core.config as cfg
            try:
                importlib.reload(cfg)
                assert False, "Expected ValueError was not raised"
            except ValueError as exc:
                assert "PRECONSULT_API_KEY" in str(exc)
        finally:
            dotenv.load_dotenv = original_load_dotenv
            if saved is not None:
                os.environ["PRECONSULT_API_KEY"] = saved


# ---------------------------------------------------------------------------
# P4: Reflex frontend must not have a hardcoded default API key
# ---------------------------------------------------------------------------
class TestP4_NoDefaultKeyInReflexFrontend:
    def test_reflex_state_has_no_default_key(self):
        """reflex_app/preconsult/state.py must not contain a hardcoded default API key."""
        state_path = os.path.join(
            os.path.dirname(__file__), "..", "reflex_app", "preconsult", "state.py"
        )
        with open(state_path) as f:
            source = f.read()
        assert "dev_key_123" not in source, (
            "Insecure default API key still present in reflex_app/preconsult/state.py"
        )


# ---------------------------------------------------------------------------
# P5: Endpoints must not leak exception text to clients
# ---------------------------------------------------------------------------
class TestP5_ErrorResponsesSanitized:
    def test_endpoints_no_fstring_in_detail(self):
        """HTTPException detail args must not contain f-string {e} patterns."""
        endpoints_path = os.path.join(
            os.path.dirname(__file__),
            "..", "src", "preconsult", "api", "endpoints.py",
        )
        with open(endpoints_path) as f:
            source = f.read()
        # Match patterns like detail=f"...{e}" but NOT detail=str(e) (which is fine)
        leaky = re.findall(r'detail=f["\'].*\{e\}', source)
        assert leaky == [], (
            f"Found error details leaking exception text: {leaky}"
        )

# ---------------------------------------------------------------------------
# P6: Auto destruction notices & Emergency rules
# ---------------------------------------------------------------------------
class TestP6_Sprint5Features:
    def test_auto_destruction_notice_en(self):
        from reflex_app.preconsult.i18n import translations
        assert "deleted" in translations["en"]["complete_desc"].lower()

    def test_auto_destruction_notice_pt(self):
        from reflex_app.preconsult.i18n import translations
        assert "apagados" in translations["pt"]["complete_desc"].lower()

    def test_emergency_rule_in_interview_prompt(self):
        from preconsult.services.agent_service import get_interview_chain
        chain = get_interview_chain()
        prompt = chain.steps[0]
        system_msg = str(prompt.messages[0])
        assert "emergency" in system_msg.lower()
        assert "do not generate questions" in system_msg.lower()


class TestP7_InputSanitization:
    def test_sanitize_escapes_html(self):
        from preconsult.api.endpoints import _sanitize_input
        assert _sanitize_input("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"

    def test_sanitize_strips_whitespace(self):
        from preconsult.api.endpoints import _sanitize_input
        assert _sanitize_input("  hello  ") == "hello"

    def test_sanitize_returns_empty_for_non_string(self):
        from preconsult.api.endpoints import _sanitize_input
        assert _sanitize_input(None) == ""
        assert _sanitize_input(123) == ""


class TestP8_BuildMode:
    def test_build_mode_allows_startup_without_api_key(self):
        import dotenv
        original_load_dotenv = dotenv.load_dotenv
        dotenv.load_dotenv = lambda *args, **kwargs: None
        saved_key = os.environ.pop("PRECONSULT_API_KEY", None)
        saved_build = os.environ.get("BUILD_MODE")
        os.environ["BUILD_MODE"] = "true"
        try:
            import preconsult.core.config as cfg
            import importlib
            importlib.reload(cfg)
            assert cfg.PRECONSULT_API_KEY is None
        finally:
            dotenv.load_dotenv = original_load_dotenv
            if saved_key is not None:
                os.environ["PRECONSULT_API_KEY"] = saved_key
            if saved_build:
                os.environ["BUILD_MODE"] = saved_build
            else:
                os.environ.pop("BUILD_MODE", None)
