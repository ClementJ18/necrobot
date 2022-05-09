CREATE SCHEMA necrobot;

CREATE TABLE necrobot.Users (
    user_id bigint PRIMARY KEY,
    necroins bigint CHECK (necroins >= 0) DEFAULT 200,
    exp int DEFAULT 0,
    daily date DEFAULT current_date,
    title varchar(40) DEFAULT '',
    tutorial boolean DEFAULT False
);

CREATE TABLE necrobot.Guilds (
    guild_id bigint PRIMARY KEY,
    mute bigint DEFAULT 0,
    automod_channel bigint DEFAULT 0,
    welcome_channel bigint DEFAULT 0,
    welcome_message varchar(2000) DEFAULT '',
    goodbye_message varchar(2000) DEFAULT '',
    prefix varchar(2000) DEFAULT '',
    starboard_channel bigint DEFAULT 0,
    starboard_limit int DEFAULT 5 CHECK(starboard_limit > 0),
    auto_role bigint DEFAULT 0,
    auto_role_timer int DEFAULT 0,
    pm_warning boolean DEFAULT False
);

CREATE TABLE necrobot.Permissions (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    level int CHECK(level BETWEEN 0 AND 7),
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE necrobot.BadgeShop (
    name varchar(50) PRIMARY KEY,
    file_name varchar(55),
    cost int DEFAULT 0,
    special boolean DEFAULT False
);

CREATE TABLE necrobot.Badges (
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    badge varchar(50) REFERENCES necrobot.BadgeShop(name) ON DELETE CASCADE,
    spot int DEFAULT 0 CHECK(spot BETWEEN 0 AND 8),
    PRIMARY KEY(user_id, badge)
);

CREATE TABLE necrobot.Disabled (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    command varchar(50),
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE necrobot.IgnoreAutomod (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    id bigint,
    PRIMARY KEY(guild_id, id)
);

CREATE TABLE necrobot.IgnoreCommand (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    id bigint,
    PRIMARY KEY(guild_id, id)
);

CREATE TABLE necrobot.SelfRoles (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    id bigint,
    PRIMARY KEY(guild_id, id)
);

CREATE TABLE necrobot.Tags (
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    name varchar(2000),
    content varchar(2000),
    owner_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    uses int DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY(guild_id, name)
);

CREATE TABLE necrobot.Aliases(
    alias varchar(2000),
    original varchar(2000),
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    PRIMARY KEY(alias, guild_id),
    FOREIGN KEY (original, guild_id) REFERENCES necrobot.Tags(name, guild_id) ON DELETE CASCADE
);

CREATE TABLE necrobot.Logs(
    log_id serial PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    username varchar(100),
    command varchar(100),
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    guildname varchar(100),
    message varchar(2000),
    time_used TIMESTAMPTZ DEFAULT NOW(),
    can_run boolean DEFAULT True
);

CREATE TABLE necrobot.Warnings(
    warn_id serial PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    issuer_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    warning_content varchar(2000),
    date_issued TIMESTAMPTZ DEFAULT NOW()
);

-- SELECT setval(pg_get_serial_sequence('necrobot.Warnings', 'warn_id'), coalesce(max(warn_id)+1, 1), false) FROM necrobot.Warnings;

CREATE TABLE necrobot.Starred(
    message_id bigint PRIMARY KEY,
    starred_id bigint,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    stars int DEFAULT 4,
    link varchar(200) DEFAULT 'None'
);

-- ALTER TABLE necrobot.Starred ADD stars int DEFAULT 4;
-- ALTER TABLE necrobot.Starred ADD link varchar(200) DEFAULT 'None';

CREATE TABLE necrobot.Reminders(
    id SERIAL PRIMARY KEY,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    channel_id bigint,
    reminder varchar(2000),
    timer varchar(200),
    start_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE necrobot.Polls(
    message_id bigint PRIMARY KEY,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    link varchar(500),
    votes int CHECK(votes BETWEEN 1 AND 20),
    emoji_list text[]
);

CREATE TABLE necrobot.Votes(
    message_id bigint REFERENCES necrobot.Polls(message_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    reaction varchar(200), 
    PRIMARY KEY(message_id, user_id, reaction)
);

CREATE TABLE necrobot.Youtube(
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    channel_id bigint,
    youtuber_id varchar(50),
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filter varchar(200),
    youtuber_name varchar(200),
    PRIMARY KEY(guild_id, youtuber_id)
);

CREATE TABLE necrobot.Twitch(
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    channel_id bigint,
    twitch_id varchar(50),
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filter varchar(200),
    twitch_name varchar(200),
    PRIMARY KEY(guild_id, twitch_id)
)

CREATE TABLE necrobot.Invites(
    id varchar(10) PRIMARY KEY,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    url varchar(200),
    uses int,
    inviter bigint
);

CREATE TABLE necrobot.MU(
    user_id bigint,
    url varchar(500),
    approver_id bigint,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    post_date date DEFAULT current_date
);

CREATE TABLE necrobot.MU_Users(
    user_id bigint PRIMARY KEY REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    username varchar(200),
    username_lower varchar(200) UNIQUE,
    active boolean DEFAULT True
);

CREATE TABLE necrobot.Leaderboards(
    guild_id bigint PRIMARY KEY REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    message varchar(200),
    symbol varchar(50)
);

CREATE TABLE necrobot.LeaderboardPoints(
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    points bigint,
    PRIMARY KEY(user_id, guild_id) 
);

CREATE TABLE necrobot.Grudges(
    id SERIAL PRIMARY KEY,
    user_id bigint,
    name varchar(50),
    grudge varchar(2000),
    grudge_date date DEFAULT current_date,
    avenged varchar(1000) DEFAULT 'False'
);

CREATE TABLE necrobot.InternalRanked(
    faction varchar(25),
    enemy varchar(25),
    defeats int DEFAULT 0,
    victories int DEFAULT 0
    PRIMARY KEY(faction, enemy)
);

CREATE TABLE necrobot.InternalRankedLogs(
    id SERIAL PRIMARY KEY
    user_id bigint,
    faction varchar(25),
    enemy varchar(25),
    faction_won boolean DEFAULT True,
    log_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE necrobot.Broadcasts(
    broadcast_id serial PRIMARY KEY,
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    channel_id bigint,
    start_time int,
    interval int,
    message varchar(2000),
    enabled boolean DEFAULT True
);

CREATE TABLE necrobot.PermissionRoles(
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    level int,
    role_id bigint,
    PRIMARY KEY(guild_id, level)
);

CREATE TABLE necrobot.Flowers(
    guild_id bigint REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    user_id bigint REFERENCES necrobot.Users(user_id) ON DELETE CASCADE,
    flowers bigint DEFAULT 0,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE necrobot.FlowersGuild(
    guild_id bigint PRIMARY KEY REFERENCES necrobot.Guilds(guild_id) ON DELETE CASCADE,
    symbol varchar(50) DEFAULT ':cherry_blossom:'

);

CREATE TYPE channel_filter_hybrid as (
    channel_id bigint,
    filter varchar(50)
);

CREATE TYPE emote_count_hybrid as (
    reaction varchar(200),
    count int
);
