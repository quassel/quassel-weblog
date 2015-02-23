from datetime import datetime
from time import mktime
from sqlalchemy import \
	MetaData, Table, Column, \
	Integer, DateTime, String, Text, Boolean, Sequence, \
	ForeignKey, \
	PrimaryKeyConstraint, UniqueConstraint, \
	create_engine, \
	desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.schema import Index
from sqlalchemy.types import TypeDecorator


class IntegerDateTime(TypeDecorator):
	"""
	Used for working with epoch timestamps.

	Converts datetimes into epoch on the way in.
	Converts epoch timestamps to datetimes on the way out.
	"""
	impl = Integer()
	def process_bind_param(self, value, dialect):
		return mktime(value.timetuple())
	def process_result_value(self, value, dialect):
		return datetime.fromtimestamp(value)


QuasselDateTime = DateTime()
QuasselDateTime = QuasselDateTime.with_variant(IntegerDateTime(), "sqlite")


class Base(object):
	def _filter_properties(self):
		# this function decides which properties should be exposed through repr
		# todo: don"t show methods
		properties = self.__dict__.keys()
		for prop in properties:
			if not prop.startswith("_"):
				yield (prop, getattr(self, prop))
		return

	def __repr__(self):
		prop_tuples = self._filter_properties()
		prop_string_tuples = ("{0}={1}".format(*prop) for prop in prop_tuples)
		prop_output_string = ", ".join(prop_string_tuples)
		cls_name = self.__class__.__name__
		return "{0}({1})".format(cls_name, prop_output_string)

	def to_dict(self):
		prop_tuples = self._filter_properties()
		d = dict(prop_tuples)
		for k,v in d.items():
			if hasattr(v, "__table__") and hasattr(v, "to_dict"):
				d[k] = v.to_dict()
		return d

	def to_json(self):
		from json import dumps
		return dumps(self.to_dict())


Model = declarative_base(cls=Base)

class Message(Model):
	__tablename__ = "backlog"
	id = Column("messageid", Integer, Sequence("backlog_messageid_seq"), nullable=False, primary_key=True)
	time = Column(QuasselDateTime, nullable=False)
	bufferid = Column(Integer, ForeignKey("buffer.bufferid", ondelete="CASCADE"), nullable=False)
	type = Column(Integer, nullable=False)
	flags = Column(Integer, nullable=False)
	senderid = Column(Integer, ForeignKey("sender.senderid", ondelete="SET NULL"), nullable=False)
	message = Column(Text)

	buffer = relationship("Buffer", backref="messages")
	sender = relationship("Sender", backref="messages")

	__tablemeta__ = [
		Index("backlog_bufferid_idx", "bufferid"),
		Index("backlog_buffer_time_idx", "bufferid", "time"),
	]

class Sender(Model):
	__tablename__ = "sender"
	id = Column("senderid", Integer, Sequence("sender_senderid_seq"), nullable=False, primary_key=True)
	name = Column("sender", String(128), nullable=False, unique=True)

	def pretty_name(self):
		return self.name.split("!")[0]


class Buffer(Model):
	__tablename__ = "buffer"
	id = Column("bufferid", Integer, Sequence("buffer_bufferid_seq"), nullable=False, primary_key=True)
	userid = Column(Integer, ForeignKey("quasseluser.userid", ondelete="CASCADE"), nullable=False, unique=True)
	groupid = Column(Integer)
	networkid = Column(Integer, ForeignKey("network.networkid", ondelete="CASCADE"), nullable=False, unique=True)
	name = Column("buffername", String(128), nullable=False)
	cname = Column("buffercname", String(128), nullable=False, unique=True)
	type = Column("buffertype", Integer, nullable=False, default=0)
	lastseenmsgid = Column(Integer, nullable=False, default=0)
	markerlinemsgid = Column(Integer, nullable=False, default=0)
	key = Column(String(128))
	joined = Column(Boolean, nullable=False, default=False)

	user = relationship("QuasselUser", backref="buffers")
	network = relationship("Network", backref="buffers")

	__tablemeta__ = [
		Index("buffer_idx", "userid", "networkid", "buffername"),
		Index("buffer_cname_idx", "userid", "networkid", "buffercname"),
		Index("buffer_user_idx", "userid"),
	]

class QuasselUser(Model):
	__tablename__ = "quasseluser"
	userid = Column(Integer, Sequence("quasseluser_userid_seq"), nullable=False, primary_key=True)
	username = Column(String(64), nullable=False, unique=True)
	password = Column(String(40), nullable=False) # CHAR(40)


class Network(Model):
	__tablename__ = "network"
	id = Column("networkid", Integer, Sequence("network_networkid_seq"), nullable=False, primary_key=True)
	userid = Column(Integer, ForeignKey("quasseluser.userid", ondelete="CASCADE"), nullable=False, unique=True)
	name = Column("networkname", String(32), nullable=False, unique=True)
	identityid = Column(Integer, ForeignKey("identity.identityid", ondelete="SET NULL"))
	encodingcodec = Column(String(32), nullable=False, default="ISO-8859-15")
	decodingcodec = Column(String(32), nullable=False, default="ISO-8859-15")
	servercodec = Column(String(32))
	userandomserver = Column(Boolean, nullable=False, default=False)
	perform = Column(Text)
	useautoidentify = Column(Boolean, nullable=False, default=False)
	saslaccount = Column(String(128))
	saslpassword = Column(String(128))
	useautoreconnect = Column(Boolean, nullable=False, default=True)
	autoreconnectinterval = Column(Integer, nullable=False, default=0)
	autoreconnectretries = Column(Integer, nullable=False, default=0)
	unlimitedconnectretries = Column(Boolean, nullable=False, default=False)
	rejoinchannels = Column(Boolean, nullable=False, default=False)
	connected = Column(Boolean, nullable=False, default=False)
	usermode = Column(String(32))
	awaymessage = Column(String(256))
	attachperform = Column(Text)
	detachperform = Column(Text)


def quassel_session(uri):
	engine = create_engine(uri, echo=False)

	session = sessionmaker(engine)()
	return session
