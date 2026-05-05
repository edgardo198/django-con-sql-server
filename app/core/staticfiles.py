from django.contrib.staticfiles.apps import StaticFilesConfig


class ProjectStaticFilesConfig(StaticFilesConfig):
    ignore_patterns = StaticFilesConfig.ignore_patterns + [
        '__pycache__',
        '__pycache__/*',
        '*.py',
        '*.pyc',
        '*.pyo',
    ]
