from flask import Flask
import click


def enable_courses_commands(app: Flask):

    @app.cli.group()
    def course():
        """Course management commands."""
        pass

    @course.command(name="fix")
    @click.argument("course_id")
    def fix(course_id):
        """Fix a course."""
        pass

    return course
