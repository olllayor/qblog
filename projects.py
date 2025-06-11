import psycopg2
from database import get_db
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Project:
    def __init__(self, title, description, image_url=None, technologies=None, github_link=None, live_demo_link=None, date_added=None, id=None):
        self.id = id
        self.title = title
        self.description = description
        self.image_url = image_url
        self.technologies = technologies # Should be a comma-separated string or list
        self.github_link = github_link
        self.live_demo_link = live_demo_link
        self.date_added = date_added or datetime.now(timezone.utc)

    @staticmethod
    def save_project(project):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            # Ensure technologies is a string
            technologies_str = ",".join(project.technologies) if isinstance(project.technologies, list) else project.technologies
            cur.execute(
                """INSERT INTO projects (title, description, image_url, technologies, github_link, live_demo_link, date_added)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                (
                    project.title,
                    project.description,
                    project.image_url,
                    technologies_str,
                    project.github_link,
                    project.live_demo_link,
                    project.date_added.isoformat(),
                ),
            )
            project.id = cur.fetchone()[0]
            conn.commit()
            logger.info(f"Project '{project.title}' saved successfully with id {project.id}.")
            return True
        except psycopg2.Error as e:
            logger.error(f"Error saving project: {e}")
            conn.rollback() # Rollback in case of error
            return False
        finally:
            pass # Connection managed by app context

    @staticmethod
    def get_all_projects():
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return []
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, title, description, image_url, technologies, github_link, live_demo_link, date_added FROM projects ORDER BY date_added DESC")
            projects_data = cur.fetchall()
            projects = []
            for row in projects_data:
                technologies_list = row[4].split(',') if row[4] else []
                projects.append(Project(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    image_url=row[3],
                    technologies=technologies_list,
                    github_link=row[5],
                    live_demo_link=row[6],
                    date_added=row[7]
                ))
            return projects
        except psycopg2.Error as e:
            logger.error(f"Error fetching all projects: {e}")
            return []
        finally:
            pass # Connection managed by app context

    @staticmethod
    def get_project_by_id(project_id):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return None
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, title, description, image_url, technologies, github_link, live_demo_link, date_added FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if row:
                technologies_list = row[4].split(',') if row[4] else []
                return Project(
                    id=row[0],
                    title=row[1],
                    description=row[2],
                    image_url=row[3],
                    technologies=technologies_list,
                    github_link=row[5],
                    live_demo_link=row[6],
                    date_added=row[7]
                )
            return None
        except psycopg2.Error as e:
            logger.error(f"Error fetching project by id: {e}")
            return None
        finally:
            pass # Connection managed by app context

    @staticmethod
    def update_project(project):
        conn = get_db()
        if conn is None:
            logger.error("Failed to connect to the database.")
            return False
        try:
            cur = conn.cursor()
            technologies_str = ",".join(project.technologies) if isinstance(project.technologies, list) else project.technologies
            cur.execute(
                """UPDATE projects SET title = %s, description = %s, image_url = %s, technologies = %s, github_link = %s, live_demo_link = %s
                    WHERE id = %s""",
                (
                    project.title,
                    project.description,
                    project.image_url,
                    technologies_str,
                    project.github_link,
                    project.live_demo_link,
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
        finally:
            pass # Connection managed by app context

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
        finally:
            pass # Connection managed by app context
