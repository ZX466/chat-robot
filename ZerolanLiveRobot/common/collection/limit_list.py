from collections import deque


class LimitList(deque):
    def __init__(self, maxsize: int):
        super().__init__(maxlen=maxsize)

    @property
    def maxsize(self) -> int:
        return self.maxlen

    def add(self, item):
        super().append(item)

    def __setitem__(self, index, value):
        if index >= len(self):
            raise IndexError("List assignment index out of range")
        super().__setitem__(index, value)

    def __delitem__(self, index):
        if index >= len(self):
            raise IndexError("List assignment index out of range")
        super().__delitem__(index)

    def insert(self, index, item):
        if index > len(self):
            raise IndexError("List assignment index out of range")
        if len(self) == self.maxlen:
            super().popleft()
        super().insert(index, item)

    def extend(self, iterable):
        super().extend(iterable)

    def append(self, item):
        super().append(item)
