"""Neo4j driver wrapper."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from neo4j import Driver, GraphDatabase, Session

from catalog.config import Settings


class Neo4jClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._driver: Driver | None = None

    def connect(self) -> None:
        self._driver = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )
        self._driver.verify_connectivity()

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @property
    def driver(self) -> Driver:
        if self._driver is None:
            raise RuntimeError("Neo4jClient.connect() must be called first")
        return self._driver

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.driver.session(database=self.settings.neo4j_database) as session:
            yield session

    def __enter__(self) -> "Neo4jClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
