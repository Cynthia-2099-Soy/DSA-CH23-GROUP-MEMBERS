"""
audit_stack.py
--------------
Data structure used: STACK (Python list used LIFO)

Every mutating action taken on the server (inserting a tick, registering
a symbol) is pushed onto an audit stack. This gives:
  1. An audit trail (compliance/history requirement common to financial
     systems), and
  2. Undo/rollback -- popping the stack reverses the most recent action,
     which is exactly the "undo/history/backtracking" use-case a stack
     is required for in this project.

Complexity
----------
record (push):  O(1)
undo (pop):     O(1)
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable, List, Optional


@dataclass
class AuditEntry:
    action: str                 # human-readable description
    undo_fn: Callable[[], None]  # closure that reverses the action


class AuditStack:
    def __init__(self):
        self._stack: List[AuditEntry] = []

    def record(self, action: str, undo_fn: Callable[[], None]) -> None:
        """Push a new action + its undo function onto the stack. O(1)."""
        self._stack.append(AuditEntry(action, undo_fn))

    def undo_last(self) -> Optional[str]:
        """
        Pop the most recent action and reverse it. O(1).
        Returns the description of the action that was undone, or None
        if there is nothing to undo.
        """
        if not self._stack:
            return None
        entry = self._stack.pop()
        entry.undo_fn()
        return entry.action

    def history(self) -> List[str]:
        """Return actions oldest-first, for display purposes only."""
        return [entry.action for entry in self._stack]

    def __len__(self) -> int:
        return len(self._stack)
