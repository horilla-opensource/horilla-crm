from copy import deepcopy

BASE_STEPS = [
    {"step": 1, "title": "Database authentication"},
    {"step": 2, "title": "Sign Up"},
    {"step": 3, "title": "Company Info"},
    {"step": 4, "title": "Role"},
]


class ProgressStepsMixin:
    current_step = 1  # override in each view

    def get_progress_steps(self):
        steps = deepcopy(BASE_STEPS)  # avoid modifying global list
        for step in steps:
            step["active"] = step["step"] <= self.current_step
        return steps

    def is_last_step(self):
        return self.current_step == BASE_STEPS[-1]["step"]
