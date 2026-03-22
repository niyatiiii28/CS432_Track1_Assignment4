from graphviz import Digraph
class BPlusTreeNode:
    def __init__(self, leaf=False):
        self.keys = []
        self.children = []
        self.values = []
        self.leaf = leaf
        self.next = None   # pointer to next leaf node

class BPlusTree:

    def __init__(self, t=3):
        self.root = BPlusTreeNode(True)
        self.t = t   # minimum degree
    
    def search(self, key):
        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, item in enumerate(node.keys):
            if item == key:
                return node.values[i]

        return None
    
    def insert(self, key, value):

        root = self.root

        if len(root.keys) == (2 * self.t - 1):
            new_root = BPlusTreeNode()
            new_root.children.append(self.root)
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

        t = self.t
        node = parent.children[index]

        new_node = BPlusTreeNode(node.leaf)

        parent.keys.insert(index, node.keys[t - 1])
        parent.children.insert(index + 1, new_node)

        new_node.keys = node.keys[t:]
        node.keys = node.keys[:t ]

        if node.leaf:
            new_node.values = node.values[t:]
            node.values = node.values[:t]

            new_node.next = node.next
            node.next = new_node

        else:
            new_node.children = node.children[t:]
            node.children = node.children[:t]

    def range_query(self, start_key, end_key):

        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and start_key >= node.keys[i]:
                i += 1
            node = node.children[i]

        results = []

        while node:
            for i, key in enumerate(node.keys):
                if start_key <= key <= end_key:
                    results.append((key, node.values[i]))

            node = node.next

        return results
    
    def update(self, key, new_value):

        node = self.root

        while not node.leaf:
            i = 0
            while i < len(node.keys) and key >= node.keys[i]:
                i += 1
            node = node.children[i]

        for i, k in enumerate(node.keys):
            if k == key:
                node.values[i] = new_value
                return True

        return False
    
    def get_all(self):

        node = self.root

        while not node.leaf:
            node = node.children[0]

        results = []

        while node:
            for i, key in enumerate(node.keys):
                results.append((key, node.values[i]))

            node = node.next

        return results
    

    # Delete
    def delete(self, key):

        if not self.root:
            return False

        self._delete(self.root, key)

        # if root becomes empty
        if not self.root.leaf and len(self.root.keys) == 0:
            self.root = self.root.children[0]

        return True
    
    def _delete(self, node, key):

        t = self.t

        # Case 1: Leaf node
        if node.leaf:

            if key in node.keys:
                idx = node.keys.index(key)
                node.keys.pop(idx)
                node.values.pop(idx)

            return

        # Case 2: Internal node

        i = 0
        while i < len(node.keys) and key >= node.keys[i]:
            i += 1

        child = node.children[i]

        # if child has minimum keys
        if len(child.keys) < t:
            self._fill_child(node, i)
            
            if i >= len(node.children):
                i = len(node.children) - 1

        self._delete(node.children[i], key)
    
    def _fill_child(self, node, index):

        if index > 0 and len(node.children[index - 1].keys) >= self.t:
            self._borrow_from_prev(node, index)

        elif index < len(node.children) - 1 and len(node.children[index + 1].keys) >= self.t:
            self._borrow_from_next(node, index)

        else:
            if index < len(node.children) - 1:
                self._merge(node, index)
            else:
                self._merge(node, index - 1)

    def _borrow_from_prev(self, node, index):

        child = node.children[index]
        sibling = node.children[index - 1]

        child.keys.insert(0, node.keys[index - 1])

        if not child.leaf:
            child.children.insert(0, sibling.children.pop())

        node.keys[index - 1] = sibling.keys.pop()

    def _borrow_from_next(self, node, index):

        child = node.children[index]
        sibling = node.children[index + 1]

        child.keys.append(node.keys[index])

        if not child.leaf:
            child.children.append(sibling.children.pop(0))

        node.keys[index] = sibling.keys.pop(0)

    
    def _merge(self, node, index):

        child = node.children[index]
        sibling = node.children[index + 1]

        child.keys.append(node.keys[index])

        child.keys.extend(sibling.keys)

        if not child.leaf:
            child.children.extend(sibling.children)

        node.keys.pop(index)
        node.children.pop(index + 1)
    
    

    def visualize_tree(self):

        dot = Digraph(name="BPlusTree")
        dot.attr(rankdir="TB")
        dot.attr('node', shape='box')
        dot.attr(ranksep="1.0")
        dot.attr(nodesep="0.5")

        seen = set()

        def add_node(node):
            node_id = f"n{id(node)}"

            if node_id in seen:
                return
            seen.add(node_id)

            # Create label
            label = " | ".join(str(k) for k in node.keys)
            label = "{" + label + "}"

            # Leaf vs internal styling
            if node.leaf:
                dot.node(node_id, label, style='filled', fillcolor='lightgreen')
            else:
                dot.node(node_id, label, style='filled', fillcolor='lightblue')

                # Add children recursively
                for child in node.children:
                    child_id = f"n{id(child)}"
                    dot.edge(node_id, child_id)
                    add_node(child)

        # Build tree
        if self.root:
            add_node(self.root)

        # -------- LEAF LINKING --------

        # Find leftmost leaf
        node = self.root
        while node and not node.leaf:
            node = node.children[0]

        leaves = []
        while node:
            leaves.append(node)
            node = node.next

        # Keep leaves at same level
        with dot.subgraph() as s:
            s.attr(rank='same')
            for leaf in leaves:
                s.node(f"n{id(leaf)}")

        # Add dashed links between leaves
        for i in range(len(leaves) - 1):
            dot.edge(
                f"n{id(leaves[i])}",
                f"n{id(leaves[i+1])}",
                style="dashed",
                color="green",
                constraint="false"
            )

        return dot