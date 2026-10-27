-- ImmHelp PostgreSQL schema (structure only, generated from models.py)
-- Regenerate with: python db/export_schema.py > db/schema.sql

CREATE TABLE users (
	id SERIAL NOT NULL, 
	email VARCHAR NOT NULL, 
	password VARCHAR NOT NULL, 
	username VARCHAR NOT NULL, 
	role VARCHAR(20) DEFAULT 'user' NOT NULL, 
	is_banned BOOLEAN DEFAULT false NOT NULL, 
	banned_reason VARCHAR, 
	banned_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	consent_version VARCHAR(40), 
	consent_accepted_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE INDEX ix_users_id ON users (id);

CREATE TABLE advertisers (
	id SERIAL NOT NULL, 
	company VARCHAR NOT NULL, 
	reg_number VARCHAR NOT NULL, 
	website VARCHAR NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	licence_number VARCHAR NOT NULL, 
	contact_name VARCHAR NOT NULL, 
	contact_email VARCHAR NOT NULL, 
	contact_phone VARCHAR NOT NULL, 
	topics VARCHAR NOT NULL, 
	notes TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	status_reason VARCHAR, 
	checks TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	created_by_id INTEGER, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	reviewed_by_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id), 
	FOREIGN KEY(reviewed_by_id) REFERENCES users (id)
);

CREATE TABLE chats (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(120), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_chats_id ON chats (id);

CREATE TABLE user_activity (
	user_id INTEGER NOT NULL, 
	minute TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (user_id, minute), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_user_activity_minute ON user_activity (minute);

CREATE TABLE chat_state (
	chat_id INTEGER NOT NULL, 
	profile VARCHAR NOT NULL, 
	compacted_through_id INTEGER NOT NULL, 
	last_topics VARCHAR NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	PRIMARY KEY (chat_id), 
	FOREIGN KEY(chat_id) REFERENCES chats (id)
);

CREATE TABLE messages (
	id SERIAL NOT NULL, 
	user_id INTEGER NOT NULL, 
	chat_id INTEGER NOT NULL, 
	message VARCHAR NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
	topics VARCHAR(80), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(chat_id) REFERENCES chats (id)
);

