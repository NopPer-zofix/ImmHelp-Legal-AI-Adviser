-- ImmHelp PostgreSQL schema exported with pg_dump --schema-only from a running database.
-- Structure only (no rows). Ownership and privileges were removed.
-- Regenerate: pg_dump --schema-only --no-owner --no-privileges -d <database> -f schema_from_postgres.sql
--
-- PostgreSQL database dump
--

\restrict v7aXHqXhyoICc8lZaoBngvPvjJgDoSRmayFMX9CRmyc8RGflbZtCrAxXB5paaAv

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: advertisers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.advertisers (
    id integer NOT NULL,
    company character varying NOT NULL,
    reg_number character varying NOT NULL,
    website character varying NOT NULL,
    category character varying(40) NOT NULL,
    licence_number character varying NOT NULL,
    contact_name character varying NOT NULL,
    contact_email character varying NOT NULL,
    contact_phone character varying NOT NULL,
    topics character varying NOT NULL,
    notes text NOT NULL,
    status character varying(20) NOT NULL,
    status_reason character varying,
    checks text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    created_by_id integer,
    reviewed_at timestamp with time zone,
    reviewed_by_id integer
);



--
-- Name: advertisers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.advertisers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: advertisers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.advertisers_id_seq OWNED BY public.advertisers.id;


--
-- Name: chat_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chat_state (
    chat_id integer NOT NULL,
    profile character varying NOT NULL,
    compacted_through_id integer NOT NULL,
    last_topics character varying NOT NULL,
    updated_at timestamp with time zone DEFAULT now()
);



--
-- Name: chats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.chats (
    id integer NOT NULL,
    user_id integer NOT NULL,
    title character varying(120)
);



--
-- Name: chats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.chats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: chats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.chats_id_seq OWNED BY public.chats.id;


--
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    id integer NOT NULL,
    user_id integer NOT NULL,
    chat_id integer NOT NULL,
    message character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    topics character varying(80)
);



--
-- Name: messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.messages_id_seq OWNED BY public.messages.id;


--
-- Name: user_activity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_activity (
    user_id integer NOT NULL,
    minute timestamp with time zone NOT NULL
);



--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email character varying NOT NULL,
    password character varying NOT NULL,
    username character varying NOT NULL,
    role character varying(20) DEFAULT 'user'::character varying NOT NULL,
    is_banned boolean DEFAULT false NOT NULL,
    banned_reason character varying,
    banned_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    consent_version character varying(40),
    consent_accepted_at timestamp with time zone
);



--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;



--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: advertisers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.advertisers ALTER COLUMN id SET DEFAULT nextval('public.advertisers_id_seq'::regclass);


--
-- Name: chats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats ALTER COLUMN id SET DEFAULT nextval('public.chats_id_seq'::regclass);


--
-- Name: messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages ALTER COLUMN id SET DEFAULT nextval('public.messages_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: advertisers advertisers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.advertisers
    ADD CONSTRAINT advertisers_pkey PRIMARY KEY (id);


--
-- Name: chat_state chat_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_state
    ADD CONSTRAINT chat_state_pkey PRIMARY KEY (chat_id);


--
-- Name: chats chats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: user_activity user_activity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_activity
    ADD CONSTRAINT user_activity_pkey PRIMARY KEY (user_id, minute);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_chats_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_chats_id ON public.chats USING btree (id);


--
-- Name: ix_user_activity_minute; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_user_activity_minute ON public.user_activity USING btree (minute);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: advertisers advertisers_created_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.advertisers
    ADD CONSTRAINT advertisers_created_by_id_fkey FOREIGN KEY (created_by_id) REFERENCES public.users(id);


--
-- Name: advertisers advertisers_reviewed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.advertisers
    ADD CONSTRAINT advertisers_reviewed_by_id_fkey FOREIGN KEY (reviewed_by_id) REFERENCES public.users(id);


--
-- Name: chat_state chat_state_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chat_state
    ADD CONSTRAINT chat_state_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chats(id);


--
-- Name: chats chats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT chats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: messages messages_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chats(id);


--
-- Name: messages messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_activity user_activity_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_activity
    ADD CONSTRAINT user_activity_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict v7aXHqXhyoICc8lZaoBngvPvjJgDoSRmayFMX9CRmyc8RGflbZtCrAxXB5paaAv

