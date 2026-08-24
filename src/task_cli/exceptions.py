class TaskNotFoundError(Exception):
    def __init__(
        self,
        task_id: int,
    ):

        self.task_id = task_id


class UserAlreadyExistsError(Exception):
    pass
