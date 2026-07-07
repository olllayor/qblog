import logging
from datetime import UTC, datetime

import psycopg2

from database import get_db

logger = logging.getLogger(__name__)

_PROJECT_COLUMNS = (
    "id, title, description, image_url, technologies, github_link, "
    "live_demo_link, date_added, is_visible, is_featured, sort_order"
)


class Project:
    def __init__(
        self,
        title,
        description,
        image_url=None,
        technologies=None,
        github_link=None,
        live_demo_link=None,
        date_added=None,
        id=None,
        is_visible=True,
        is_featured=False,
        sort_order=0,
    ):
        self.id = id
        self.title = title
        self.description = description
        self.image_url = image_url
        self.technologies = technologies  # Should be a comma-separated string or list
        self.github_link = github_link
        self.live_demo_link = live_demo_link
        self.date_added = date_added or datetime.now(UTC)
        self.is_visible = is_visible
        self.is_featured = is_featured
        self.sort_order = sort_order

    @staticmethod
    def _from_row(row):
        technologies_list = row[4].split(",") if row[4] else []
        return Project(
            id=row[0],
            title=row[1],
            description=row[2],
            image_url=row[3],
            technologies=technologies_list,
            github_link=row[5],
            live_demo_link=row[6],
            date_added=row[7],
            is_visible=row[8],
            is_featured=row[9],
            sort_order=row[10],
        )

    @staticmethod
    def save_project(project):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            # Ensure technologies is a string
            technologies_str = (
                ",".join(project.technologies)
                if isinstance(project.technologies, list)
                else project.technologies
            )
            cur.execute(
                """INSERT INTO projects
                    (title, description, image_url, technologies, github_link,
                     live_demo_link, date_added, is_visible, is_featured, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    project.title,
                    project.description,
                    project.image_url,
                    technologies_str,
                    project.github_link,
                    project.live_demo_link,
                    project.date_added.isoformat(),
                    project.is_visible,
                    project.is_featured,
                    project.sort_order,
                ),
            )
            project.id = cur.fetchone()[0]
            conn.commit()
            logger.info(
                f"Project '{project.title}' saved successfully with id {project.id}."
            )
            return True
        except psycopg2.Error as e:
            logger.error(f"Error saving project: {e}")
            conn.rollback()  # Rollback in case of error
            return False

    @staticmethod
    def get_all_projects():
        """All projects for the admin panel, curation order first."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {_PROJECT_COLUMNS} FROM projects "  # noqa: S608 — constant column list
                "ORDER BY sort_order ASC, date_added DESC"
            )
            return [Project._from_row(row) for row in cur.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Error fetching all projects: {e}")
            return []

    @staticmethod
    def get_visible_projects():
        """Publicly visible projects in curation order."""
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {_PROJECT_COLUMNS} FROM projects WHERE is_visible = TRUE "  # noqa: S608 — constant column list
                "ORDER BY sort_order ASC, date_added DESC"
            )
            return [Project._from_row(row) for row in cur.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Error fetching visible projects: {e}")
            return []

    @staticmethod
    def get_homepage_projects():
        """Featured visible projects; falls back to all visible when none are featured."""
        projects = Project.get_visible_projects()
        featured = [p for p in projects if p.is_featured]
        return featured or projects

    @staticmethod
    def get_project_by_id(project_id):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return None
        try:
            cur = conn.cursor()
            cur.execute(
                f"SELECT {_PROJECT_COLUMNS} FROM projects WHERE id = %s",  # noqa: S608 — constant column list
                (project_id,),
            )
            row = cur.fetchone()
            return Project._from_row(row) if row else None
        except psycopg2.Error as e:
            logger.error(f"Error fetching project by id: {e}")
            return None

    @staticmethod
    def update_project(project):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            technologies_str = (
                ",".join(project.technologies)
                if isinstance(project.technologies, list)
                else project.technologies
            )
            cur.execute(
                """UPDATE projects SET title = %s, description = %s, image_url = %s,
                    technologies = %s, github_link = %s, live_demo_link = %s,
                    is_visible = %s, is_featured = %s, sort_order = %s
                    WHERE id = %s""",
                (
                    project.title,
                    project.description,
                    project.image_url,
                    technologies_str,
                    project.github_link,
                    project.live_demo_link,
                    project.is_visible,
                    project.is_featured,
                    project.sort_order,
                    project.id,
                ),
            )
            conn.commit()
            logger.info(f"Project '{project.title}' updated successfully.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error updating project: {e}")
            conn.rollback()
            return False

    @staticmethod
    def set_flag(project_id, column, value):
        """Set is_visible or is_featured for a project."""
        if column not in ("is_visible", "is_featured"):
            raise ValueError(f"Unsupported flag column: {column}")
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE projects SET {column} = %s WHERE id = %s",  # noqa: S608 — column whitelisted above
                (value, project_id),
            )
            conn.commit()
            return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Error setting {column} on project {project_id}: {e}")
            conn.rollback()
            return False

    @staticmethod
    def move(project_id, direction):
        """Swap sort_order with the neighbour above/below in admin ordering."""
        if direction not in ("up", "down"):
            return False
        projects = Project.get_all_projects()
        # Normalize sort_order to the current display order so swaps are stable
        # even when rows share the default 0.
        for i, p in enumerate(projects):
            p.sort_order = i
        index = next((i for i, p in enumerate(projects) if p.id == project_id), None)
        if index is None:
            return False
        swap_with = index - 1 if direction == "up" else index + 1
        if swap_with < 0 or swap_with >= len(projects):
            return True  # already at the edge; nothing to do
        projects[index].sort_order, projects[swap_with].sort_order = (
            projects[swap_with].sort_order,
            projects[index].sort_order,
        )

        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            for p in projects:
                cur.execute(
                    "UPDATE projects SET sort_order = %s WHERE id = %s",
                    (p.sort_order, p.id),
                )
            conn.commit()
            return True
        except psycopg2.Error as e:
            logger.error(f"Error reordering projects: {e}")
            conn.rollback()
            return False

    @staticmethod
    def delete_project_by_id(project_id):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM projects WHERE id = %s", (project_id,))
            conn.commit()
            logger.info(f"Project with id {project_id} deleted successfully.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error deleting project: {e}")
            conn.rollback()
            return False
