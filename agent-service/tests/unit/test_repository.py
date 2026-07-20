import pytest

from app.domain.models import Conversation
from app.domain.repository import ConversationNotFoundError, InMemoryConversationRepository


@pytest.mark.asyncio
async def test_create_and_get_round_trip():
    repo = InMemoryConversationRepository()
    conversation = Conversation()
    await repo.create(conversation)

    fetched = await repo.get(conversation.id)
    assert fetched.id == conversation.id


@pytest.mark.asyncio
async def test_get_missing_conversation_raises():
    repo = InMemoryConversationRepository()
    with pytest.raises(ConversationNotFoundError):
        await repo.get("conv_does_not_exist")


@pytest.mark.asyncio
async def test_save_updates_and_touches_updated_at():
    repo = InMemoryConversationRepository()
    conversation = Conversation()
    await repo.create(conversation)
    original_updated_at = conversation.updated_at

    conversation.lead_profile.idade = 35
    await repo.save(conversation)

    fetched = await repo.get(conversation.id)
    assert fetched.lead_profile.idade == 35
    assert fetched.updated_at >= original_updated_at


def test_lock_for_returns_same_lock_for_same_conversation_id():
    repo = InMemoryConversationRepository()
    lock_a = repo.lock_for("conv_1")
    lock_b = repo.lock_for("conv_1")
    lock_c = repo.lock_for("conv_2")
    assert lock_a is lock_b
    assert lock_a is not lock_c
