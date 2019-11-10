#!/usr/bin/env python3
# encoding: utf-8

from abc import ABC
from enum import Enum
from typing import List, Callable

import npyscreen


class Hotkeys(int, Enum):
    CTRL_UP = 566
    CTRL_DOWN = 525
    CTRL_RIGHT = 560
    CTRL_LEFT = 545


#
# Domain classes
#


class Task:
    def __init__(self, position: int, name: str) -> None:
        self.position = position
        self.name = name


class Project:
    def __init__(self, position: int, name: str, tasks: List[Task] = None) -> None:
        self.position = position
        self.name = name
        self.tasks = tasks


class Group:
    def __init__(
            self,
            position: int,
            name: str,
            projects: List[Project] = None,
            tasks: List[Task] = None,
    ) -> None:
        self.position = position
        self.name = name
        self.projects = projects
        self.tasks = tasks


class Database:
    DATA_ = {
        Group(
            1,
            "Home",
            tasks=[Task(1, "Watch movies")],
            projects=[
                Project(
                    1, "Movies", tasks=[Task(1, "Watch Matrix"), Task(2, "Watch Matrix II")]
                )
            ],
        )
    }

    @staticmethod
    def get_groups() -> List[Group]:
        return [key for key in Database.DATA_]

    @staticmethod
    def get_projects_by_group(group) -> List[Project]:
        return group.projects


DATABASE: Database = Database()


#
# Controller
#


class StrEnum(str, Enum):
    pass


class BuiltinViews(StrEnum):
    INBOX = ("Inbox",)
    TODAY = ("Today",)
    UPCOMING = ("Upcoming",)
    ANYTIME = ("Anytime",)
    SOMEDAY = ("Someday",)
    LOGBOOK = "Logbook"


class TaskView:
    def __init__(self, task: Task):
        self.task = task

    def __str__(self):
        return self.task.name


class ListView(ABC):
    def __init__(self, name: str, description: str = None, icon: str = None, shortcut: int = None) -> None:
        self.name_: str = name
        self.description_: str = description
        self.icon_: str = icon
        self.shortcut: int = shortcut

    @property
    def name(self) -> str:
        return self.name_

    @property
    def description(self) -> str:
        return self.description_

    @property
    def icon(self) -> str:
        return self.icon_

    @property
    def tasks(self) -> List[TaskView]:
        return []


class ViewListView(ListView):
    def __str__(self) -> str:
        if self.shortcut:
            return "{}. {}".format(self.shortcut, self.name)
        else:
            return "   {}".format(self.name)


class GroupListView(ListView):
    def __init__(self, group: Group):
        super(GroupListView, self).__init__(
            group.name,
        )
        self.group: Group = group

    @property
    def tasks(self) -> List[TaskView]:
        result: List[TaskView] = [TaskView(task) for task in self.group.tasks]
        for project in self.group.projects:
            for task in project.tasks:
                result.append(TaskView(task))
        return result

    def __str__(self) -> str:
        return self.name


class ProjectListView(ListView):
    def __init__(self, project: Project):
        super(ProjectListView, self).__init__(project.name)
        self.project: Project = project

    @property
    def tasks(self) -> List[TaskView]:
        return [TaskView(task) for task in self.project.tasks]

    def __str__(self) -> str:
        return "  " + self.name


class DelimiterListView(ListView):
    def __str__(self) -> str:
        return ""


class State:
    @staticmethod
    def get_builtin_lists():
        result: List[ListView] = []
        shortcut = 0
        for view in BuiltinViews:
            result.append(ViewListView(view, shortcut=shortcut))
            shortcut += 1
        return result

    @staticmethod
    def get_user_lists() -> List[ListView]:
        result: List[ListView] = []
        for group in DATABASE.get_groups():
            result.append(GroupListView(group))
            for project in DATABASE.get_projects_by_group(group):
                result.append(ProjectListView(project))
        return result

    @staticmethod
    def get_all_lists() -> List[ListView]:
        result: List[ListView] = State.get_builtin_lists()
        result.insert(1, DelimiterListView(""))
        result.append(DelimiterListView(""))

        result.extend(State.get_user_lists())
        return result


STATE: State = State()


class MultiLineActionWithDelegate(npyscreen.MultiLineAction):
    def __init__(self, screen, on_selection: Callable = None, *args, **keywords) -> None:
        super(MultiLineActionWithDelegate, self).__init__(screen, *args, **keywords)
        self.on_selection_ = on_selection

    def when_cursor_moved(self) -> None:
        super(MultiLineActionWithDelegate, self).when_cursor_moved()
        if self.on_selection_:
            self.on_selection_(self.values[self.cursor_line])

    @property
    def on_selection(self):
        return self.on_selection_

    @on_selection.setter
    def on_selection(self, on_selection):
        self.on_selection_ = on_selection


class ListsViewWidget(npyscreen.BoxTitle):
    _contained_widget = MultiLineActionWithDelegate

    def __init__(self, screen, *args, **keywords) -> None:
        super(ListsViewWidget, self).__init__(
            screen,
            name="Lists",
            footer="0 projects",
            *args,
            **keywords
        )
        all_lists: List[ListView] = STATE.get_all_lists()
        self.entry_widget.values = all_lists
        self.footer = f"{len(STATE.get_user_lists())} projects"

        self.entry_widget.on_selection = self.on_list_view_selected

    def on_list_view_selected(self, list_view: ListView) -> None:
        self.main_form().display_list(list_view)

    def main_form(self):
        return self.parent.parentApp.main_form()


class TasksViewWidget(npyscreen.BoxTitle):
    _contained_widget = MultiLineActionWithDelegate

    def __init__(self, screen, *args, **keywords) -> None:
        super(TasksViewWidget, self).__init__(
            screen,
            name="Tasks",
            footer="0 tasks",
            *args,
            **keywords
        )

    def display_list(self, list_view: ListView):
        if len(list_view.name):
            title: str = list_view.name
            if len(list_view.tasks):
                title = "{} ({})".format(list_view.name, len(list_view.tasks))
            self.name: str = title
        self.entry_widget.values = list_view.tasks
        self.update()


class MainForm(npyscreen.FormBaseNew):
    def __init__(self, *args, **keywords):
        super(MainForm, self).__init__(*args, **keywords)
        self.title_widget: npyscreen.Textfield = self.add_widget(
            npyscreen.Textfield,
            name="TerminalThings",
            value="TerminalThings",
            relx=1,
            rely=1,
            editable=False,

        )
        self.lists_view_widget: ListsViewWidget = self.add_widget(ListsViewWidget, relx=1, rely=2, width=30)
        self.tasks_view_widget: TasksViewWidget = self.add_widget(TasksViewWidget, relx=31, rely=2)
        self.cycle_widgets = True

    def display_list(self, list_view: ListView):
        self.tasks_view_widget.display_list(list_view)

    def create(self):
        pass


class TestApp(npyscreen.NPSAppManaged):
    def onStart(self):
        npyscreen.setTheme(npyscreen.Themes.ColorfulTheme)
        self.registerForm("MAIN", MainForm())

    def main_form(self):
        return self.getForm("MAIN")


if __name__ == "__main__":
    TestApp().run()
