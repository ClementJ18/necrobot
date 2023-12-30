-- migrate:up
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: necrobot; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA necrobot;


--
-- Name: channel_filter_hybrid; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.channel_filter_hybrid AS (
	channel_id bigint,
	filter character varying(50)
);


--
-- Name: character_stat; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.character_stat AS (
	is_percent boolean,
	stat integer
);


--
-- Name: emote_count_hybrid; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.emote_count_hybrid AS (
	reaction character varying(200),
	count integer
);


--
-- Name: poll_option; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.poll_option AS (
	poll_id bigint,
	message text
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: aliases; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.aliases (
    alias character varying(2000) NOT NULL,
    original character varying(2000),
    guild_id bigint NOT NULL
);


--
-- Name: badges; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.badges (
    user_id bigint NOT NULL,
    badge character varying(50) NOT NULL,
    spot integer DEFAULT 0,
    CONSTRAINT badges_spot_check CHECK (((spot >= 0) AND (spot <= 8)))
);


--
-- Name: badgeshop; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.badgeshop (
    name character varying(50) NOT NULL,
    file_name character varying(55),
    cost integer DEFAULT 0,
    special boolean DEFAULT false
);


--
-- Name: bannercharacters; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.bannercharacters (
    banner_id integer NOT NULL,
    char_id integer NOT NULL,
    modifier integer DEFAULT 1
);


--
-- Name: banners; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.banners (
    id integer NOT NULL,
    guild_id bigint,
    duration timestamp with time zone,
    name text,
    description text,
    image_url text,
    ongoing boolean DEFAULT false,
    max_rolls integer DEFAULT 0
);


--
-- Name: banners_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.banners_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: banners_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.banners_id_seq OWNED BY necrobot.banners.id;


--
-- Name: broadcasts; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.broadcasts (
    broadcast_id integer NOT NULL,
    guild_id bigint,
    channel_id bigint,
    start_time integer,
    "interval" integer,
    message character varying(2000),
    enabled boolean DEFAULT true,
    CONSTRAINT broadcasts_start_time_check CHECK (((start_time >= 0) AND (start_time <= 23))),
    CONSTRAINT broadcasts_start_time_check1 CHECK (((start_time >= 0) AND (start_time <= 23)))
);


--
-- Name: broadcasts_broadcast_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.broadcasts_broadcast_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: broadcasts_broadcast_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.broadcasts_broadcast_id_seq OWNED BY necrobot.broadcasts.broadcast_id;


--
-- Name: channelsubscriptions; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.channelsubscriptions (
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    last_update timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: characters; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.characters (
    id integer NOT NULL,
    name text,
    title text,
    description text,
    image_url text,
    tier integer,
    obtainable boolean,
    universe text,
    type text DEFAULT 'character'::text NOT NULL,
    active_skill text,
    passive_skill text,
    primary_health public.character_stat DEFAULT ROW(false, 100),
    secondary_health public.character_stat DEFAULT ROW(false, 0),
    physical_defense public.character_stat DEFAULT ROW(false, 0),
    physical_attack public.character_stat DEFAULT ROW(false, 0),
    magical_defense public.character_stat DEFAULT ROW(false, 0),
    magical_attack public.character_stat DEFAULT ROW(false, 0)
);


--
-- Name: characters_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.characters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: characters_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.characters_id_seq OWNED BY necrobot.characters.id;


--
-- Name: disabled; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.disabled (
    guild_id bigint NOT NULL,
    command character varying(50) NOT NULL
);


--
-- Name: equipmentset; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.equipmentset (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    char_id integer NOT NULL,
    weapon_id integer,
    artefact_id integer
);


--
-- Name: flowers; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.flowers (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    flowers bigint DEFAULT 0,
    CONSTRAINT check_positive CHECK ((flowers >= 0))
);


--
-- Name: flowersguild; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.flowersguild (
    guild_id bigint NOT NULL,
    symbol character varying(50) DEFAULT ':cherry_blossom:'::character varying,
    roll_cost integer DEFAULT 50,
    guaranteed integer DEFAULT 9
);


--
-- Name: grudges; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.grudges (
    id integer NOT NULL,
    user_id bigint,
    name character varying(50),
    grudge character varying(2000),
    grudge_date date DEFAULT CURRENT_DATE,
    avenged character varying(1000) DEFAULT 'False'::character varying
);


--
-- Name: grudges_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.grudges_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: grudges_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.grudges_id_seq OWNED BY necrobot.grudges.id;


--
-- Name: guilds; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.guilds (
    guild_id bigint NOT NULL,
    mute bigint DEFAULT 0,
    automod_channel bigint DEFAULT 0,
    welcome_channel bigint DEFAULT 0,
    welcome_message character varying(2000) DEFAULT ''::character varying,
    goodbye_message character varying(2000) DEFAULT ''::character varying,
    prefix character varying(2000) DEFAULT ''::character varying,
    broadcast_channel bigint DEFAULT 0,
    broadcast_message character varying(2000) DEFAULT ''::character varying,
    broadcast_time integer DEFAULT 1,
    starboard_channel bigint DEFAULT 0,
    starboard_limit integer DEFAULT 5,
    auto_role bigint DEFAULT 0,
    auto_role_timer integer DEFAULT 0,
    pm_warning boolean DEFAULT false,
    CONSTRAINT guilds_starboard_limit_check CHECK ((starboard_limit > 0))
);


--
-- Name: ignoreautomod; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.ignoreautomod (
    guild_id bigint NOT NULL,
    id bigint NOT NULL
);


--
-- Name: ignorecommand; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.ignorecommand (
    guild_id bigint NOT NULL,
    id bigint NOT NULL
);


--
-- Name: internalranked; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.internalranked (
    faction character varying(25),
    enemy character varying(25),
    defeats integer DEFAULT 0,
    victories integer DEFAULT 0
);


--
-- Name: internalrankedlogs; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.internalrankedlogs (
    user_id bigint,
    faction character varying(25),
    enemy character varying(25),
    faction_won boolean DEFAULT true,
    log_date timestamp with time zone DEFAULT now(),
    id integer NOT NULL
);


--
-- Name: internalrankedlogs_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.internalrankedlogs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: internalrankedlogs_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.internalrankedlogs_id_seq OWNED BY necrobot.internalrankedlogs.id;


--
-- Name: invites; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.invites (
    id character varying(10) NOT NULL,
    guild_id bigint,
    url character varying(200),
    uses integer,
    inviter bigint
);


--
-- Name: leaderboardpoints; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.leaderboardpoints (
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL,
    points bigint
);


--
-- Name: leaderboards; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.leaderboards (
    guild_id bigint NOT NULL,
    message character varying(200),
    symbol character varying(50)
);


--
-- Name: logs; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.logs (
    log_id integer NOT NULL,
    user_id bigint,
    username character varying(40),
    command character varying(50),
    guild_id bigint,
    guildname character varying(40),
    message character varying(2000),
    time_used timestamp with time zone DEFAULT now(),
    can_run boolean DEFAULT true
);


--
-- Name: logs_log_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.logs_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: logs_log_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.logs_log_id_seq OWNED BY necrobot.logs.log_id;


--
-- Name: mu; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.mu (
    user_id bigint,
    url character varying(500),
    approver_id bigint,
    guild_id bigint,
    post_date date DEFAULT CURRENT_DATE
);


--
-- Name: mu_users; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.mu_users (
    user_id bigint NOT NULL,
    username character varying(200),
    username_lower character varying(200),
    active boolean DEFAULT true
);


--
-- Name: permissionroles; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.permissionroles (
    guild_id bigint NOT NULL,
    level integer NOT NULL,
    role_id bigint
);


--
-- Name: permissions; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.permissions (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    level integer,
    CONSTRAINT permissions_level_check CHECK (((level >= 0) AND (level <= 7)))
);


--
-- Name: pity; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.pity (
    user_id bigint NOT NULL,
    banner_id integer NOT NULL,
    tier_5_pity integer DEFAULT 0,
    tier_4_pity integer DEFAULT 0,
    roll_count integer DEFAULT 1
);


--
-- Name: polloptions; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.polloptions (
    id integer NOT NULL,
    poll_id bigint,
    message text
);


--
-- Name: polloptions_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.polloptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: polloptions_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.polloptions_id_seq OWNED BY necrobot.polloptions.id;


--
-- Name: polls; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.polls (
    message_id bigint NOT NULL,
    guild_id bigint,
    link character varying(500),
    votes integer,
    emoji_list text[],
    CONSTRAINT polls_votes_check CHECK (((votes >= 1) AND (votes <= 20)))
);


--
-- Name: pollsv2; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.pollsv2 (
    message_id bigint NOT NULL,
    channel_id bigint,
    guild_id bigint,
    message text,
    title text,
    max_votes integer,
    open boolean DEFAULT true
);


--
-- Name: pollvotes; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.pollvotes (
    option_id integer NOT NULL,
    user_id bigint NOT NULL,
    poll_id bigint
);


--
-- Name: reminders; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.reminders (
    id integer NOT NULL,
    user_id bigint,
    channel_id bigint,
    reminder character varying(2000),
    timer character varying(200),
    start_date timestamp with time zone DEFAULT now(),
    end_date timestamp with time zone
);


--
-- Name: reminders_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.reminders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reminders_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.reminders_id_seq OWNED BY necrobot.reminders.id;


--
-- Name: rolledcharacters; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.rolledcharacters (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    char_id integer NOT NULL,
    level integer DEFAULT 1 NOT NULL
);


--
-- Name: selfroles; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.selfroles (
    guild_id bigint NOT NULL,
    id bigint NOT NULL
);


--
-- Name: starred; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.starred (
    message_id bigint NOT NULL,
    starred_id bigint,
    guild_id bigint,
    user_id bigint,
    stars integer DEFAULT 0,
    link character varying(200) DEFAULT 'None'::character varying
);


--
-- Name: tags; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.tags (
    guild_id bigint NOT NULL,
    name character varying(2000) NOT NULL,
    content character varying(2000),
    owner_id bigint,
    uses integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: twitch; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.twitch (
    guild_id bigint NOT NULL,
    channel_id bigint,
    twitch_id character varying(50) NOT NULL,
    last_update timestamp with time zone DEFAULT now() NOT NULL,
    filter character varying(200),
    twitch_name character varying(200)
);


--
-- Name: users; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.users (
    user_id bigint NOT NULL,
    necroins bigint DEFAULT 200,
    exp integer DEFAULT 0,
    daily date DEFAULT CURRENT_DATE,
    title character varying(40) DEFAULT ''::character varying,
    tutorial boolean DEFAULT false,
    CONSTRAINT users_necroins_check CHECK ((necroins >= 0))
);


--
-- Name: votes; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.votes (
    message_id bigint NOT NULL,
    user_id bigint NOT NULL,
    reaction character varying(200) NOT NULL
);


--
-- Name: warnings; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.warnings (
    warn_id integer NOT NULL,
    user_id bigint,
    issuer_id bigint,
    guild_id bigint,
    warning_content character varying(2000),
    date_issued timestamp with time zone DEFAULT now()
);


--
-- Name: warnings_warn_id_seq; Type: SEQUENCE; Schema: necrobot; Owner: -
--

CREATE SEQUENCE necrobot.warnings_warn_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: warnings_warn_id_seq; Type: SEQUENCE OWNED BY; Schema: necrobot; Owner: -
--

ALTER SEQUENCE necrobot.warnings_warn_id_seq OWNED BY necrobot.warnings.warn_id;


--
-- Name: youtube; Type: TABLE; Schema: necrobot; Owner: -
--

CREATE TABLE necrobot.youtube (
    guild_id bigint NOT NULL,
    channel_id bigint,
    youtuber_id character varying(50) NOT NULL,
    last_update timestamp with time zone DEFAULT now() NOT NULL,
    filter character varying(200),
    youtuber_name character varying(200)
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying(128) NOT NULL
);


--
-- Name: banners id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.banners ALTER COLUMN id SET DEFAULT nextval('necrobot.banners_id_seq'::regclass);


--
-- Name: broadcasts broadcast_id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.broadcasts ALTER COLUMN broadcast_id SET DEFAULT nextval('necrobot.broadcasts_broadcast_id_seq'::regclass);


--
-- Name: characters id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.characters ALTER COLUMN id SET DEFAULT nextval('necrobot.characters_id_seq'::regclass);


--
-- Name: grudges id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.grudges ALTER COLUMN id SET DEFAULT nextval('necrobot.grudges_id_seq'::regclass);


--
-- Name: internalrankedlogs id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.internalrankedlogs ALTER COLUMN id SET DEFAULT nextval('necrobot.internalrankedlogs_id_seq'::regclass);


--
-- Name: logs log_id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.logs ALTER COLUMN log_id SET DEFAULT nextval('necrobot.logs_log_id_seq'::regclass);


--
-- Name: polloptions id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.polloptions ALTER COLUMN id SET DEFAULT nextval('necrobot.polloptions_id_seq'::regclass);


--
-- Name: reminders id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.reminders ALTER COLUMN id SET DEFAULT nextval('necrobot.reminders_id_seq'::regclass);


--
-- Name: warnings warn_id; Type: DEFAULT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.warnings ALTER COLUMN warn_id SET DEFAULT nextval('necrobot.warnings_warn_id_seq'::regclass);


--
-- Name: aliases aliases_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.aliases
    ADD CONSTRAINT aliases_pkey PRIMARY KEY (alias, guild_id);


--
-- Name: badges badges_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.badges
    ADD CONSTRAINT badges_pkey PRIMARY KEY (user_id, badge);


--
-- Name: badgeshop badgeshop_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.badgeshop
    ADD CONSTRAINT badgeshop_pkey PRIMARY KEY (name);


--
-- Name: bannercharacters bannercharacters_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.bannercharacters
    ADD CONSTRAINT bannercharacters_pkey PRIMARY KEY (banner_id, char_id);


--
-- Name: banners banners_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.banners
    ADD CONSTRAINT banners_pkey PRIMARY KEY (id);


--
-- Name: broadcasts broadcasts_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.broadcasts
    ADD CONSTRAINT broadcasts_pkey PRIMARY KEY (broadcast_id);


--
-- Name: channelsubscriptions channelsubscriptions_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.channelsubscriptions
    ADD CONSTRAINT channelsubscriptions_pkey PRIMARY KEY (user_id, channel_id);


--
-- Name: characters characters_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.characters
    ADD CONSTRAINT characters_pkey PRIMARY KEY (id);


--
-- Name: disabled disabled_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.disabled
    ADD CONSTRAINT disabled_pkey PRIMARY KEY (guild_id, command);


--
-- Name: equipmentset equipmentset_guild_id_user_id_artefact_id_key; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_guild_id_user_id_artefact_id_key UNIQUE (guild_id, user_id, artefact_id);


--
-- Name: equipmentset equipmentset_guild_id_user_id_weapon_id_key; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_guild_id_user_id_weapon_id_key UNIQUE (guild_id, user_id, weapon_id);


--
-- Name: equipmentset equipmentset_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_pkey PRIMARY KEY (guild_id, user_id, char_id);


--
-- Name: flowers flowers_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.flowers
    ADD CONSTRAINT flowers_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: flowersguild flowersguild_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.flowersguild
    ADD CONSTRAINT flowersguild_pkey PRIMARY KEY (guild_id);


--
-- Name: grudges grudges_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.grudges
    ADD CONSTRAINT grudges_pkey PRIMARY KEY (id);


--
-- Name: guilds guilds_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.guilds
    ADD CONSTRAINT guilds_pkey PRIMARY KEY (guild_id);


--
-- Name: ignoreautomod ignoreautomod_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.ignoreautomod
    ADD CONSTRAINT ignoreautomod_pkey PRIMARY KEY (guild_id, id);


--
-- Name: ignorecommand ignorecommand_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.ignorecommand
    ADD CONSTRAINT ignorecommand_pkey PRIMARY KEY (guild_id, id);


--
-- Name: internalrankedlogs internalrankedlogs_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.internalrankedlogs
    ADD CONSTRAINT internalrankedlogs_pkey PRIMARY KEY (id);


--
-- Name: invites invites_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.invites
    ADD CONSTRAINT invites_pkey PRIMARY KEY (id);


--
-- Name: leaderboardpoints leaderboardpoints_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.leaderboardpoints
    ADD CONSTRAINT leaderboardpoints_pkey PRIMARY KEY (user_id, guild_id);


--
-- Name: leaderboards leaderboards_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.leaderboards
    ADD CONSTRAINT leaderboards_pkey PRIMARY KEY (guild_id);


--
-- Name: logs logs_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.logs
    ADD CONSTRAINT logs_pkey PRIMARY KEY (log_id);


--
-- Name: mu_users mu_users_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.mu_users
    ADD CONSTRAINT mu_users_pkey PRIMARY KEY (user_id);


--
-- Name: mu_users mu_users_username_lower_key; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.mu_users
    ADD CONSTRAINT mu_users_username_lower_key UNIQUE (username_lower);


--
-- Name: permissionroles permissionroles_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.permissionroles
    ADD CONSTRAINT permissionroles_pkey PRIMARY KEY (guild_id, level);


--
-- Name: permissions permissions_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.permissions
    ADD CONSTRAINT permissions_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: pity pity_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pity
    ADD CONSTRAINT pity_pkey PRIMARY KEY (user_id, banner_id);


--
-- Name: polloptions polloptions_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.polloptions
    ADD CONSTRAINT polloptions_pkey PRIMARY KEY (id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (message_id);


--
-- Name: pollsv2 pollsv2_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pollsv2
    ADD CONSTRAINT pollsv2_pkey PRIMARY KEY (message_id);


--
-- Name: pollvotes pollvotes_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pollvotes
    ADD CONSTRAINT pollvotes_pkey PRIMARY KEY (option_id, user_id);


--
-- Name: reminders reminders_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.reminders
    ADD CONSTRAINT reminders_pkey PRIMARY KEY (id);


--
-- Name: rolledcharacters rolledcharacters_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.rolledcharacters
    ADD CONSTRAINT rolledcharacters_pkey PRIMARY KEY (guild_id, user_id, char_id);


--
-- Name: selfroles selfroles_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.selfroles
    ADD CONSTRAINT selfroles_pkey PRIMARY KEY (guild_id, id);


--
-- Name: starred starred_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.starred
    ADD CONSTRAINT starred_pkey PRIMARY KEY (message_id);


--
-- Name: tags tags_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (guild_id, name);


--
-- Name: twitch twitch_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.twitch
    ADD CONSTRAINT twitch_pkey PRIMARY KEY (guild_id, twitch_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: votes votes_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.votes
    ADD CONSTRAINT votes_pkey PRIMARY KEY (message_id, user_id, reaction);


--
-- Name: warnings warnings_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.warnings
    ADD CONSTRAINT warnings_pkey PRIMARY KEY (warn_id);


--
-- Name: youtube youtube_pkey; Type: CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.youtube
    ADD CONSTRAINT youtube_pkey PRIMARY KEY (guild_id, youtuber_id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: aliases aliases_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.aliases
    ADD CONSTRAINT aliases_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: aliases aliases_original_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.aliases
    ADD CONSTRAINT aliases_original_guild_id_fkey FOREIGN KEY (original, guild_id) REFERENCES necrobot.tags(name, guild_id) ON DELETE CASCADE;


--
-- Name: badges badges_badge_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.badges
    ADD CONSTRAINT badges_badge_fkey FOREIGN KEY (badge) REFERENCES necrobot.badgeshop(name) ON DELETE CASCADE;


--
-- Name: badges badges_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.badges
    ADD CONSTRAINT badges_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: bannercharacters bannercharacters_banner_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.bannercharacters
    ADD CONSTRAINT bannercharacters_banner_id_fkey FOREIGN KEY (banner_id) REFERENCES necrobot.banners(id) ON DELETE CASCADE;


--
-- Name: bannercharacters bannercharacters_char_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.bannercharacters
    ADD CONSTRAINT bannercharacters_char_id_fkey FOREIGN KEY (char_id) REFERENCES necrobot.characters(id) ON DELETE CASCADE;


--
-- Name: banners banners_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.banners
    ADD CONSTRAINT banners_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: broadcasts broadcasts_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.broadcasts
    ADD CONSTRAINT broadcasts_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: channelsubscriptions channelsubscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.channelsubscriptions
    ADD CONSTRAINT channelsubscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: disabled disabled_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.disabled
    ADD CONSTRAINT disabled_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: equipmentset equipmentset_artefact_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_artefact_id_fkey FOREIGN KEY (artefact_id) REFERENCES necrobot.characters(id) ON DELETE CASCADE;


--
-- Name: equipmentset equipmentset_char_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_char_id_fkey FOREIGN KEY (char_id) REFERENCES necrobot.characters(id) ON DELETE CASCADE;


--
-- Name: equipmentset equipmentset_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: equipmentset equipmentset_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: equipmentset equipmentset_weapon_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.equipmentset
    ADD CONSTRAINT equipmentset_weapon_id_fkey FOREIGN KEY (weapon_id) REFERENCES necrobot.characters(id) ON DELETE CASCADE;


--
-- Name: flowers flowers_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.flowers
    ADD CONSTRAINT flowers_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: flowers flowers_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.flowers
    ADD CONSTRAINT flowers_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: flowersguild flowersguild_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.flowersguild
    ADD CONSTRAINT flowersguild_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: ignoreautomod ignoreautomod_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.ignoreautomod
    ADD CONSTRAINT ignoreautomod_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: ignorecommand ignorecommand_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.ignorecommand
    ADD CONSTRAINT ignorecommand_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: invites invites_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.invites
    ADD CONSTRAINT invites_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: leaderboardpoints leaderboardpoints_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.leaderboardpoints
    ADD CONSTRAINT leaderboardpoints_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: leaderboardpoints leaderboardpoints_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.leaderboardpoints
    ADD CONSTRAINT leaderboardpoints_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: leaderboards leaderboards_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.leaderboards
    ADD CONSTRAINT leaderboards_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: logs logs_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.logs
    ADD CONSTRAINT logs_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: logs logs_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.logs
    ADD CONSTRAINT logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: mu mu_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.mu
    ADD CONSTRAINT mu_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: mu_users mu_users_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.mu_users
    ADD CONSTRAINT mu_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: permissionroles permissionroles_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.permissionroles
    ADD CONSTRAINT permissionroles_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: permissions permissions_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.permissions
    ADD CONSTRAINT permissions_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: permissions permissions_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.permissions
    ADD CONSTRAINT permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: pity pity_banner_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pity
    ADD CONSTRAINT pity_banner_id_fkey FOREIGN KEY (banner_id) REFERENCES necrobot.banners(id) ON DELETE CASCADE;


--
-- Name: pity pity_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pity
    ADD CONSTRAINT pity_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: polloptions polloptions_poll_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.polloptions
    ADD CONSTRAINT polloptions_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES necrobot.pollsv2(message_id) ON DELETE CASCADE;


--
-- Name: polls polls_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.polls
    ADD CONSTRAINT polls_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: pollsv2 pollsv2_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pollsv2
    ADD CONSTRAINT pollsv2_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: pollvotes pollvotes_option_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pollvotes
    ADD CONSTRAINT pollvotes_option_id_fkey FOREIGN KEY (option_id) REFERENCES necrobot.polloptions(id) ON DELETE CASCADE;


--
-- Name: pollvotes pollvotes_poll_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pollvotes
    ADD CONSTRAINT pollvotes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES necrobot.pollsv2(message_id) ON DELETE CASCADE;


--
-- Name: pollvotes pollvotes_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.pollvotes
    ADD CONSTRAINT pollvotes_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: reminders reminders_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.reminders
    ADD CONSTRAINT reminders_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: rolledcharacters rolledcharacters_char_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.rolledcharacters
    ADD CONSTRAINT rolledcharacters_char_id_fkey FOREIGN KEY (char_id) REFERENCES necrobot.characters(id) ON DELETE CASCADE;


--
-- Name: rolledcharacters rolledcharacters_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.rolledcharacters
    ADD CONSTRAINT rolledcharacters_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: rolledcharacters rolledcharacters_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.rolledcharacters
    ADD CONSTRAINT rolledcharacters_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: selfroles selfroles_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.selfroles
    ADD CONSTRAINT selfroles_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: starred starred_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.starred
    ADD CONSTRAINT starred_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: starred starred_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.starred
    ADD CONSTRAINT starred_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: tags tags_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.tags
    ADD CONSTRAINT tags_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: tags tags_owner_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.tags
    ADD CONSTRAINT tags_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: twitch twitch_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.twitch
    ADD CONSTRAINT twitch_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: votes votes_message_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.votes
    ADD CONSTRAINT votes_message_id_fkey FOREIGN KEY (message_id) REFERENCES necrobot.polls(message_id) ON DELETE CASCADE;


--
-- Name: votes votes_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.votes
    ADD CONSTRAINT votes_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: warnings warnings_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.warnings
    ADD CONSTRAINT warnings_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- Name: warnings warnings_issuer_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.warnings
    ADD CONSTRAINT warnings_issuer_id_fkey FOREIGN KEY (issuer_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: warnings warnings_user_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.warnings
    ADD CONSTRAINT warnings_user_id_fkey FOREIGN KEY (user_id) REFERENCES necrobot.users(user_id) ON DELETE CASCADE;


--
-- Name: youtube youtube_guild_id_fkey; Type: FK CONSTRAINT; Schema: necrobot; Owner: -
--

ALTER TABLE ONLY necrobot.youtube
    ADD CONSTRAINT youtube_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES necrobot.guilds(guild_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--


--
-- Dbmate schema migrations
--



-- migrate:down
