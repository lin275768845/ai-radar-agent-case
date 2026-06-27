import logging

from ai_radar_agent.utils import setup_logging


def test_setup_logging_verbose_keeps_third_party_sdks_quiet():
    setup_logging(verbose=True)

    for name in ("openai", "openai._base_client", "httpx", "httpcore", "urllib3"):
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING

    assert logging.getLogger("ai_radar_agent").getEffectiveLevel() == logging.DEBUG
