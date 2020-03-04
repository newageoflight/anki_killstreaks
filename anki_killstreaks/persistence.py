from datetime import datetime
import itertools
from pathlib import Path
import sqlite3

from anki_killstreaks._vendor import attr
from anki_killstreaks._vendor.yoyo import read_migrations
from anki_killstreaks._vendor.yoyo import get_backend

from anki_killstreaks.toolz import join
from anki_killstreaks.streaks import get_all_displayable_medals


@attr.s(frozen=True)
class DbSettings:
    db_path = attr.ib()
    migration_dir_path = attr.ib()

    @classmethod
    def from_addon_path(cls, addon_path):
        return cls(
            db_path=addon_path / 'user_files' / 'medals.db',
            migration_dir_path=addon_path / 'migrations'
        )

    @property
    def db_uri(self):
        return f"sqlite:///{self.db_path}"


this_addon_path = Path(__file__).parent.absolute()
default_settings = DbSettings.from_addon_path(this_addon_path)


def migrate_database(settings=default_settings):
    backend = get_backend(settings.db_uri)
    migrations = read_migrations(str(settings.migration_dir_path))

    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))

    return settings


def get_db_connection(db_settings=default_settings):
    return sqlite3.connect(str(db_settings.db_path), isolation_level=None)


class AchievementsRepository:
    def __init__(self, db_connection):
        self.conn = db_connection

    def create_all(self, new_achievements):
        self.conn.executemany(
            "INSERT INTO achievements(medal_id, deck_id) VALUES (?, ?)",
            ((a.medal_name, a.deck_id) for a in new_achievements)
        )

    # This whole method can be replaced with a groupby count(*) on medal_id
    def all(self):
        cursor = self.conn.execute("SELECT * FROM achievements")

        loaded_achievements = [
            PersistedAchievement(*row, medal=None)
            for row
            in cursor
        ]

        # will probably become a performance issue, move to
        # spot where we need this join.
        matches = join(
            leftseq=get_all_displayable_medals(),
            rightseq=loaded_achievements,
            leftkey=lambda dm: dm.name,
            rightkey=lambda la: la.medal_id
        )

        return [
            persisted_achievement.with_medal(medal)
            for medal, persisted_achievement
            in matches
        ]


    def todays_achievements(self, day_start_time):
        """
        :param day_start_time unix epoch time corresponding to when day starts
        """
        return self.count_by_medal_id(created_at_gt=datetime.utcfromtimestamp(day_start_time))

    def count_by_medal_id(self, created_at_gt=datetime.min):
        cursor = self.conn.execute(
            """
            SELECT medal_id, count(*)
            FROM achievements
            WHERE created_at > ?
            GROUP BY medal_id
            """,
            (created_at_gt,)
        )

        return dict(row for row in cursor)

    def todays_achievements_for_deck_ids(self, day_start_time, deck_ids):
        created_at_gt = datetime.utcfromtimestamp(day_start_time)

        return self.achievements_for_deck_ids_since(
            deck_ids=deck_ids,
            since_datetime=created_at_gt
        )

    def achievements_for_deck_ids_since(self, deck_ids, since_datetime):
        cursor = self.conn.execute(
            f"""
            SELECT medal_id, count(*)
            FROM achievements
            WHERE created_at > ? AND
                deck_id in ({','.join('?' for i in deck_ids)})
            GROUP BY medal_id
            """,
            (since_datetime, *deck_ids)
        )

        return dict(row for row in cursor)

    def achievements_for_whole_collection_since(self, since_datetime):
        cursor = self.conn.execute(
            f"""
            SELECT medal_id, count(*)
            FROM achievements
            WHERE created_at > ?
            GROUP BY medal_id
            """,
            (since_datetime,)
        )

        return dict(row for row in cursor)



@attr.s
class PersistedAchievement:
    id_ = attr.ib()
    medal_id = attr.ib()
    created_at = attr.ib()
    deck_id = attr.ib()
    medal = attr.ib()

    def with_medal(self, medal):
        return attr.evolve(self, medal=medal)

    @property
    def medal_name(self):
        return self.medal.name

    @property
    def medal_img_src(self):
        return self.medal.medal_image