from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Float, String, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()


class Bookie(Base):

    __tablename__ = 'bookie'

    id = Column(Integer, primary_key = True)
    name = Column(String, nullable = False)
    events = relationship('BookieEvent', order_by = 'BookieEvent.id', backref = 'bookie')
    odds = relationship('Odds', order_by = 'Odds.id', backref = 'bookie')

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Bookie(name = '{self.name}')"


class Event(Base):

    __tablename__ = 'event'

    id = Column(Integer, primary_key = True)
    course = Column(String, nullable = False)
    date_time = Column(DateTime, nullable = False)
    bookies = relationship('BookieEvent', order_by = 'BookieEvent.id', backref = 'event')
    runners = relationship('Runner', order_by = 'Runner.name', backref = 'event')
    last_checkpoint_id = Column(Integer, ForeignKey('checkpoint.id'), nullable = True)
    last_checkpoint = relationship('Checkpoint', foreign_keys = 'Event.last_checkpoint_id')
    checkpoints = relationship('Checkpoint', primaryjoin = 'Event.id == Checkpoint.event_id', order_by = 'Checkpoint.date_time', backref = 'event')

    def __str__(self):
        return f"{self.course} {self.date_time}"

    def __repr__(self):
        return f"Event(course = '{self.course}', date_time = '{self.date_time}')"


class BookieEvent(Base):

    __tablename__ = 'bookie_event'

    id = Column(Integer, primary_key = True)
    bookie_id = Column(Integer, ForeignKey('bookie.id'), nullable = False)
    event_id = Column(Integer, ForeignKey('event.id'), nullable = False)
    ew_places = Column(Integer, default = 0, nullable = False)
    ew_divider = Column(Integer, default = 1, nullable = False)

    def __str__(self):
        return f"{self.bookie}: {self.event}"

    def __repr__(self):
        return f"BookieEvent(bookie_id = {self.bookie_id}, event_id = {self.event_id}, ew_places = {self.ew_places}, ew_divider = {self.ew_divider})"


class Runner(Base):

    __tablename__ = 'runner'

    id = Column(Integer, primary_key = True)
    event_id = Column(Integer, ForeignKey('event.id'), nullable = False)
    name = Column(String, nullable = False)
    odds = relationship('Odds', order_by = 'Odds.id', backref = 'runner')

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Runner(event_id = {self.event_id}, name = '{self.name}')"


class Checkpoint(Base):

    __tablename__ = 'checkpoint'

    id = Column(Integer, primary_key = True)
    event_id = Column(Integer, ForeignKey('event.id'), nullable = False)
    date_time = Column(DateTime, nullable = False)
    source = Column(String, nullable = False)
    odds = relationship('Odds', order_by = 'Odds.id', backref = 'checkpoint')

    def __str__(self):
        return f"<Checkpoint: {self.event.course}, {self.event.date_time}, {self.date_time}>"

    def __repr__(self):
        return f"Checkpoint(event_id = {self.event_id}, date_time = '{self.date_time}')"


class Odds(Base):

    __tablename__ = 'odds'

    id = Column(Integer, primary_key = True)
    checkpoint_id = Column(Integer, ForeignKey('checkpoint.id'), nullable = False)
    runner_id = Column(Integer, ForeignKey('runner.id'), nullable = False)
    bookie_id = Column(Integer, ForeignKey('bookie.id'), nullable = False)
    win = Column(Float, nullable = False)
    place = Column(Float, nullable = False)

    def __str__(self):
        return f"<Odds: {self.checkpoint.date_time}, {self.runner.name}, {self.bookie.name}, {self.win}, {self.place}>"

    def __repr__(self):
        return f"Odds(checkpoint_id = {self.checkpoint_id}, runner_id = {self.runner_id}, bookie_id = {self.bookie_id}, win = {self.value}, place = {self.place})"
