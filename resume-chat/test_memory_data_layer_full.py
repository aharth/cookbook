import pytest
from memory import InMemoryDataLayer
from chainlit.user import User
from chainlit.types import Feedback, Pagination, ThreadFilter


@pytest.fixture
def data_layer():
    return InMemoryDataLayer()


@pytest.mark.asyncio
async def test_get_user(data_layer):
    user = User(identifier="user123", metadata={"role": "tester"})
    await data_layer.create_user(user)
    result = await data_layer.get_user("user123")
    assert result is not None
    assert result.identifier == "user123"


@pytest.mark.asyncio
async def test_get_user_not_found(data_layer):
    result = await data_layer.get_user("missing_user")
    assert result is None


@pytest.mark.asyncio
async def test_create_user_id_none(data_layer):
    user = User(identifier="", metadata={"note": "no ID"})
    result = await data_layer.create_user(user)
    assert result is not None
    assert result.identifier == ""


@pytest.mark.asyncio
async def test_create_user_update_existing(data_layer):
    user = User(identifier="user1", metadata={"a": 1})
    await data_layer.create_user(user)
    updated_user = await data_layer.create_user(user)
    assert updated_user.identifier == "user1"
    assert updated_user.metadata["a"] == 1


@pytest.mark.asyncio
async def test_update_thread(data_layer):
    await data_layer.update_thread("t1", name="Test Thread", user_id="user1")
    assert data_layer.threads["t1"]["name"] == "Test Thread"


@pytest.mark.asyncio
async def test_get_thread_author(data_layer):
    await data_layer.update_thread("t1", name="Thread", user_id="userX")
    author = await data_layer.get_thread_author("t1")
    assert author == "userX"


@pytest.mark.asyncio
async def test_get_thread(data_layer):
    await data_layer.update_thread("t1", name="Thread", user_id="u1")
    thread = await data_layer.get_thread("t1")
    assert thread["id"] == "t1"
    assert thread["steps"] == []


@pytest.mark.asyncio
async def test_get_thread_non_existing(data_layer):
    thread = await data_layer.get_thread("ghost")
    assert thread is None


@pytest.mark.asyncio
async def test_delete_thread(data_layer):
    await data_layer.update_thread("t1")
    deleted = await data_layer.delete_thread("t1")
    assert deleted is True
    assert "t1" not in data_layer.threads


@pytest.mark.asyncio
async def test_list_threads(data_layer):
    await data_layer.update_thread("t1", name="A", user_id="u1")
    await data_layer.update_thread("t2", name="B", user_id="u1")
    result = await data_layer.list_threads(Pagination(first=10), ThreadFilter(userId="u1"))
    assert len(result.data) == 2


@pytest.mark.asyncio
async def test_create_element(data_layer):
    el = {"id": "e1", "threadId": "t1", "type": "text", "name": "test"}
    await data_layer.create_element(el)
    assert data_layer.elements["e1"]["name"] == "test"


@pytest.mark.asyncio
async def test_get_element(data_layer):
    el = {"id": "e2", "threadId": "t1", "type": "text", "name": "test"}
    await data_layer.create_element(el)
    result = await data_layer.get_element("t1", "e2")
    assert result["id"] == "e2"


@pytest.mark.asyncio
async def test_delete_element(data_layer):
    el = {"id": "e3", "threadId": "t1", "type": "text"}
    await data_layer.create_element(el)
    deleted = await data_layer.delete_element("e3")
    assert deleted is True


@pytest.mark.asyncio
async def test_create_step(data_layer):
    step = {"id": "s1", "threadId": "t1", "input": "hi"}
    await data_layer.create_step(step)
    assert "s1" in data_layer.steps


@pytest.mark.asyncio
async def test_update_step(data_layer):
    step = {"id": "s2", "threadId": "t1", "input": "hello"}
    await data_layer.create_step(step)
    step["output"] = "world"
    await data_layer.update_step(step)
    assert data_layer.steps["s2"]["output"] == "world"


@pytest.mark.asyncio
async def test_delete_step(data_layer):
    step = {"id": "s3", "threadId": "t1", "input": "bye"}
    await data_layer.create_step(step)
    deleted = await data_layer.delete_step("s3")
    assert deleted is True


@pytest.mark.asyncio
async def test_upsert_feedback_create(data_layer):
    feedback = Feedback(threadId="t1", forId="s1", value=1)
    fid = await data_layer.upsert_feedback(feedback)
    assert fid in data_layer.feedbacks


@pytest.mark.asyncio
async def test_upsert_feedback_update(data_layer):
    fb = Feedback(threadId="t1", forId="s1", value=0)
    fid = await data_layer.upsert_feedback(fb)
    fb.value = 1
    updated_id = await data_layer.upsert_feedback(fb)
    assert data_layer.feedbacks[updated_id].value == 1


@pytest.mark.asyncio
async def test_delete_feedback(data_layer):
    fb = Feedback(threadId="t1", forId="s1", value=1)
    fid = await data_layer.upsert_feedback(fb)
    await data_layer.delete_feedback(fid)
    assert fid not in data_layer.feedbacks


@pytest.mark.asyncio
async def test_delete_feedback_empty_id(data_layer):
    result = await data_layer.delete_feedback("ghost")
    assert result is None


@pytest.mark.asyncio
async def test_build_debug_url(data_layer):
    result = await data_layer.build_debug_url("any")
    assert result == ""
