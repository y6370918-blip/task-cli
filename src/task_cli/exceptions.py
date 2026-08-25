class TaskNotFoundError(Exception):
    def __init__(
        self,
        task_id: int,
    ) -> None:

        self.task_id = task_id


class UserAlreadyExistsError(Exception):
    pass
