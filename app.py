import hashlib
import re
from datetime import date, timedelta
from flask import Flask, render_template, request, abort
from jinja2.utils import urlize
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload
from quassel import quassel_session, Message, Buffer, Sender, Network

import settings


app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = True

## Quassel Connection
session = quassel_session(settings.uri)


def hash_nick(nick):
	hash = hashlib.sha1(nick.encode("utf-8"))
	return int(hash.hexdigest(), 16)


def process_message(message):
	# NOTE: Working around jinja2.utils.urlize being far too greedy on matches
	message = message.replace("\x0f", " \x0f")
	message = urlize(message)
	message = message.replace(" \x0f", "\x0f")
	message = re.sub("\x03(\\d\\d)", r'<span class="color\1">', message)
	message = message.replace("\x03", "</span>")
	message = message.replace("\x0f", "</b></em></u></span>")  # Nasty.
	while "\x02" in message:
	    message = message.replace("\x02", "<b>", 1)
	    message = message.replace("\x02", "</b>", 1)
	while "\x1d" in message:
	    message = message.replace("\x1d", "<em>", 1)
	    message = message.replace("\x1d", "</em>", 1)
	while "\x1f" in message:
	    message = message.replace("\x1f", "<u>", 1)
	    message = message.replace("\x1f", "</u>", 1)
	return message


@app.route("/<name>/")
def channel_index(name):
	if name not in settings.channels:
		abort(404)

	days = request.args.get("days", "")
	if days.isdigit():
		days = min(int(days), 200)
	else:
		days = settings.days
	query = session.query(Message).join(Sender)
	query = query.order_by(asc(Message.time))
	query = query.filter(Message.time >= date.today() - timedelta(days))
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
		"process_message": process_message,
	}
	return render_template("backlog.html", **context)


if __name__ == "__main__":
	app.debug = True
	app.run()
	session.close()
