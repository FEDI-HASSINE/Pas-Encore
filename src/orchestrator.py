class Orchestrator:
    """
    Main simulation orchestrator.

    It retrieves pending tasks, asks the allocation strategy
    where to execute them, and launches their execution.
    """

    def __init__(self, env, pending_store, strategy):
        self.env = env
        self.pending_store = pending_store
        self.strategy = strategy

    def run(self):
        """
        Main orchestration loop.
        """
        while True:
            task = yield self.pending_store.get()

            node = self.strategy.allocate(task, self.env.now)

            self.env.process(
                self.execute_task(node, task)
            )

    def execute_task(self, node, task):
        """
        Simulates execution of a task on a node.
        """

        node.cpu_utilized += task.cpu_units

        try:
            yield self.env.timeout(task.cpu_units)
        finally:
            node.cpu_utilized -= task.cpu_units