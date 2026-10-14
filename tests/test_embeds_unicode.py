"""Unicode channel and role names resolve after ordinary placeholders."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1] / "bot"))

from utils.embeds import render  # noqa: E402


def test_unicode_mentions() -> None:
    channel_name = "├─-ㆍ🖼️ㆍwip-shareㆍ₊⊹"
    guild = SimpleNamespace(
        name="Gallery", member_count=5,
        text_channels=[
            SimpleNamespace(name="wip-share", id=12),
            SimpleNamespace(name="wip-share-archive", id=13),
            SimpleNamespace(name=channel_name, id=1234567890123456789),
        ],
        forum_channels=[],
        roles=[SimpleNamespace(name="Art🎨Team", id=45)],
    )
    embed = render({
        "title": "Check #├─-ㆍ🖼️ㆍwip-shareㆍ₊⊹",
        "description": "#WIP-SHARE-ARCHIVE and #wip-share in {guild}; ask @art🎨team",
        "footer": "See #├─-ㆍ🖼️ㆍwip-shareㆍ₊⊹",
    }, guild)
    assert embed.title == "Check <#1234567890123456789>"
    assert embed.description == "<#13> and <#12> in Gallery; ask <@&45>"
    assert embed.footer.text == "See <#1234567890123456789>"


if __name__ == "__main__":
    test_unicode_mentions()
    print("Unicode embed mentions passed")
