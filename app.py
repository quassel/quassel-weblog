import hashlib
from datetime import date, timedelta
from flask import Flask, render_template, request, abort
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload
from quassel import quassel_session, Message, Buffer, Sender, Network

import config


app = Flask(__name__)

## Quassel Connection
session = quassel_session(config.uri)


@app.route("/")
def index():
        return render_template("page/index.html", **{"channels": config.channels})


def hash_nick(nick):
	hash = hashlib.sha1(nick.encode("utf-8"))
	return int(hash.hexdigest(), 16)


@app.route("/<name>/")
def channel_index(name):
	if name not in config.channels:
		abort(404)
	query = session.query(Message).join(Sender)
	query = query.order_by(asc(Message.time))
	query = query.filter(Message.time >= date.today() - timedelta(config.days))
	#query = query.options(joinedload(Message.sender))
	#query = query.options(joinedload(Message.buffer))
	query = query.join(Message.buffer)
	query = query.filter(Buffer.userid == 1)
	channel_name = "#" + name # XXX
	query = query.filter(Buffer.name == channel_name)

	nick = request.args.get("nick")
	if nick:
		query = query.filter(Sender.name.startswith(nick))

	context = {
		"channel": channel_name,
		"highlight": request.args.get("highlight", "").lower(),
		"messages": query,
		"hash": hash_nick,
	}
	return render_template("backlog.html", **context)


if __name__ == "__main__":
	app.debug = True
	app.run()
	session.close()
