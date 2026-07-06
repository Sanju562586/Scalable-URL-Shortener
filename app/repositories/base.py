"""
Abstract generic repository (base class).

Follows the Repository pattern — provides a standard CRUD interface
that concrete repositories inherit, extend, or override.

Type parameter T is the SQLAlchemy ORM model class.
"""

from typing import Generic, TypeVar, Type, Optional
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Generic CRUD repository.

    Subclasses must pass their model class to the constructor:

        class URLRepository(BaseRepository[URL]):
            def __init__(self, db: Session) -> None:
                super().__init__(db, URL)
    """

    def __init__(self, db: Session, model: Type[T]) -> None:
        self._db = db
        self._model = model

    def get_by_id(self, record_id: int) -> Optional[T]:
        """Fetch a single record by primary key, or None."""
        return self._db.get(self._model, record_id)

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Retrieve a paginated list of all records."""
        return (
            self._db.query(self._model)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(self, obj: T) -> T:
        """Persist a new ORM object and return it with its generated PK."""
        self._db.add(obj)
        self._db.flush()   # populate auto-generated fields (id, timestamps)
        self._db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        """Hard-delete a record from the database."""
        self._db.delete(obj)
        self._db.flush()

    def commit(self) -> None:
        """Commit the current transaction."""
        self._db.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        self._db.rollback()
