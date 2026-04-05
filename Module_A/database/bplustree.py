class BPlusTreeNode:
    def __init__(self, leaf=False):
        self.keys = []
        self.children = []
        self.values = []
        self.leaf = leaf
        self.next = None  # leaf linkage


class BPlusTree:
    def __init__(self, t=3):
        self.root = BPlusTreeNode(leaf=True)
        self.t = t

    # ---------------- SEARCH ---------------- #
    def search(self, key):
        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, k in enumerate(node.keys):
            if k == key:
                return node.values[i]
        return None

    # ---------------- INSERT ---------------- #
    def insert(self, key, value):
        root = self.root

        # duplicate → overwrite
        if self.search(key) is not None:
            self.update(key, value)
            return

        if len(root.keys) == (2 * self.t - 1):
            new_root = BPlusTreeNode(leaf=False)
            new_root.children.append(root)
            self._split_child(new_root, 0)
            self.root = new_root

        self._insert_non_full(self.root, key, value)

    def _insert_non_full(self, node, key, value):
        if node.leaf:
            i = 0
            while i < len(node.keys) and node.keys[i] < key:
                i += 1
            node.keys.insert(i, key)
            node.values.insert(i, value)

        else:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1

            child = node.children[i]

            if len(child.keys) == (2 * self.t - 1):
                self._split_child(node, i)
                if key >= node.keys[i]:
                    i += 1

            self._insert_non_full(node.children[i], key, value)

    def _split_child(self, parent, index):
        node = parent.children[index]
        t = self.t

        new_node = BPlusTreeNode(leaf=node.leaf)

        if node.leaf:
            # split leaf
            new_node.keys = node.keys[t:]
            new_node.values = node.values[t:]

            node.keys = node.keys[:t]
            node.values = node.values[:t]

            # fix leaf links
            new_node.next = node.next
            node.next = new_node

            # insert separator
            parent.keys.insert(index, new_node.keys[0])

        else:
            # split internal
            parent.keys.insert(index, node.keys[t - 1])

            new_node.keys = node.keys[t:]
            node.keys = node.keys[:t - 1]

            new_node.children = node.children[t:]
            node.children = node.children[:t]

        parent.children.insert(index + 1, new_node)

    # ---------------- UPDATE ---------------- #
    def update(self, key, value):
        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, k in enumerate(node.keys):
            if k == key:
                node.values[i] = value
                return True
        return False

    # ---------------- DELETE ---------------- #
    def delete(self, key):
        value = self.search(key)
        if value is None:
            return None

        self._delete(self.root, key)

        # fix root
        if not self.root.leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return value

    def _delete(self, node, key):
        t = self.t

        if node.leaf:
            if key in node.keys:
                idx = node.keys.index(key)
                node.keys.pop(idx)
                node.values.pop(idx)
            return

        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1

        child = node.children[i]

        if len(child.keys) < t:
            self._fill(node, i)

            if i >= len(node.children):
                i = len(node.children) - 1

        self._delete(node.children[i], key)

    def _fill(self, node, idx):
        # minimum keys = t-1

        if idx > 0 and len(node.children[idx - 1].keys) > self.t - 1:
            self._borrow_from_prev(node, idx)

        elif idx < len(node.children) - 1 and len(node.children[idx + 1].keys) > self.t - 1:
            self._borrow_from_next(node, idx)

        else:
            #  MERGE WILL HAPPEN HERE
            if idx < len(node.children) - 1:
                self._merge(node, idx)
            else:
                self._merge(node, idx - 1)

    def _borrow_from_prev(self, node, idx):
        child = node.children[idx]
        sibling = node.children[idx - 1]

        if child.leaf:
            child.keys.insert(0, sibling.keys.pop())
            child.values.insert(0, sibling.values.pop())
            node.keys[idx - 1] = child.keys[0]
        else:
            child.keys.insert(0, node.keys[idx - 1])
            node.keys[idx - 1] = sibling.keys.pop()
            child.children.insert(0, sibling.children.pop())

    def _borrow_from_next(self, node, idx):
        child = node.children[idx]
        sibling = node.children[idx + 1]

        if child.leaf:
            child.keys.append(sibling.keys.pop(0))
            child.values.append(sibling.values.pop(0))
            node.keys[idx] = sibling.keys[0]
        else:
            child.keys.append(node.keys[idx])
            node.keys[idx] = sibling.keys.pop(0)
            child.children.append(sibling.children.pop(0))

    def _merge(self, node, idx):
        child = node.children[idx]
        sibling = node.children[idx + 1]

        if child.leaf:
            #  leaf merge (NO parent key)
            child.keys.extend(sibling.keys)
            child.values.extend(sibling.values)

            # fix linked list
            child.next = sibling.next

        else:
            #  internal merge (include separator)
            child.keys.append(node.keys[idx])
            child.keys.extend(sibling.keys)
            child.children.extend(sibling.children)

        # remove separator from parent
        node.keys.pop(idx)
        node.children.pop(idx + 1)

    # ---------------- RANGE QUERY ---------------- #
    def range_query(self, start, end):
        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and start >= node.keys[i]:
                i += 1
            node = node.children[i]

        result = []

        while node:
            for i, k in enumerate(node.keys):
                if start <= k <= end:
                    result.append((k, node.values[i]))
            node = node.next

        return result

    # ---------------- GET ALL ---------------- #
    def get_all(self):
        node = self.root
        while not node.leaf:
            node = node.children[0]

        result = []
        while node:
            for i, k in enumerate(node.keys):
                result.append((k, node.values[i]))
            node = node.next

        return result