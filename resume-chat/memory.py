from typing import Optional, Dict, List
from uuid import uuid4
from datetime import datetime, timezone
import json

import logging

from chainlit.data.base import BaseDataLayer
from chainlit.types import (
    Feedback,
    PageInfo,
    Pagination,
    PaginatedResponse,
    ThreadDict,
    ThreadFilter,
)
from chainlit.user import User, PersistedUser
from chainlit.element import ElementDict
from chainlit.step import StepDict


def now_iso():
#    return datetime.utcnow().isoformat() + "Z"
#    return datetime.now(datetime.UTC).isoformat() + "Z"
    return datetime.now(timezone.utc).isoformat()

class InMemoryDataLayer(BaseDataLayer):
    def __init__(self):
        logging.info("Initialising InMemoryDataLayer...")

        self.users: Dict[str, PersistedUser] = {}
        self.threads: Dict[str, ThreadDict] = {}
        self.steps: Dict[str, StepDict] = {}
        self.elements: Dict[str, ElementDict] = {}
        self.feedbacks: Dict[str, Feedback] = {}

    async def get_user(self, identifier: str) -> Optional[PersistedUser]:
        user = self.users.get(identifier)

        logging.info(f"Returning user {user}...")

        return user

    async def create_user(self, user: User) -> Optional[PersistedUser]:
        logging.info(f"Creating user {user.identifier}...")

        # Reuse if user already exists
        existing_user = self.users.get(user.identifier)
        if existing_user:
            logging.info(f"User already exists: {existing_user}")
            return existing_user

        user_id = user.identifier  # str(uuid4())
        persisted_user = PersistedUser(
            id=user_id,
            identifier=user.identifier,
            metadata=user.metadata,
            createdAt=now_iso(),
        )

        self.users[user.identifier] = persisted_user

        return persisted_user

    async def upsert_feedback(self, feedback: Feedback) -> str:
        logging.info(f"Upserting feedback {feedback}")

        feedback.id = f"THREAD#{feedback.threadId}::STEP#{feedback.forId}"
        self.feedbacks[feedback.id] = feedback

        return feedback.id

    async def delete_feedback(self, feedback_id: str) -> None:
        logging.info(f"Deleting feedback {feedback_id}")
        self.feedbacks.pop(feedback_id, None)

    async def create_element(self, element_dict: ElementDict):
        element_id = element_dict.get("id")
        if not element_id:
            raise ValueError("Element ID is required")

        self.elements[element_id] = element_dict

    async def get_element(
        self, thread_id: str, element_id: str
    ) -> Optional[ElementDict]:
        return self.elements.get(element_id)

    async def delete_element(self, element_id: str) -> bool:
        if element_id in self.elements:
            del self.elements[element_id]
            return True

        return False

    async def create_step(self, step_dict: StepDict):
        step_id = step_dict.get("id")
        thread_id = step_dict.get("threadId")

        if not step_id or not thread_id:
            raise ValueError("Both 'id' and 'threadId' must be provided in step_dict")

        logging.info(f"Creating step: id={step_id}, threadId={thread_id}")

        # Avoid overwriting steps with same ID
        if step_id in self.steps:
            logging.warning(
                f"Step with id={step_id} already exists. Skipping re-creation."
            )
            return

        self.steps[step_id] = step_dict

    async def update_step(self, step_dict: StepDict):
        step_id = step_dict.get("id")
        thread_id = step_dict.get("threadId")

        if not step_id or not thread_id:
            raise ValueError("Both 'id' and 'threadId' must be provided in step_dict")

        logging.info(f"Updating step: {step_id} in thread: {thread_id}")

        existing_step = self.steps.get(step_id)
        if not existing_step:
            raise ValueError(f"Step with id {step_id} does not exist")

        # Merge updates into existing step (like partial update)
        existing_step.update(step_dict)

        self.steps[step_id] = existing_step

    async def delete_step(self, step_id: str) -> bool:
        if step_id in self.steps:
            del self.steps[step_id]
            return True

        return False

    async def get_thread_author(self, thread_id: str) -> Optional[str]:
        thread = self.threads.get(thread_id)

        if thread:
            user_id = thread.get("userId")
            logging.info(f"Returning user {user_id}")
            return user_id

        logging.info("Returning user None")

        return None

    async def delete_thread(self, thread_id: str) -> bool:
        if thread_id in self.threads:
            del self.threads[thread_id]
            return True

        return False

    async def update_thread(
        self,
        thread_id: str,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
    ):
        logging.info(f"Updating thread {thread_id} for user {user_id}...")

        thread = self.threads.get(thread_id)
        if not thread:
            logging.info(f"Creating a new thread with {thread_id}...")

            thread = {
                "id": thread_id,
                "name": name or "",
                "userId": user_id or "",
                "userIdentifier": user_id or "",
                "createdAt": now_iso(),
                "metadata": metadata or {},
                "tags": tags or [],
            }
        else:
            if name is not None:
                thread["name"] = name
            if user_id is not None:
                thread["userId"] = user_id
            if metadata is not None:
                thread["metadata"] = metadata
            if tags is not None:
                thread["tags"] = tags

        self.threads[thread_id] = thread

    async def list_threads(
        self, pagination: Optional[Pagination], filters: Optional[ThreadFilter]
    ) -> PaginatedResponse[ThreadDict]:
        logging.info(f"Listing {len(self.threads.values())} threads...")

        # Get all threads
        all_threads = list(self.threads.values())

        if len(all_threads) > 0:
            logging.info(f"Original thread: {json.dumps(all_threads[0])}")

        # 🧹 Apply filters
        if filters:
            # Filter by userId
            if filters.userId:
                logging.info(f"Filter by userId {filters.userId}")
                all_threads = [
                    t for t in all_threads if t.get("userId") == filters.userId
                ]

            # Filter by feedback (1 = has feedback, 0 = no feedback)
            if filters.feedback is not None:
                thread_ids_with_feedback = {
                    f.threadId for f in self.feedbacks.values() if f.threadId
                }
                if filters.feedback == 1:
                    all_threads = [
                        t
                        for t in all_threads
                        if t.get("id") in thread_ids_with_feedback
                    ]
                elif filters.feedback == 0:
                    all_threads = [
                        t
                        for t in all_threads
                        if t.get("id") not in thread_ids_with_feedback
                    ]

            # Fuzzy search (in name and tags)
            if filters.search:
                search_term = filters.search.lower()
                all_threads = [
                    t
                    for t in all_threads
                    if search_term in (t.get("name", "") or "").lower()
                    or any(search_term in tag.lower() for tag in (t.get("tags") or []))
                ]

        # 🗃️ Sort by createdAt
        all_threads.sort(key=lambda t: t.get("createdAt", ""), reverse=False)

        # 🔎 Cursor-based slicing
        if pagination and pagination.cursor:
            try:
                cursor_index = next(
                    i
                    for i, thread in enumerate(all_threads)
                    if thread.get("id") == pagination.cursor
                )
                threads = all_threads[cursor_index + 1 :]
            except StopIteration:
                threads = []
        else:
            threads = all_threads

        # 📦 Apply limit
        limit = pagination.first if pagination else len(threads)
        paginated_items = threads[:limit]

        # 🧭 Page info
        has_next_page = len(threads) > limit
        end_cursor = paginated_items[-1]["id"] if paginated_items else None

        logging.info(f"Found {len(paginated_items)} items")

        return PaginatedResponse(
            data=paginated_items,
            total=len(all_threads),
            pageInfo=PageInfo(
                hasNextPage=has_next_page,
                startCursor=paginated_items[0]["id"] if paginated_items else None,
                endCursor=end_cursor,
            ),
        )

    async def get_thread(self, thread_id: str) -> Optional[ThreadDict]:
        logging.info(f"Trying to get thread id {thread_id}")
        thread = self.threads.get(thread_id)
        if not thread:
            logging.info(f"Thread id {thread_id} not found!")
            return None

        logging.info(f"Found thread id {thread_id}, trying to get the steps...")

        # Get steps for the thread
        thread_steps = [
            step for step in self.steps.values() if step.get("threadId") == thread_id
        ]

        logging.info(f"Steps found for thread {thread_id}: { json.dumps(thread_steps) }")

        # Get elements for the thread
        thread_elements = [
            element
            for element in self.elements.values()
            if element.get("threadId") == thread_id
        ]

        # Include steps and elements in thread dict
        enriched_thread = {
            **thread,
            "steps": thread_steps,
            "elements": thread_elements,
        }

        logging.info(f"Returning enriched thread {json.dumps(enriched_thread)}...")

        return enriched_thread

    async def build_debug_url(self, thread_id: str) -> Optional[str]:
        return ""
