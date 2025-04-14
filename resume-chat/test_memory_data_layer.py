import pytest
from memory import InMemoryDataLayer
from chainlit.user import User
from chainlit.types import Feedback, ThreadFilter, Pagination


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
async def test_create_and_get_thread(data_layer):
    await data_layer.update_thread("t1", name="Test Thread", user_id="user1")
    thread = await data_layer.get_thread("t1")
    assert thread["id"] == "t1"
    assert thread["name"] == "Test Thread"
    assert thread["userId"] == "user1"
    assert thread["steps"] == []
    assert thread["elements"] == []


@pytest.mark.asyncio
async def test_list_threads_with_filters(data_layer):
    await data_layer.update_thread("t1", name="Thread One", user_id="user1")
    await data_layer.update_thread("t2", name="Thread Two", user_id="user1")

    # Add feedback only to t2
    feedback = Feedback(threadId="t2", forId="s2", value=1)
    await data_layer.upsert_feedback(feedback)

    # Filter by feedback present
    threads_with_feedback = await data_layer.list_threads(
        pagination=None,
        filters=ThreadFilter(feedback=1, userId="user1")
    )
    assert len(threads_with_feedback.data) == 1
    assert threads_with_feedback.data[0]["id"] == "t2"

    # Filter by feedback missing
    threads_without_feedback = await data_layer.list_threads(
        pagination=None,
        filters=ThreadFilter(feedback=0, userId="user1")
    )
    assert len(threads_without_feedback.data) == 1
    assert threads_without_feedback.data[0]["id"] == "t1"


@pytest.mark.asyncio
async def test_create_and_update_step(data_layer):
    step = {
        "id": "s1",
        "threadId": "t1",
        "input": "Hello",
        "output": "World"
    }

    await data_layer.create_step(step)
    assert "s1" in data_layer.steps

    updated_step = {
        "id": "s1",
        "threadId": "t1",
        "output": "Universe"
    }

    await data_layer.update_step(updated_step)
    assert data_layer.steps["s1"]["output"] == "Universe"


@pytest.mark.asyncio
async def test_element_lifecycle(data_layer):
    element = {
        "id": "e1",
        "threadId": "t1",
        "type": "text",
        "name": "note"
    }

    await data_layer.create_element(element)
    assert await data_layer.get_element("t1", "e1") == element

    deleted = await data_layer.delete_element("e1")
    assert deleted is True
    assert await data_layer.get_element("t1", "e1") is None
