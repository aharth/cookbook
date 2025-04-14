
import pytest
from datetime import datetime
from memory import InMemoryDataLayer, now_iso
from chainlit.user import User
from chainlit.types import Feedback


@pytest.fixture
def data_layer():
    return InMemoryDataLayer()


@pytest.mark.asyncio
async def test_user_thread_relationship(data_layer):
    user = User(identifier="alice", metadata={"role": "admin"})
    await data_layer.create_user(user)

    await data_layer.update_thread("t42", user_id="alice")
    author_id = await data_layer.get_thread_author("t42")
    assert author_id == "alice"


@pytest.mark.asyncio
async def test_delete_nonexistent_thread(data_layer):
    deleted = await data_layer.delete_thread("ghost_thread")
    assert deleted is False


@pytest.mark.asyncio
async def test_create_and_get_element_integration(data_layer):
    element = {
        "id": "el123",
        "threadId": "t1",
        "type": "text",
        "name": "note.txt",
        "mime": "text/plain"
    }
    await data_layer.create_element(element)
    fetched = await data_layer.get_element("t1", "el123")
    assert fetched["id"] == "el123"
    assert fetched["mime"] == "text/plain"
