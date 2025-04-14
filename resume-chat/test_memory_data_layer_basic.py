import pytest
import asyncio
from memory import InMemoryDataLayer
from chainlit.user import User
from chainlit.types import Feedback, ThreadFilter, Pagination
from chainlit.element import ElementDict
from chainlit.step import StepDict

@pytest.fixture
def data_layer():
    return InMemoryDataLayer()

@pytest.mark.asyncio
async def test_create_and_get_user(data_layer):
    user = User(identifier="user1", metadata={"role": "tester"})
    created_user = await data_layer.create_user(user)
    assert created_user.id == "user1"

    fetched_user = await data_layer.get_user("user1")
    assert fetched_user is not None
    assert fetched_user.metadata["role"] == "tester"

@pytest.mark.asyncio
async def test_upsert_and_delete_feedback(data_layer):
    feedback = Feedback(threadId="t1", forId="s1", value=1)
    feedback_id = await data_layer.upsert_feedback(feedback)
    assert feedback_id == "THREAD#t1::STEP#s1"
    assert data_layer.feedbacks[feedback_id].value == 1

    await data_layer.delete_feedback(feedback_id)
    assert feedback_id not in data_layer.feedbacks

@pytest.mark.asyncio
async def test_create_and_get_element(data_layer):
    element = ElementDict(id="e1", threadId="t1", type="text", name="Example", display="inline")
    await data_layer.create_element(element)
    retrieved = await data_layer.get_element("t1", "e1")
    assert retrieved["name"] == "Example"

@pytest.mark.asyncio
async def test_create_and_update_step(data_layer):
    step = StepDict(id="s1", threadId="t1", input="Hello", output="World")
    await data_layer.create_step(step)
    assert "s1" in data_layer.steps

    step["output"] = "Updated"
    await data_layer.update_step(step)
    assert data_layer.steps["s1"]["output"] == "Updated"

@pytest.mark.asyncio
async def test_create_and_get_thread(data_layer):
    await data_layer.update_thread(thread_id="t1", name="My Thread", user_id="user1")
    thread = await data_layer.get_thread("t1")
    assert thread["name"] == "My Thread"
    assert thread["userId"] == "user1"

@pytest.mark.asyncio
async def test_list_threads_with_filters(data_layer):
    await data_layer.update_thread("t1", name="Test 1", user_id="u1")
    await data_layer.update_thread("t2", name="Feedback", user_id="u1")

    fb = Feedback(threadId="t2", forId="s1", value=1)
    await data_layer.upsert_feedback(fb)

    filters = ThreadFilter(userId="u1", feedback=1)
    result = await data_layer.list_threads(pagination=None, filters=filters)
    assert len(result.data) == 1
    assert result.data[0]["id"] == "t2"
